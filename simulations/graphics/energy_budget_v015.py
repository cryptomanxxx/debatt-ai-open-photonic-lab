"""C3B.1 conditional energy budgets. All energy inputs are illustrative."""
import argparse
import csv
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

SCENARIOS=("scale_only","large_scale","noise_only","combined","drift_quantization")
SCENES=("distributed","clustered","anisotropic","translated_boundary")
POLICIES=("electronic_only","all_optical_fallback","raw","max_min_125")
MATCHED=("all_optical_fallback","max_min_125")
FIELDS=("rays","nodes","accepted","leaves","triangles","guards","optical","fallback","sides",
        "driven_operands","extra_nodes","missing_nodes","extra_triangles","missing_triangles",
        "final_fp","final_fn","wrong_id","distance_fail","nearest_not_tested")
QUALITY=("final_fp","final_fn","wrong_id","distance_fail","nearest_not_tested")
GRID=list(itertools.product((10,100,1000),(1,10),(1,10,100),(.01,.1),(.1,1.)))
RATE=1e9


def require(ok,msg):
    if not ok:
        raise ValueError(msg)


def verified(root):
    manifest=json.loads((root/"archive-provenance.json").read_text())
    for name,m in manifest["files"].items():
        b=(root/name).read_bytes()
        require(len(b)==m["bytes"] and hashlib.sha256(b).hexdigest()==m["sha256"]
                and hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==m["git_blob_sha1"],
                "archive digest "+name)
    return json.loads((root/"result.json").read_text())


def budget(n_cpu,n,fb,s,eb,ep,es,power,util):
    # Side-service-only occupancy window, not end-to-end latency.
    # S=0 incurs zero service-window static charge; idle source cost remains unknown.
    static=power*s/(RATE*util)*1e12
    saved=(n_cpu-fb)*eb
    pre=n*ep
    dynamic=s*es
    ceiling=saved-pre-dynamic
    remaining=ceiling-static
    return dict(saved_box_pj=saved,pre_pj=pre,dynamic_side_pj=dynamic,
                static_service_pj=static,optimistic_remaining_pj=ceiling,
                remaining_pj=remaining,
                max_dynamic_side_pj=(saved-pre-static)/s if s else None,
                positive=remaining>0)


def load(c2,fp,cpu):
    original=verified(c2)
    audit=verified(fp)
    timing=verified(cpu)
    require(original["passed"] and original["scientific_gate"],"C2 gate")
    require(audit["passed"] and audit["scientific_gate"] and audit["discrepancies"]==0,"FP64 gate")
    require(timing["passed"] and timing["scientific_gate"] and timing["timing_valid"]
            and timing["discrepancies"]==0,"CPU gate")
    byscene={s["scene"]:s for s in timing["scenes"]}
    require(set(byscene)==set(SCENES),"CPU scenes")
    rows={}
    with (fp/"panels.csv").open(newline="") as f:
        for x in csv.DictReader(f):
            k=(x["scenario"],int(x["repeat"]),x["scene"],x["policy"])
            require(k not in rows,"duplicate panel")
            row={field:int(x[field]) for field in FIELDS}
            require(all(v>=0 for v in row.values()),"negative count")
            rows[k]=row
    require(set(rows)==set(itertools.product(SCENARIOS,range(10),SCENES,POLICIES)),
            "panel coverage")
    sums=defaultdict(Counter)
    for (scenario,rep,scene,policy),row in rows.items():
        sums[scenario,policy].update(row)
        require(row["rays"]==byscene[scene]["rays"],"ray count")
        if policy=="electronic_only":
            require(all(row[k]==v for k,v in byscene[scene]["operations_per_batch"].items()),
                    "CPU work mismatch")
            require(not any(row[k] for k in ("guards","optical","fallback","sides","driven_operands")),
                    "electronic optical work")
        else:
            require(row["nodes"]==row["guards"]+row["optical"] and
                    0<=row["fallback"]<=row["optical"] and
                    2*row["optical"]<=row["sides"]<=6*row["optical"] and
                    row["driven_operands"]==4*row["sides"],"optical counts")
            if policy=="all_optical_fallback":
                require(row["fallback"]==row["optical"],"fallback control")
        if policy!="raw":
            require(original["gates"][policy]["final"] and original["gates"][policy]["node"]
                    and not any(row[k] for k in QUALITY),"matched quality")
            baseline=rows[scenario,rep,scene,"electronic_only"]
            require(all(row[k]==baseline[k] for k in ("rays","nodes","accepted","leaves","triangles"))
                    and not any(row[k] for k in ("extra_nodes","missing_nodes","extra_triangles","missing_triangles")),
                    "matched work")
    require(len(original["summary"])==20,"summary coverage")
    for x in original["summary"]:
        a=sums[x["scenario"],x["policy"]]
        require(all(a[k]==x[k] for k in FIELDS),"C2 aggregate mismatch")
    return rows,byscene


def write_csv(path,rows):
    require(bool(rows),"empty output")
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)


def run(c2,fp,cpu,out):
    rows,byscene=load(c2,fp,cpu)
    counts=[]
    grid=[]
    aggregates=defaultdict(Counter)
    for k,row in sorted(rows.items()):
        scenario,rep,scene,policy=k
        if policy=="raw":
            continue
        base=rows[scenario,rep,scene,"electronic_only"]
        n=row["nodes"]
        counts.append(dict(scenario=scenario,repeat=rep,scene=scene,policy=policy,**row,
                           stack_pushes=n,stack_pops=n,
                           full_box_calls=n if policy=="electronic_only" else row["fallback"],
                           optical_only=row["optical"]-row["fallback"],
                           fallback_fraction=row["fallback"]/row["optical"] if row["optical"] else None,
                           cpu_p50_batch_ns=byscene[scene]["p50_batch_ns"]))
        if policy not in MATCHED:
            continue
        for eb,ep,es,p,u in GRID:
            b=budget(base["nodes"],n,row["fallback"],row["sides"],eb,ep,es,p,u)
            grid.append(dict(scenario=scenario,repeat=rep,scene=scene,policy=policy,
                             e_box_pj=eb,e_pre_pj=ep,e_side_pj=es,static_w=p,utilization=u,
                             side_rate_per_s=RATE,**b,remaining_pj_per_correct_ray=b["remaining_pj"]/row["rays"]))
            a=aggregates[scenario,policy,eb,ep,es,p,u]
            a.update(panels=1,positive_panels=int(b["positive"]),rays=row["rays"],
                     remaining_pj=b["remaining_pj"],optimistic_remaining_pj=b["optimistic_remaining_pj"])
    totals=[]
    for k,a in sorted(aggregates.items()):
        scenario,policy,eb,ep,es,p,u=k
        totals.append(dict(scenario=scenario,policy=policy,e_box_pj=eb,e_pre_pj=ep,e_side_pj=es,
                           static_w=p,utilization=u,side_rate_per_s=RATE,**a,
                           nonpositive_panels=a["panels"]-a["positive_panels"],
                           remaining_pj_per_correct_ray=a["remaining_pj"]/a["rays"]))
    require(len(counts)==600 and len(grid)==400*len(GRID) and len(totals)==10*len(GRID),"grid coverage")
    write_csv(out/"counts.csv",counts)
    write_csv(out/"panel-budgets.csv",grid)
    write_csv(out/"scenario-budgets.csv",totals)
    worst=max(x["fallback_fraction"] for x in counts if x["policy"]=="max_min_125" and x["fallback_fraction"] is not None)
    worst_panels=[{k:x[k] for k in ("scenario","repeat","scene","optical","fallback")}
                  for x in counts if x["policy"]=="max_min_125" and x["fallback_fraction"]==worst]
    return dict(passed=True,stage="C3B.1 conditional energy budgets",energy="not_measured",
                gpu="not_run",matched_panels=len(counts),grid_rows=len(grid),scenario_rows=len(totals),
                worst_fallback_fraction=worst,worst_panels=worst_panels,
                positive_panel_grid_rows=sum(x["positive"] for x in grid),
                nonpositive_panel_grid_rows=sum(not x["positive"] for x in grid),
                equations={"cpu":"C_cpu + N_cpu*e_box",
                           "hybrid":"C_hybrid + F*e_box + N*e_pre + S*e_side + E_static + E_extra",
                           "remaining":"(N_cpu-F)*e_box - N*e_pre - S*e_side - E_static",
                           "condition":"(C_hybrid-C_cpu)+E_extra < remaining for strict savings"},
                assumptions={"e_box_pj":[10,100,1000],"e_pre_pj":[1,10],"e_side_pj":[1,10,100],
                             "incremental_static_w":[.01,.1],"side_rate_per_s":RATE,"utilization":[.1,1]},
                boundaries={"optical_core":"unknown; MZM dynamic energy and optical path loss not measured",
                            "accelerator_card":"unknown; aggregate illustrative side cost includes four drives and readout; static service window only",
                            "host_inclusive":"unknown; common costs and extra memory, scheduling, transfer, calibration and source idle overhead not quantified"},
                limitations=["All energy inputs hypothetical, not inferred from measured CPU time",
                             "Static service window S/(rate*utilization) is not measured latency; extra static time remains unknown",
                             "Positive budget is conditional, not a measured energy advantage; nonpositive budget cannot cover nonnegative extra overhead under the assumed costs",
                             "Raw optical policy excluded for failed quality gate",
                             "Shared costs not assumed equal; actual difference must fit remaining budget",
                             "No physical performance or VR power claims"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("c2",type=Path)
    p.add_argument("fp64",type=Path)
    p.add_argument("cpu",type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    try:
        report=run(a.c2,a.fp64,a.cpu,a.output)
    except Exception as exc:
        report=dict(passed=False,error=str(exc),energy="not_measured")
    (a.output/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
