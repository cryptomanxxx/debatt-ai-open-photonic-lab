"""OPA-ID-004: fourfold-symmetric inverse-designed crossing, generic 2D Ez."""
import csv
import json
from pathlib import Path
import time

import autograd.numpy as npa
import meep as mp
import meep.adjoint as mpa
import numpy as np

from opa_common import write_report

OUT = Path("results/opa-id-004")
SIZE = 2.4
N = 25
WIDTH = 0.6
SPAN = 1.8
INDEX = 1.8
CORE = mp.Medium(index=INDEX)
PARITY = mp.ODD_Z
RES = (30, 60)
WL = 1.55
MIN_TIME = 200
ITERATIONS = 10
# Monitor positions are outside the design, away from PML and source.
PORTS = {"west": (-2., 0.), "east": (2., 0.),
         "north": (0., 2.), "south": (0., -2.)}


def symmetric(w):
    a = np.asarray(w).reshape(N, N)
    rotations = [np.rot90(a, k) for k in range(4)]
    b = sum(rotations + [v[::-1, :] for v in rotations]) / 8
    return b.ravel()


def seed(binary=False):
    # Integer distances from the grid centre prevent asymmetric rounding
    # at nominal +/- WIDTH/2. Exclude boundary nodes consistently.
    offsets = abs(2*np.arange(N) - (N-1))
    distance = np.minimum(offsets[:, None], offsets[None, :])
    cross = distance < (WIDTH*(N-1)/SIZE - 1e-12)
    return np.where(cross, 1. if binary else .8,
                    0. if binary else .2).ravel()


def port_volume(port):
    x, y = PORTS[port]
    return mp.Volume(center=mp.Vector3(x, y),
                     size=mp.Vector3(0, SPAN) if x else mp.Vector3(SPAN, 0))


def simulation(w, res, wl, source_axis="x", reference=False):
    f = 1/wl
    if source_axis not in ("x", "y"):
        raise ValueError("Unsupported source axis")
    horizontal = source_axis == "x"
    direction = mp.X if horizontal else mp.Y
    source = mp.Vector3(-2.7, 0) if horizontal else mp.Vector3(0, -2.7)
    source_size = mp.Vector3(0, SPAN) if horizontal else mp.Vector3(SPAN, 0)
    # MPB exposes EVEN_Y and EVEN_Z, not EVEN_X. For y propagation,
    # select the fundamental band without an in-plane parity constraint.
    parity = mp.EVEN_Y + PARITY if horizontal else PARITY
    region = None
    if reference:
        geom = [mp.Block(size=mp.Vector3(mp.inf, WIDTH, mp.inf) if horizontal
                         else mp.Vector3(WIDTH, mp.inf, mp.inf), material=CORE)]
    else:
        # Lead blocks extend through PML and overlap the grid by 0.1 um.
        geom = []
        for sign in (-1, 1):
            geom.extend([
                mp.Block(center=mp.Vector3(sign*2.6, 0),
                         size=mp.Vector3(3, WIDTH, mp.inf), material=CORE),
                mp.Block(center=mp.Vector3(0, sign*2.6),
                         size=mp.Vector3(WIDTH, 3, mp.inf), material=CORE)])
        grid = mp.MaterialGrid(mp.Vector3(N, N), mp.air, CORE,
                               weights=np.asarray(w).reshape(N, N),
                               do_averaging=False)
        region = mpa.DesignRegion(grid, volume=mp.Volume(
            center=mp.Vector3(), size=mp.Vector3(SIZE, SIZE)))
        geom.append(mp.Block(center=region.center, size=region.size, material=grid))
    sim = mp.Simulation(cell_size=mp.Vector3(8, 8), resolution=res,
        dimensions=2, boundary_layers=[mp.PML(.8)], geometry=geom,
        sources=[mp.EigenModeSource(mp.GaussianSource(f, fwidth=.4*f),
            center=source, size=source_size, direction=direction, eig_parity=parity)])
    return sim, region


def monitor(sim, port, wl):
    v = port_volume(port)
    return sim.add_mode_monitor([1/wl], mp.ModeRegion(center=v.center, size=v.size),
                               yee_grid=True, decimation_factor=1)


def port_power(sim, mon, port, wl, outgoing=True):
    # Use the same signed MPB k-point convention as Meep 1.35.1's
    # EigenmodeCoefficient, but in an independent direct FDTD run.
    # The default positive-k solve's alpha[1] is not numerically identical
    # to solving the negative-k mode and reading alpha[0].
    x, y = PORTS[port]
    sign = (1 if x+y > 0 else -1) * (1 if outgoing else -1)
    k = mp.Vector3(sign/wl, 0) if x else mp.Vector3(0, sign/wl)
    coeff = sim.get_eigenmode_coefficients(mon, [1], eig_parity=PARITY,
        direction=mp.NO_DIRECTION, kpoint_func=lambda *_: k)
    return float(abs(coeff.alpha[0,0,0])**2)


def run(sim):
    sim.run(until_after_sources=mp.stop_when_dft_decayed(1e-10, MIN_TIME))


def reference(res, wl, axis):
    sim, _ = simulation(None, res, wl, axis, True)
    input_port, output_port = ("west", "east") if axis == "x" else ("south", "north")
    try:
        left, right = [monitor(sim, p, wl) for p in (input_port, output_port)]
        run(sim)
        inc = port_power(sim, left, input_port, wl, outgoing=False)
        if not np.isfinite(inc) or inc <= 0:
            raise RuntimeError("Invalid incident reference")
        return inc, sim.get_flux_data(left), port_power(sim, right, output_port, wl)/inc
    finally:
        sim.reset_meep()


def objective(w, res, incident, gradient=False):
    sim, region = simulation(w, res, WL)
    monitors = [mpa.EigenmodeCoefficient(sim, port_volume(p), 1,
        forward=(p != "south"), eig_parity=PARITY, decimation_factor=1)
        for p in ("east", "north", "south")]

    def score(t, c1, c2):
        return (npa.abs(t)**2 - npa.abs(c1)**2 - npa.abs(c2)**2)/incident

    opt = mpa.OptimizationProblem(simulation=sim, objective_functions=[score],
        objective_arguments=monitors, design_regions=[region], frequencies=[1/WL],
        decay_by=1e-10, minimum_run_time=MIN_TIME, decimation_factor=1)
    try:
        val, g = opt([np.asarray(w)], need_gradient=gradient)
        return float(np.asarray(val).item()), (np.asarray(g).reshape(-1).copy()
                                                if gradient else None)
    finally:
        sim.reset_meep()


def measure(w, res, wl, axis, ref):
    inc, subtraction, straight = ref
    sim, _ = simulation(w, res, wl, axis)
    src, dst, side1, side2 = (("west", "east", "north", "south") if axis == "x"
                             else ("south", "north", "east", "west"))
    try:
        monitors = {p: monitor(sim, p, wl) for p in PORTS}
        sim.load_minus_flux_data(monitors[src], subtraction)
        run(sim)
        def outgoing(p):
            return port_power(sim, monitors[p], p, wl)/inc
        t, c1, c2, r = map(outgoing, (dst, side1, side2, src))
        return dict(resolution=res, wavelength_um=wl, axis=axis,
            straight_reference=straight, transmission=t, crosstalk_1=c1,
            crosstalk_2=c2, crosstalk=c1+c2, reflection=r,
            unaccounted=1-t-c1-c2-r, objective=t-c1-c2)
    finally:
        sim.reset_meep()


def gradient_checks(w, res, inc):
    _, g = objective(w, res, inc, True)
    if g.shape != (N*N,) or not np.all(np.isfinite(g)) or np.linalg.norm(g) < 1e-10:
        raise RuntimeError("Invalid gradient")
    rng = np.random.default_rng(404)
    rows = []
    for i, d in enumerate((symmetric(rng.normal(size=N*N)), symmetric(g))):
        d = d/np.linalg.norm(d)
        for h in (.01, .005):
            plus, _ = objective(w+h*d, res, inc)
            minus, _ = objective(w-h*d, res, inc)
            fd, adj = (plus-minus)/(2*h), float(g@d)
            rows.append(dict(resolution=res, direction=i, step=h, adjoint=adj,
                finite_difference=fd,
                scaled_error=float(abs(fd-adj)/np.linalg.norm(g)),
                relative_error=float(abs(fd-adj)/max(abs(fd),abs(adj),1e-12))))
    return rows


def main():
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    refs = {}
    def ref(res, wl=WL, axis="x"):
        key = res, wl, axis
        if key not in refs:
            refs[key] = reference(*key)
        return refs[key]

    # Validate both launch directions before expensive optimization.
    ref(RES[0])
    ref(RES[-1], WL, "y")
    initial = seed()
    # Early diagnostic on the plain crossing, whose side-port power is
    # substantial. Keep the original 1e-6 agreement criterion.
    for res in RES:
        direct = measure(seed(True), res, WL, "x", ref(res))
        adj, _ = objective(seed(True), res, ref(res)[0])
        print("objective preflight", json.dumps(dict(resolution=res,
            direct=direct["objective"], adjoint=adj,
            difference=abs(direct["objective"]-adj))), flush=True)
        if abs(direct["objective"]-adj) >= 1e-6:
            raise RuntimeError("Direct/adjoint objective preflight mismatch")
    w = initial.copy()
    gradients = [row for res in RES
                 for row in gradient_checks(initial, res, ref(res)[0])]
    inc = ref(RES[0])[0]
    history = []
    for i in range(ITERATIONS):
        val, g = objective(w, RES[0], inc, True)
        g = symmetric(g)
        if not np.all(np.isfinite(g)):
            raise RuntimeError("Nonfinite projected gradient")
        accepted = False
        for step in (.15, .075, .0375):
            candidate = symmetric(np.clip(w+step*g/max(np.max(abs(g)),1e-30),0,1))
            score, _ = objective(candidate, RES[0], inc)
            if score > val+1e-9:
                w = candidate
                accepted = True
                break
        history.append(dict(iteration=i, objective_before=val,
            objective_after=score if accepted else val,
            accepted=accepted, step=step if accepted else 0.))
        print(history[-1], flush=True)
        if not accepted:
            break

    # Symmetrize before binarizing; exact orbit values avoid tie asymmetry.
    def binary(w):
        a = np.asarray(w).reshape(N,N)
        out = np.empty_like(a)
        for i in range(N):
            for j in range(N):
                orbit = {(i,j),(j,i),(N-1-i,j),(i,N-1-j),
                    (N-1-j,i),(j,N-1-i),(N-1-i,N-1-j),(N-1-j,N-1-i)}
                value = float(np.mean([a[k,l] for k,l in sorted(orbit)]) >= .5)
                for k,l in orbit:
                    out[k,l] = value
        return out.ravel()

    designs = {"plain_cross": seed(True), "initial": initial,
               "optimized": w, "thresholded": binary(w)}
    # Fail before measuring a mislabeled baseline or thresholded design.
    for label in ("plain_cross", "thresholded"):
        if not np.all(np.isin(designs[label], (0., 1.))):
            raise RuntimeError(f"{label} must contain only binary weights")
    rows = []
    for res in RES:
        for label, weights in designs.items():
            m = measure(weights, res, WL, "x", ref(res))
            score, _ = objective(weights, res, ref(res)[0])
            rows.append(dict(design=label, adjoint_forward_objective=score, **m))
    # Independent orthogonal excitation, plus held-out wavelength checks.
    for axis, wl in (("y", WL), ("x", 1.53), ("x", 1.57)):
        for label in ("plain_cross", "optimized", "thresholded"):
            m = measure(designs[label], RES[-1], wl, axis, ref(RES[-1],wl,axis))
            rows.append(dict(design=label, adjoint_forward_objective=None, **m))
    nominal = {(m["resolution"],m["design"]):m for m in rows
               if m["wavelength_um"]==WL and m["axis"]=="x"}
    fine = nominal[RES[-1],"optimized"]
    coarse = nominal[RES[0],"optimized"]
    base = nominal[RES[-1],"plain_cross"]
    initial_fine = nominal[RES[-1],"initial"]
    orthogonal = next(m for m in rows if m["axis"]=="y" and m["design"]=="optimized")
    checks = dict(
        complete=len(rows)==17 and len(gradients)==8,
        normalization_window=MIN_TIME>2*5/(.1/WL),
        gradient_agreement=all(m["scaled_error"]<.02 for m in gradients),
        ascent_direction=all(m["relative_error"]<.05 for m in gradients if m["direction"]==1),
        finite=all(np.isfinite(v) for m in rows+gradients for v in m.values()
                   if isinstance(v,(int,float))),
        straight_reference=all(abs(m["straight_reference"]-1)<.02 for m in rows),
        objective_agreement=all(abs(m["objective"]-m["adjoint_forward_objective"])<1e-6
                                for m in rows if m["adjoint_forward_objective"] is not None),
        symmetry=all(np.max(abs(v-symmetric(v)))<1e-12 for v in designs.values()),
        binary_designs=all(np.all(np.isin(designs[k], (0., 1.)))
                           for k in ("plain_cross", "thresholded")),
        seed_geometry=bool(np.array_equal(designs["plain_cross"],
                                        (initial > .5).astype(float))),
        physical_sanity=all(0<=m["transmission"]+m["crosstalk"]+m["reflection"]<=1.05
                            for m in rows),
        accepted_steps_monotonic=all(h["objective_after"]>=h["objective_before"] for h in history))
    targets = dict(
        optimized_improves_initial=fine["objective"]>initial_fine["objective"],
        optimized_improves_plain_cross=fine["objective"]>base["objective"],
        transmission_above_95_percent=fine["transmission"]>.95,
        summed_crosstalk_below_1_percent=fine["crosstalk"]<.01,
        reflection_below_1_percent=fine["reflection"]<.01,
        resolution_change_below_3_points=abs(fine["transmission"]-coarse["transmission"])<.03,
        orthogonal_transmission_agreement=abs(fine["transmission"]-orthogonal["transmission"])<.03)
    report = dict(experiment="OPA-ID-004", meep_version=mp.__version__,
        config=dict(index=INDEX, design_size_um=SIZE, port_width_um=WIDTH,
                    density_grid=[N,N], wavelength_um=WL, resolutions=RES,
                    minimum_run_time=MIN_TIME, iterations=ITERATIONS),
        assumptions=["Generic 2D Ez dielectric in air, no foundry stack.",
            "Continuous density optimization at one wavelength; thresholding is diagnostic.",
            "Band-1 port powers normalized to straight incident power, not aperture flux.",
            "Unaccounted power is not independently measured radiation.",
            "No fabrication tolerance, coherent multi-input, full S matrix, 3D or novelty claim."],
        checks=checks,research_targets=targets,gradient_checks=gradients,
        history=history,measurements=rows,
        weights={k:v.tolist() for k,v in designs.items()},
        elapsed_seconds=time.monotonic()-start)
    for name, records in (("gradient_checks",gradients),("optimization_history",history),
                          ("measurements",rows)):
        with (OUT/(name+".csv")).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    np.savetxt(OUT/"optimized_density.csv",w.reshape(N,N),delimiter=",")
    # Shared helper serializes native types; convert numpy booleans explicitly.
    report["checks"] = {k:bool(v) for k,v in checks.items()}
    report["research_targets"] = {k:bool(v) for k,v in targets.items()}
    json.dumps(report,allow_nan=False)
    write_report(OUT,report)
    return 0 if all(checks.values()) else 1


if __name__=="__main__":
    raise SystemExit(main())
