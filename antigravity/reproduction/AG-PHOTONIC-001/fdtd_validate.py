"""3D FDTD check of straight-pair beating, with an abrupt single-guide launch.

Half-plane flux is a spatial power partition, not isolated output modal power.
Fit launch phase separately rather than attributing it to the straight pair.
"""
import json
import math
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import least_squares

WL=1.55
WIDTH,HEIGHT,GAP=.45,.22,.20
L50=12.28282630189538
POSITIONS=(3.,6.,9.,L50,15.,18.)
RESOLUTIONS=(16,24,32)

def run(res,out):
    import meep as mp
    f=1/WL
    pml=1.0
    # Physical x coordinates relative to onset of the second guide.
    xmin,xmax=-5.,22.
    xc=(xmin+xmax)/2
    cell=mp.Vector3(xmax-xmin,4.65,3.22)
    offset=(WIDTH+GAP)/2
    si=mp.Medium(index=3.48)
    def point(x,y=0):
        return mp.Vector3(x-xc,y,0)
    geometry=[
        mp.Block(center=point(xc,offset),size=mp.Vector3(mp.inf,WIDTH,HEIGHT),material=si),
        mp.Block(center=point(xmax/2,-offset),size=mp.Vector3(xmax,WIDTH,HEIGHT),material=si)]
    sim=mp.Simulation(cell_size=cell,resolution=res,geometry=geometry,
        default_material=mp.Medium(index=1.44),boundary_layers=[mp.PML(pml)],
        symmetries=[mp.Mirror(mp.Z,phase=1)],
        sources=[mp.EigenModeSource(mp.GaussianSource(f,fwidth=.2*f),
            center=point(-3.,offset),size=mp.Vector3(0,2.4,1.22),
            direction=mp.X,eig_band=1,eig_parity=mp.EVEN_Z,eig_match_freq=True)])
    # Monitor the entire non-PML cross section, partitioned at y=0.
    half_y=(cell.y-2*pml)/2
    zspan=cell.z-2*pml
    def flux(x,y,span):
        return sim.add_flux(f,0,1,mp.FluxRegion(center=point(x,y),
                            size=mp.Vector3(0,span,zspan),direction=mp.X))
    incoming=flux(-1.5,0,2*half_y)
    monitors=[(flux(x,half_y/2,half_y),flux(x,-half_y/2,half_y)) for x in POSITIONS]
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        1e-6,minimum_run_time=6*cell.x,maximum_run_time=1000))
    pin=float(mp.get_fluxes(incoming)[0])
    if not math.isfinite(pin) or pin<=0:
        raise ValueError("Invalid net input flux")
    rows=[]
    for x,(a,b) in zip(POSITIONS,monitors):
        through,cross=(float(mp.get_fluxes(m)[0])/pin for m in (a,b))
        total=through+cross
        if not all(map(math.isfinite,(through,cross))) or min(through,cross)<0 or not .85<=total<=1.10:
            raise ValueError(f"Invalid flux at {x}: {through}, {cross}")
        rows.append(dict(x_um=x,through=through,cross=cross,total=total,fraction=cross/total))
    x=np.array(POSITIONS)
    y=np.array([r["fraction"] for r in rows])
    # Free phase and amplitude allow launch imbalance; offset fixed by symmetry.
    def residual(p):
        lc,phase,visibility=p
        return .5-.5*visibility*np.cos(np.pi*x/lc+2*phase)-y
    fit=least_squares(residual,[2*L50,0,.98],bounds=([15,-.5,0],[40,.5,1]))
    lc,phase,visibility=map(float,fit.x)
    report=dict(resolution=res,geometry=dict(width_um=WIDTH,height_um=HEIGHT,gap_um=GAP,
        wavelength_um=WL,n_core=3.48,n_clad=1.44),meep_version=mp.__version__,
        input_net_flux=pin,rows=rows,L50_um=lc/2,phase_rad=phase,visibility=visibility,
        fit_max_residual=float(max(abs(fit.fun))),fit_success=bool(fit.success),
        meep_time=float(sim.meep_time()))
    Path(out).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report),flush=True)

def aggregate(root,out):
    cases=[json.loads((Path(root)/f"fdtd-{r}"/"result.json").read_text()) for r in RESOLUTIONS]
    if [c["resolution"] for c in cases]!=list(RESOLUTIONS):
        raise ValueError("Wrong resolution")
    fine=cases[-1]
    target=next(r for r in fine["rows"] if r["x_um"]==L50)
    checks=dict(fits=all(c["fit_success"] and c["fit_max_residual"]<=.04 and c["visibility"]>=.85 for c in cases),
        fine_matches_mpb=abs(fine["L50_um"]/L50-1)<=.08,
        refinement=abs(fine["L50_um"]/cases[-2]["L50_um"]-1)<=.08,
        near_half=abs(target["fraction"]-.5)<=.08)
    report=dict(mpb_L50_um=L50,cases=cases,checks=checks,passed=all(checks.values()))
    Path(out).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report),flush=True)
    return 0 if report["passed"] else 1

if __name__=="__main__":
    if sys.argv[1]=="case":
        run(int(sys.argv[2]),sys.argv[3])
    elif sys.argv[1]=="aggregate":
        sys.exit(aggregate(sys.argv[2],sys.argv[3]))
    else:
        raise SystemExit("Expected case or aggregate")
