"""OPA-ID-003: robust parametric inverse design of a 2D directional coupler."""
import argparse
import csv
import os
import json
from pathlib import Path
import time

import meep as mp
import numpy as np

OUT = Path("results/opa-id-003")
INDEX = 1.8
WIDTH = 0.6
PORT = 1.1
BEND = 2.5
CELL = (19, 6)
SOURCE_X = -8.0
LEFT_X, RIGHT_X = -7.2, 7.2
SPAN = 1.8
WL0 = 1.55
RES = (30, 60)
MIN_TIME = 200
LENGTHS = (2., 4., 6., 8.)
GAPS = (0.2, 0.35, 0.5)
TRAIN = ((0., WL0), (-0.02, WL0), (0.02, WL0))
# Held-out width biases and wavelengths never used to select the design.
HOLDOUT = ((-0.01, WL0), (0.01, WL0), (-0.03, WL0), (0.03, WL0),
           (0., 1.53), (0., 1.57))
PARITY = mp.ODD_Z
CORE = mp.Medium(index=INDEX)


def geometry(length, gap, bias):
    """Uniform full-width bias at fixed guide centre lines, in micrometres."""
    half = length/2
    x = np.unique(np.concatenate(([-CELL[0]/2], np.linspace(-half-BEND,-half,51),
                                 [half], np.linspace(half,half+BEND,51),
                                 [CELL[0]/2])))
    inner = (WIDTH+gap)/2
    u = np.clip((abs(x)-half)/BEND,0,1)
    y = inner+(PORT-inner)*(0.5-0.5*np.cos(np.pi*u))
    width = WIDTH+bias
    result = []
    for sign in (-1,1):
        center = sign*y
        # Vertical edge offset: deliberately a width-bias proxy, not a
        # true normal-direction morphological etch of curved sidewalls.
        vertices = [mp.Vector3(float(a),float(b)) for a,b in
                    zip(x,center-width/2)]
        vertices += [mp.Vector3(float(a),float(b)) for a,b in
                     zip(x[::-1],(center+width/2)[::-1])]
        result.append(mp.Prism(vertices,height=mp.inf,axis=mp.Vector3(0,0,1),
                               material=CORE))
    return result


def make_sim(res,bias,wl,length=None,gap=None):
    geom = ([mp.Block(center=mp.Vector3(0,-PORT),
                      size=mp.Vector3(mp.inf,WIDTH+bias,mp.inf),material=CORE)]
            if length is None else geometry(length,gap,bias))
    freq=1/wl
    return mp.Simulation(cell_size=mp.Vector3(*CELL),dimensions=2,resolution=res,
        boundary_layers=[mp.PML(0.8)],geometry=geom,
        sources=[mp.EigenModeSource(mp.GaussianSource(freq,fwidth=0.4*freq),
            center=mp.Vector3(SOURCE_X,-PORT),size=mp.Vector3(0,SPAN),
            eig_parity=mp.EVEN_Y+PARITY)])


def monitor(sim,x,y,wl):
    return sim.add_mode_monitor([1/wl],mp.ModeRegion(center=mp.Vector3(x,y),
        size=mp.Vector3(0,SPAN)),yee_grid=True,decimation_factor=1)


def modes(sim,m):
    return sim.get_eigenmode_coefficients(m,[1],eig_parity=PARITY).alpha[0,0,:]


def run(sim):
    sim.run(until_after_sources=mp.stop_when_dft_decayed(1e-10,MIN_TIME))


def reference(res,bias,wl):
    sim=make_sim(res,bias,wl)
    try:
        left=monitor(sim,LEFT_X,-PORT,wl)
        right=monitor(sim,RIGHT_X,-PORT,wl)
        run(sim)
        inc=float(abs(modes(sim,left)[0])**2)
        if not np.isfinite(inc) or inc<=0:
            raise RuntimeError("Invalid incident reference")
        return inc,sim.get_flux_data(left),float(abs(modes(sim,right)[0])**2/inc)
    finally:
        sim.reset_meep()


def measure(res,length,gap,bias,wl,ref):
    inc,sub,straight=ref
    sim=make_sim(res,bias,wl,length,gap)
    try:
        left=monitor(sim,LEFT_X,-PORT,wl)
        sim.load_minus_flux_data(left,sub)
        # Reflection into the opposite input guide has no incident field.
        reflected_cross=monitor(sim,LEFT_X,PORT,wl)
        bar=monitor(sim,RIGHT_X,-PORT,wl)
        cross=monitor(sim,RIGHT_X,PORT,wl)
        run(sim)
        t,c=[float(abs(modes(sim,m)[0])**2/inc) for m in (bar,cross)]
        r1,r2=[float(abs(modes(sim,m)[1])**2/inc) for m in (left,reflected_cross)]
        total=t+c
        return dict(resolution=res,length_um=length,gap_um=gap,width_bias_um=bias,
            wavelength_um=wl,straight_reference=straight,bar=t,cross=c,total=total,
            reflection=r1+r2,reflection_bar=r1,reflection_cross=r2,
            cross_fraction=c/max(total,1e-30),split_error=abs(c/max(total,1e-30)-0.5),
            unaccounted=1-total-r1-r2,
            objective_error=max(abs(t-0.5),abs(c-0.5)))
    finally:
        sim.reset_meep()


def design_key(rows, robust):
    # Same incident-normalized target for both searches; robust minimizes
    # worst case, nominal minimizes nominal error only.
    errors=[r["objective_error"] for r in rows]
    return (max(errors) if robust else errors[0],errors[0],
            rows[0]["length_um"],rows[0]["gap_um"])


def evaluator():
    refs={}
    def evaluate(res,length,gap,scenario):
        bias,wl=scenario
        key=(res,bias,wl)
        if key not in refs:
            refs[key]=reference(*key)
        row=measure(res,length,gap,bias,wl,refs[key])
        print("measurement",json.dumps(row,allow_nan=False),flush=True)
        return row
    return evaluate


def main():
    started=time.monotonic()
    evaluate=evaluator()
    candidates=[]
    for length in LENGTHS:
        for gap in GAPS:
            candidates.append([evaluate(RES[0],length,gap,s) for s in TRAIN])
    designs=choose(candidates)
    validation=[]
    cache={}
    for label,(length,gap) in designs.items():
        for res in RES:
            for scenario in TRAIN+HOLDOUT:
                key=(res,length,gap,scenario)
                if key not in cache:
                    cache[key]=evaluate(res,length,gap,scenario)
                validation.append(dict(design=label,
                    scenario_set="training" if scenario in TRAIN else "holdout",**cache[key]))
    return report_results(candidates,validation,started)


def choose(candidates):
    nominal=min(candidates,key=lambda rows:design_key(rows,False))
    robust=min(candidates,key=lambda rows:design_key(rows,True))
    return {label:(rows[0]["length_um"],rows[0]["gap_um"])
             for label,rows in (("nominal",nominal),("robust",robust))}


def report_results(candidates,validation,started,parallel=None):
    OUT.mkdir(parents=True,exist_ok=True)
    nominal=min(candidates,key=lambda rows:design_key(rows,False))
    robust=min(candidates,key=lambda rows:design_key(rows,True))
    designs=choose(candidates)
    search=[r for rows in candidates for r in rows]
    all_rows=search+validation
    def subset(label,res,group):
        return [r for r in validation if r["design"]==label and
                r["resolution"]==res and r["scenario_set"]==group]
    summary={}
    for label in designs:
        fine=subset(label,RES[-1],"training")
        held=subset(label,RES[-1],"holdout")
        coarse=subset(label,RES[0],"training")
        summary[label]=dict(length_um=designs[label][0],gap_um=designs[label][1],
            nominal=fine[0],worst_training_error=max(r["objective_error"] for r in fine),
            worst_holdout_error=max(r["objective_error"] for r in held),
            worst_split_error=max(r["split_error"] for r in fine+held),
            minimum_transmission=min(r["total"] for r in fine+held),
            maximum_reflection=max(r["reflection"] for r in fine+held),
            max_resolution_total_difference=max(abs(a["total"]-b["total"])
                                                 for a,b in zip(fine,coarse)))
    checks=dict(complete_search=len(search)==len(LENGTHS)*len(GAPS)*len(TRAIN),
        complete_validation=len(validation)==2*len(RES)*(len(TRAIN)+len(HOLDOUT)),
        finite=all(np.isfinite(v) for r in all_rows for v in r.values()
                   if isinstance(v,(int,float))),
        straight_reference=all(abs(r["straight_reference"]-1)<0.02 for r in all_rows),
        physical_sanity=all(r["total"]+r["reflection"]<=1.05 for r in all_rows),
        robust_search_optimal=design_key(robust,True)<=design_key(nominal,True),
        nominal_search_optimal=design_key(nominal,False)<=design_key(robust,False),
        positive_gap=all(r["gap_um"]-r["width_bias_um"]>0 for r in all_rows))
    a,b=summary["nominal"],summary["robust"]
    targets=dict(distinct_robust_design=designs["robust"]!=designs["nominal"],
        improved_fine_training_worst_case=b["worst_training_error"]<a["worst_training_error"],
        improved_fine_holdout_worst_case=b["worst_holdout_error"]<a["worst_holdout_error"],
        worst_split_error_below_5_points=b["worst_split_error"]<0.05,
        minimum_transmission_above_95_percent=b["minimum_transmission"]>0.95,
        maximum_reflection_below_1_percent=b["maximum_reflection"]<0.01,
        resolution_difference_below_3_points=b["max_resolution_total_difference"]<0.03)
    report=dict(experiment="OPA-ID-003",meep_version=mp.__version__,
        config=dict(index=INDEX,width_um=WIDTH,port_offset_um=PORT,bend_length_um=BEND,
            cell_um=CELL,source_x_um=SOURCE_X,left_x_um=LEFT_X,right_x_um=RIGHT_X,
            monitor_span_um=SPAN,resolutions=RES,minimum_run_time=MIN_TIME,
            candidate_lengths_um=LENGTHS,candidate_gaps_um=GAPS,
            training_scenarios=TRAIN,holdout_scenarios=HOLDOUT),
        method="Deterministic parametric inverse design by exhaustive coarse FDTD search; no adjoint/topology optimization.",
        limitations=["Generic 2D Ez dielectric model in air, not the 3D silicon coupler in OPA-COUPLER-003.",
          "Uniform vertical full-width bias with fixed centerlines; not a true normal etch offset, stochastic process or foundry tolerance.",
          "Constant refractive index across wavelength; finite modal monitor spans and possible overlap.",
          "Only lower input excited; no full complex scattering matrix or phase/reciprocity verification.",
          "Unaccounted power is not independently measured radiation. No hardware, GDS or novelty claim."],
        checks=checks,research_targets=targets,summary=summary,search=search,
        validation=validation,elapsed_seconds=time.monotonic()-started)
    if parallel is not None:
        report["parallel_execution"]=parallel
        report.pop("elapsed_seconds")  # aggregation time is not experiment runtime
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    for name,rows in (("search",search),("validation",validation)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(dict(checks=checks,research_targets=targets,summary=summary),indent=2),flush=True)
    return 0 if all(checks.values()) else 1


def identity(row):
    return tuple(row[k] for k in ("resolution","length_um","gap_um",
                                  "width_bias_um","wavelength_um"))


def expected_identity(res,length,gap,scenario):
    return (res,length,gap,*scenario)


def write_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def provenance():
    return dict(workflow_sha=os.environ.get("GITHUB_SHA","local"),
                run_id=os.environ.get("GITHUB_RUN_ID","local"),
                meep_version=mp.__version__)


def read_shards(root,stage,specs):
    """Require exactly one complete shard per planned index, with matching identity."""
    root=Path(root)
    paths=sorted(root.glob("*/shard.json"))
    expected_names={f"id003-{stage}-{i}" for i in range(len(specs))}
    if {p.parent.name for p in paths}!=expected_names:
        raise ValueError(f"Missing or unexpected {stage} shards")
    result=[]
    for i,expected in enumerate(specs):
        data=json.loads((root/f"id003-{stage}-{i}"/"shard.json").read_text())
        if (data["stage"]!=stage or data["index"]!=i
                or data["provenance"]!=provenance()):
            raise ValueError(f"Wrong shard identity/provenance: {stage} {i}")
        rows=data["rows"]
        if [identity(r) for r in rows]!=expected:
            raise ValueError(f"Wrong or incomplete measurements: {stage} {i}")
        result.append(rows)
    return result


def search_specs():
    return [[expected_identity(RES[0],l,g,s) for s in TRAIN]
            for l in LENGTHS for g in GAPS]


def validation_specs(designs):
    # Deduplicate identical winners; each scenario/resolution gets its own job.
    return [[expected_identity(res,l,g,s)] for l,g in sorted(set(designs.values()))
            for res in RES for s in TRAIN+HOLDOUT]


def run_shard(stage,index,specs,path):
    started=time.monotonic()
    evaluate=evaluator()
    rows=[evaluate(res,l,g,(bias,wl)) for res,l,g,bias,wl in specs[index]]
    write_json(path,dict(stage=stage,index=index,provenance=provenance(),
                         elapsed_seconds=time.monotonic()-started,rows=rows))


def cli():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",nargs="?",default="serial",
                        choices=("serial","search","plan","validate","aggregate"))
    parser.add_argument("--index",type=int)
    parser.add_argument("--search-dir",default="search-shards")
    parser.add_argument("--validation-dir",default="validation-shards")
    parser.add_argument("--output",default="shard/shard.json")
    args=parser.parse_args()
    if args.stage=="serial":
        return main()
    if args.stage=="search":
        run_shard("search",args.index,search_specs(),args.output)
        return 0
    candidates=read_shards(args.search_dir,"search",search_specs())
    designs=choose(candidates)
    specs=validation_specs(designs)
    if args.stage=="plan":
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:
            f.write("matrix="+json.dumps({"include":[{"index":i} for i in range(len(specs))]})+"\n")
        return 0
    if args.stage=="validate":
        run_shard("validation",args.index,specs,args.output)
        return 0
    rows=read_shards(args.validation_dir,"validation",specs)
    lookup={identity(r):r for shard in rows for r in shard}
    validation=[dict(design=label,scenario_set="training" if scenario in TRAIN else "holdout",
                     **lookup[expected_identity(res,l,g,scenario)])
                for label,(l,g) in designs.items() for res in RES for scenario in TRAIN+HOLDOUT]
    return report_results(candidates,validation,time.monotonic(),
                          parallel=dict(search_shards=len(candidates),validation_shards=len(rows),
                                        provenance=provenance()))


if __name__=="__main__":
    raise SystemExit(cli())
