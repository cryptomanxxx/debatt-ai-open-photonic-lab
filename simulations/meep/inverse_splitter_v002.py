"""OPA-ID-002: symmetric continuous-material 1x2 splitter, 2D Ez only."""
import csv
import json
from pathlib import Path
import time

import autograd.numpy as npa
import meep as mp
import meep.adjoint as mpa
import numpy as np

OUT = Path("results/opa-id-002")
FREQ = 1/1.55
MIN_TIME = 200
NX, NY = 25, 25
N = NX*NY
L, W = 2.4, 2.4
PORT = 0.65
WIDTH = 0.6
SPAN = 1.15
RES = (30, 60)
PARITY = mp.ODD_Z
ITERATIONS = 16
CORE = mp.Medium(index=1.8)


def simulation(weights, resolution, reference=False):
    geometry = [mp.Block(center=mp.Vector3(-2.5,0),
                         size=mp.Vector3(2.6,WIDTH,mp.inf),material=CORE)]
    if reference:
        geometry = [mp.Block(size=mp.Vector3(mp.inf,WIDTH,mp.inf),material=CORE)]
        region = None
    else:
        for y in (-PORT,PORT):
            geometry.append(mp.Block(center=mp.Vector3(2.5,y),
                size=mp.Vector3(2.6,WIDTH,mp.inf),material=CORE))
        grid = mp.MaterialGrid(mp.Vector3(NX,NY),mp.air,CORE,
            weights=np.asarray(weights).reshape(NX,NY),do_averaging=False)
        region = mpa.DesignRegion(grid,volume=mp.Volume(
            center=mp.Vector3(),size=mp.Vector3(L,W)))
        geometry.append(mp.Block(center=region.center,size=region.size,material=grid))
    sim = mp.Simulation(cell_size=mp.Vector3(7,5),resolution=resolution,
        dimensions=2,boundary_layers=[mp.PML(0.8)],geometry=geometry,
        sources=[mp.EigenModeSource(mp.GaussianSource(FREQ,fwidth=0.4*FREQ),
            center=mp.Vector3(-2.3,0),size=mp.Vector3(0,2),
            eig_parity=mp.EVEN_Y+PARITY)])
    return sim,region


def volume(x,y,span=SPAN):
    return mp.Volume(center=mp.Vector3(x,y),size=mp.Vector3(0,span))


def mode_monitor(sim,x,y,span=SPAN):
    v=volume(x,y,span)
    return sim.add_mode_monitor([FREQ],mp.ModeRegion(center=v.center,size=v.size),
                                yee_grid=True,decimation_factor=1)


def coefficients(sim,monitor):
    return sim.get_eigenmode_coefficients(monitor,[1],eig_parity=PARITY).alpha[0,0,:]


def reference(resolution):
    sim,_=simulation(None,resolution,True)
    try:
        left=mode_monitor(sim,-1.7,0,2)
        right=mode_monitor(sim,1.9,0,2)
        sim.run(until_after_sources=mp.stop_when_dft_decayed(1e-10,MIN_TIME))
        incident=float(abs(coefficients(sim,left)[0])**2)
        transmitted=float(abs(coefficients(sim,right)[0])**2)
        if not np.isfinite(incident) or incident<=0:
            raise RuntimeError("Invalid incident mode power")
        return incident,sim.get_flux_data(left),transmitted/incident
    finally:
        sim.reset_meep()


def evaluate(weights,resolution,incident,gradient=False):
    sim,region=simulation(weights,resolution)
    monitors=[mpa.EigenmodeCoefficient(sim,volume(1.9,y),1,
                eig_parity=PARITY,decimation_factor=1) for y in (-PORT,PORT)]
    def objective(a,b):
        return (npa.abs(a)**2+npa.abs(b)**2)/incident
    opt=mpa.OptimizationProblem(simulation=sim,objective_functions=[objective],
        objective_arguments=monitors,design_regions=[region],frequencies=[FREQ],
        decay_by=1e-10,minimum_run_time=MIN_TIME,decimation_factor=1)
    try:
        value,g=opt([np.asarray(weights)],need_gradient=gradient)
        return float(np.asarray(value).item()),(np.asarray(g).reshape(-1).copy()
                                                if gradient else None)
    finally:
        sim.reset_meep()


def measure(weights,resolution,incident,subtraction):
    sim,_=simulation(weights,resolution)
    try:
        left=mode_monitor(sim,-1.7,0,2)
        sim.load_minus_flux_data(left,subtraction)
        outputs=[mode_monitor(sim,1.9,y) for y in (-PORT,PORT)]
        sim.run(until_after_sources=mp.stop_when_dft_decayed(1e-10,MIN_TIME))
        powers=[float(abs(coefficients(sim,m)[0])**2/incident) for m in outputs]
        reflected=float(abs(coefficients(sim,left)[1])**2/incident)
        total=sum(powers)
        return dict(lower=powers[0],upper=powers[1],total=total,
            reflection=reflected,imbalance=abs(powers[0]-powers[1])/max(total,1e-30),
            unaccounted=1-total-reflected)
    finally:
        sim.reset_meep()


def symmetric(v):
    a=np.asarray(v).reshape(NX,NY)
    return ((a+a[:,::-1])/2).ravel()


def initial_weights():
    x=np.linspace(-L/2,L/2,NX)[:,None]
    y=np.linspace(-W/2,W/2,NY)[None,:]
    center=PORT*(x+L/2)/L
    distance=np.minimum(abs(y-center),abs(y+center))
    return np.where(distance<WIDTH/2,0.8,0.2).ravel()


def gradient_check(w,res,incident):
    value,g=evaluate(w,res,incident,True)
    if g.shape!=(N,) or not np.all(np.isfinite(g)) or np.linalg.norm(g)<1e-10:
        raise RuntimeError("Invalid gradient")
    rng=np.random.default_rng(202)
    directions=[symmetric(np.ones(N)),symmetric(rng.normal(size=N)),
                symmetric(g)]
    records=[]
    for i,d in enumerate(directions):
        d=d/np.linalg.norm(d)
        for h in (0.01,0.005):
            plus,_=evaluate(w+h*d,res,incident)
            minus,_=evaluate(w-h*d,res,incident)
            fd=(plus-minus)/(2*h)
            adj=float(g@d)
            records.append(dict(resolution=res,direction=i,step=h,adjoint=adj,
                finite_difference=fd,scaled_error=float(abs(adj-fd)/np.linalg.norm(g)),
                relative_direction_error=float(abs(adj-fd)/max(abs(adj),abs(fd),1e-12))))
    return records


def main():
    started=time.monotonic()
    OUT.mkdir(parents=True,exist_ok=True)
    initial=initial_weights()
    refs={r:reference(r) for r in RES}
    gradients=[row for r in RES for row in gradient_check(initial,r,refs[r][0])]
    w=initial.copy()
    incident=refs[RES[0]][0]
    history=[]
    for iteration in range(ITERATIONS):
        val,g=evaluate(w,RES[0],incident,True)
        g=symmetric(g)
        if not np.all(np.isfinite(g)):
            raise RuntimeError("Nonfinite optimizer gradient")
        scale=max(np.max(abs(g)),1e-30)
        accepted=False
        for step in (0.15,0.075,0.0375):
            candidate=np.clip(w+step*g/scale,0,1)
            score,_=evaluate(candidate,RES[0],incident)
            if score>val+1e-9:
                w=candidate
                accepted=True
                break
        history.append(dict(iteration=iteration,objective_before=val,
            objective_after=score if accepted else val,accepted=accepted,
            step=step if accepted else 0.0))
        print(history[-1],flush=True)
        if not accepted:
            break
    binary=(w>=0.5).astype(float)
    measurements=[]
    for res in RES:
        inc,sub,straight=refs[res]
        for label,weights in (("initial",initial),("optimized",w),("thresholded",binary)):
            result=measure(weights,res,inc,sub)
            objective,_=evaluate(weights,res,inc)
            measurements.append(dict(resolution=res,design=label,
                straight_reference=straight,adjoint_forward_objective=objective,**result))
    fine={m["design"]:m for m in measurements if m["resolution"]==RES[-1]}
    coarse={m["design"]:m for m in measurements if m["resolution"]==RES[0]}
    checks=dict(normalization_window=MIN_TIME>2*5/(0.1*FREQ),
        gradient_agreement=all(m["scaled_error"]<0.02 for m in gradients),
        gradient_ascent_direction=all(m["relative_direction_error"]<0.05
            for m in gradients if m["direction"]==2),
        finite=all(np.isfinite(v) for m in measurements for v in m.values()
                   if isinstance(v,(int,float))),
        straight_reference=all(abs(m["straight_reference"]-1)<0.02 for m in measurements),
        objective_matches_measurement=all(abs(m["total"]-m["adjoint_forward_objective"])<1e-6
                                         for m in measurements),
        symmetry=bool(np.max(abs(w.reshape(NX,NY)-w.reshape(NX,NY)[:,::-1]))<1e-12),
        optimization_improves=any(h["accepted"] for h in history)
            and fine["optimized"]["total"]>fine["initial"]["total"],
        balanced=fine["optimized"]["imbalance"]<0.05,
        physical_sanity=all(m["total"]+m["reflection"]<=1.05 for m in measurements))
    targets=dict(transmission_above_95_percent=fine["optimized"]["total"]>0.95,
        reflection_below_1_percent=fine["optimized"]["reflection"]<0.01,
        resolution_change_below_3_percent_points=abs(fine["optimized"]["total"]-
            coarse["optimized"]["total"])<0.03)
    report=dict(experiment="OPA-ID-002",meep_version=mp.__version__,
        config=dict(wavelength=1.55,index=1.8,grid=[NX,NY],design_size=[L,W],
            output_offset=PORT,port_width=WIDTH,monitor_span=SPAN,resolutions=RES,
            minimum_run_time=MIN_TIME,iterations=ITERATIONS),
        assumptions=["2D Ez scalar polarization, generic dielectric in air, no foundry stack.",
          "Output powers are local band-1 mode overlaps, normalized to straight input mode.",
          "Finite output monitor span and evanescent overlap may bias modal power; unaccounted is not independently measured radiation.",
          "Thresholded design is diagnostic only, not optimized for fabrication.",
          "Single wavelength, no novelty, fabrication or 3D claim."],
        checks=checks,research_targets=targets,gradient_checks=gradients,
        history=history,measurements=measurements,initial_weights=initial.tolist(),
        optimized_weights=w.tolist(),thresholded_weights=binary.tolist(),
        elapsed_seconds=time.monotonic()-started)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    for name,rows in (("gradient_checks",gradients),("optimization_history",history),
                      ("measurements",measurements)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    np.savetxt(OUT/"optimized_density.csv",w.reshape(NX,NY),delimiter=",")
    print(json.dumps(dict(checks=checks,research_targets=targets),indent=2),flush=True)
    return 0 if all(checks.values()) else 1


if __name__=="__main__":
    raise SystemExit(main())
