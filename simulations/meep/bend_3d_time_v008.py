"""OPA-FDTD-008: temporal convergence check for 3D dielectric waveguide bends.

Measured aperture flux is not guided-mode transmission and is not a validated
bend loss. The same finite-size source is used in a straight reference.
"""
import json
import math
from pathlib import Path
import resource
import time

import meep as mp

OUT = Path("results/opa-fdtd-008")
OUT.mkdir(parents=True, exist_ok=True)
CELL = mp.Vector3(10, 10, 4)
RESOLUTION = 12
THICKNESS = 0.4
WIDTH = 0.8
INDEX = 1.8
FREQ = 0.8
RADIUS_SET = (1.0, 2.0)
DURATIONS = (80, 120)
INPUT = mp.FluxRegion(
    center=mp.Vector3(0, -3.0, 0),
    size=mp.Vector3(1.6, 0, 1.0),
    direction=mp.Y,
)
OUTPUT = mp.FluxRegion(
    center=mp.Vector3(3.0, 0, 0),
    size=mp.Vector3(0, 1.6, 1.0),
    direction=mp.X,
)


def bend_polygon(radius):
    centerline = [(0.0, -5.2), (0.0, -radius)]
    for i in range(1, 49):
        theta = math.pi - math.pi * 0.5 * i / 48
        centerline.append((
            radius + radius * math.cos(theta),
            -radius + radius * math.sin(theta),
        ))
    centerline.append((5.2, 0))
    left, right = [], []
    for i, (x, y) in enumerate(centerline):
        ax, ay = centerline[max(0, i - 1)]
        bx, by = centerline[min(len(centerline) - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        left.append(mp.Vector3(x + nx * WIDTH / 2,
                               y + ny * WIDTH / 2, -THICKNESS / 2))
        right.append(mp.Vector3(x - nx * WIDTH / 2,
                                y - ny * WIDTH / 2, -THICKNESS / 2))
    return left + right[::-1]


def run_case(radius):
    """Capture two monitor snapshots in the same Meep run."""
    start = time.perf_counter()
    medium = mp.Medium(index=INDEX)
    if radius is None:
        geometry = [mp.Block(size=mp.Vector3(WIDTH, mp.inf, THICKNESS),
                             material=medium)]
    else:
        geometry = [mp.Prism(vertices=bend_polygon(radius),
                             height=THICKNESS,
                             axis=mp.Vector3(0, 0, 1),
                             material=medium)]
    sim = mp.Simulation(
        cell_size=CELL,
        dimensions=3,
        resolution=RESOLUTION,
        boundary_layers=[mp.PML(1.0)],
        geometry=geometry,
        sources=[mp.Source(
            src=mp.GaussianSource(FREQ, fwidth=0.25),
            component=mp.Ez,
            center=mp.Vector3(0, -3.5, 0),
            size=mp.Vector3(WIDTH, 0, THICKNESS),
        )],
    )
    input_monitor = sim.add_flux(FREQ, 0, 1, INPUT)
    output_monitor = sim.add_flux(FREQ, 0, 1, OUTPUT)
    snapshots = {}
    previous = 0
    for duration in DURATIONS:
        sim.run(until=duration - previous)
        previous = duration
        input_flux = float(mp.get_fluxes(input_monitor)[0])
        output_flux = float(mp.get_fluxes(output_monitor)[0])
        if not all(map(math.isfinite, (input_flux, output_flux))):
            raise ValueError("Non-finite 3D aperture flux")
        snapshots[str(duration)] = {
            "input_aperture_flux": input_flux,
            "output_aperture_flux": output_flux,
            "elapsed_wall_seconds": time.perf_counter() - start,
        }
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    sim.reset_meep()
    return {"radius_meep_units": radius,
            "snapshots": snapshots,
            "process_peak_rss_bytes": peak_rss}


reference = run_case(None)
bends = {str(radius): run_case(radius) for radius in RADIUS_SET}
normalized = {}
for duration in DURATIONS:
    key = str(duration)
    incident = reference["snapshots"][key]["input_aperture_flux"]
    if not math.isfinite(incident) or incident <= 0:
        raise ValueError("Non-positive straight reference incident power")
    normalized[key] = {
        str(radius): bends[str(radius)]["snapshots"][key]["output_aperture_flux"] / incident
        for radius in RADIUS_SET
    }

changes = {
    str(radius): abs(
        normalized[str(DURATIONS[-1])][str(radius)] -
        normalized[str(DURATIONS[0])][str(radius)]
    )
    for radius in RADIUS_SET
}
tolerance = 0.02
report = {
    "experiment": "OPA-FDTD-008",
    "goal": "Check temporal stability of 3D aperture-relative bend flux",
    "durations_meep_units": DURATIONS,
    "cell_meep_units": [CELL.x, CELL.y, CELL.z],
    "resolution": RESOLUTION,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "straight_reference": reference,
    "bend_cases": bends,
    "aperture_relative_output_ratios": normalized,
    "absolute_ratio_changes": changes,
    "temporal_convergence_tolerance": tolerance,
    "limitations": [
        "Temporal stability alone is not physical or spatial convergence",
        "Aperture flux is not mode-resolved guided transmission",
        "Same simple finite source as v007; source back-action is not corrected",
        "No PML, resolution or monitor-position sensitivity study",
        "No fabrication or material stack validation",
    ],
}
(OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
if any(delta > tolerance for delta in changes.values()):
    raise SystemExit("3D bend flux failed temporal convergence tolerance")
