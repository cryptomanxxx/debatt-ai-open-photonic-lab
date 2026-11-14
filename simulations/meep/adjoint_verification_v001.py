"""OPA-ID-001: verify adjoint sensitivities on a small 2D dielectric waveguide region.

A numerical capability test, not an optimized or fabricated photonic component.
"""
import csv
import json
from pathlib import Path
import time
import subprocess
import sys

import autograd.numpy as npa
import meep as mp
import meep.adjoint as mpa
import numpy as np

OUT = Path("results/opa-id-001")
FREQ = 1/1.55
DESIGN_LENGTH = 1.2
DESIGN_WIDTH = 1.0
MONITOR_CENTER_X = 1.5
MONITOR_LENGTH = 0.2
MONITOR_WIDTH = 0.6
NX, NY = 13, 11
N = NX*NY
RESOLUTIONS = (30,60)
EPS = (0.01,0.005)
REL_TOL = 0.15
# Meep v1.35.1 normalizes its adjoint Gaussian using the forward run time.
# Its single-frequency pulse has cutoff=5 and fwidth=0.1*FREQ, hence
# full duration 2*5/(0.1*FREQ) = 155 Meep time units.
ADJOINT_PULSE_DURATION = 2*5/(0.1*FREQ)
MIN_RUN_TIME = 200


def evaluate(weights, resolution, gradient=False, objective_kind='mean', minimum_run_time=MIN_RUN_TIME):
    # Use a nondegenerate 2D MaterialGrid and transverse Ez, following
    # the geometry class exercised by Meep's upstream adjoint DFT tests.
    core = mp.Medium(index=1.8)
    grid = mp.MaterialGrid(mp.Vector3(NX,NY),mp.air,core,
                           weights=np.asarray(weights).reshape(NX,NY),
                           do_averaging=False)
    region = mpa.DesignRegion(grid,volume=mp.Volume(
        center=mp.Vector3(),size=mp.Vector3(DESIGN_LENGTH,DESIGN_WIDTH)))
    sim = mp.Simulation(cell_size=mp.Vector3(5,4),dimensions=2,
        resolution=resolution,boundary_layers=[mp.PML(0.8)],
        geometry=[mp.Block(size=mp.Vector3(mp.inf,0.6,mp.inf),material=core),
                  mp.Block(size=region.size,center=region.center,material=grid)],
        sources=[mp.EigenModeSource(mp.GaussianSource(FREQ,fwidth=0.4*FREQ),
                   center=mp.Vector3(-1.5,0),size=mp.Vector3(0,2.0),
                   eig_parity=mp.EVEN_Y+mp.ODD_Z)])
    monitor = mpa.FourierFields(sim,volume=mp.Volume(
        center=mp.Vector3(MONITOR_CENTER_X,0),
        size=mp.Vector3(MONITOR_LENGTH,MONITOR_WIDTH)),component=mp.Ez,
        yee_grid=False,decimation_factor=1)
    def objective(field):
        if objective_kind == 'sample':
            # Upstream DFT test selects one spatial sample, retaining frequency axis.
            return npa.abs(field[:,field.shape[1]//2,field.shape[2]//2])**2
        return npa.mean(npa.abs(field)**2)
    opt = mpa.OptimizationProblem(simulation=sim,objective_functions=[objective],
        objective_arguments=[monitor],design_regions=[region],
        frequencies=[FREQ],decay_by=1e-10,minimum_run_time=minimum_run_time,
        decimation_factor=1)
    try:
        value,grad = opt([np.asarray(weights)],need_gradient=gradient)
        if np.asarray(monitor._eval).size <= 1:
            raise RuntimeError("FourierFields monitor must sample multiple spatial points")
        return float(np.asarray(value).item()), (np.asarray(grad).reshape(-1).copy()
                                                if gradient else None)
    finally:
        sim.reset_meep()


def main():
    started = time.monotonic()
    OUT.mkdir(parents=True,exist_ok=True)
    reference_dir = Path(__file__).resolve().parent / 'upstream_adjoint'
    command = [sys.executable, '-m', 'unittest', '-v',
               'test_adjoint_solver.TestAdjointSolver.test_DFT_fields']
    print('Running unmodified upstream Meep DFT adjoint reference test', flush=True)
    with (OUT/'upstream_reference.log').open('w') as log:
        reference = subprocess.run(command, cwd=reference_dir, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=600, check=False)
    print(f'Upstream reference exit code: {reference.returncode}', flush=True)
    weights = 0.45+0.12*np.sin(np.linspace(0,2*np.pi,N))
    rng = np.random.default_rng(101)
    directions = [np.ones(N), rng.normal(size=N), np.cos(np.linspace(0,2*np.pi,N))]
    directions = [v/np.linalg.norm(v) for v in directions]
    records, runs = [], []
    for resolution in RESOLUTIONS:
        print(f"Resolution {resolution}: adjoint calculation",flush=True)
        val,g = evaluate(weights,resolution,True)
        if g.shape != weights.shape or not np.all(np.isfinite(g)):
            raise RuntimeError("Invalid adjoint gradient")
        scale = max(np.linalg.norm(g),1e-30)
        for i,d in enumerate(directions):
            adj = float(g@d)
            for h in EPS:
                plus,_ = evaluate(weights+h*d,resolution)
                minus,_ = evaluate(weights-h*d,resolution)
                fd = (plus-minus)/(2*h)
                records.append(dict(resolution=resolution,direction=i,step=h,
                    adjoint=adj,finite_difference=fd,
                    scaled_error=float(abs(adj-fd)/scale)))
            print(f"  direction {i+1}/{len(directions)} checked",flush=True)
        # Fixed small gradient-ascent step, evaluated by independent forward run.
        candidate = np.clip(weights+0.02*g/scale,0,1)
        improved,_ = evaluate(candidate,resolution)
        runs.append(dict(resolution=resolution,objective=val,
            gradient_norm=float(np.linalg.norm(g)),gradient=g.tolist(),
            candidate_weights=candidate.tolist(),candidate_objective=improved,
            ascent_gain=improved-val))
    # Diagnostic only: reproduce short forward run versus full normalization window.
    # Preserve the original mean-objective acceptance gate.
    diagnostic = []
    resolution = RESOLUTIONS[-1]
    for kind, duration in (("mean",20),("sample",MIN_RUN_TIME)):
        value, g = evaluate(weights,resolution,True,kind,duration)
        for i,d in enumerate(directions):
            h = EPS[-1]
            plus,_ = evaluate(weights+h*d,resolution,False,kind,duration)
            minus,_ = evaluate(weights-h*d,resolution,False,kind,duration)
            fd = (plus-minus)/(2*h)
            adj = float(g@d)
            diagnostic.append(dict(objective=kind,minimum_run_time=duration,resolution=resolution,direction=i,
                step=h,adjoint=adj,finite_difference=fd,
                scaled_error=float(abs(adj-fd)/max(np.linalg.norm(g),1e-30))))
    print("Objective and normalization-window diagnostics:",json.dumps(diagnostic),flush=True)
    fine = [r for r in records if r["resolution"]==RESOLUTIONS[-1] and r["step"]==EPS[-1]]
    checks = dict(upstream_reference_passes=reference.returncode==0,
        normalization_window_covers_adjoint_pulse=MIN_RUN_TIME>ADJOINT_PULSE_DURATION,
        all_directions=len(records)==len(RESOLUTIONS)*len(directions)*len(EPS),
        finite=all(np.isfinite(r[k]) for r in records for k in ("adjoint","finite_difference","scaled_error"))
            and all(np.isfinite(r[k]) for r in runs for k in ("objective","gradient_norm","candidate_objective")),
        nonzero_gradient=all(r["gradient_norm"]>1e-10 for r in runs),
        fine_directional_agreement=max(r["scaled_error"] for r in fine)<REL_TOL,
        fine_ascent_improves=runs[-1]["ascent_gain"]>0)
    report=dict(experiment="OPA-ID-001",meep_version=mp.__version__,numpy_version=np.__version__,
        config=dict(frequency=FREQ,wavelength=1.55,design_length=DESIGN_LENGTH,
            weights=N,resolutions=RESOLUTIONS,steps=EPS,scaled_error_tolerance=REL_TOL,
            minimum_run_time=MIN_RUN_TIME,adjoint_pulse_duration=ADJOINT_PULSE_DURATION,
            design_width=DESIGN_WIDTH,design_grid=[NX,NY],monitor_center_x=MONITOR_CENTER_X,
            monitor_length=MONITOR_LENGTH,monitor_width=MONITOR_WIDTH,
            objective="mean_squared_fourier_Ez_over_monitor_samples"),
        assumptions=["2D dielectric waveguide with continuous material grid in air; no foundry model.",
            "Objective is the unnormalized mean squared Fourier Ez over interpolated field samples in a 0.2 x 0.6 um rectangle, not transmission efficiency.",
            "Continuous grayscale material weights; no binary geometry or fabrication claim.",
            "Finite differences use independently rebuilt forward simulations.",
            "Directional error normalized by full adjoint gradient norm; not componentwise relative error."],
        upstream_reference=dict(tag='v1.35.1',test=command[-1],exit_code=reference.returncode,
            log='upstream_reference.log'),
        initial_weights=weights.tolist(),directions=[d.tolist() for d in directions],
        checks=checks,measurements=records,runs=runs,objective_diagnostics=diagnostic,elapsed_seconds=time.monotonic()-started)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (OUT/"gradient_checks.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps(checks,indent=2),flush=True)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
