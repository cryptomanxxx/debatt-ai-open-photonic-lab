"""OPA-FDTD-009: resolution sensitivity check for 3D dielectric waveguide bends.

Measured aperture flux is not guided-mode transmission and is not a validated
bend loss. The same finite-size source is used in a straight reference.
"""
import json
import math
from pathlib import Path
import resource
import time

import meep as mp

OUT = Path("results/opa-fdtd-009")
OUT.mkdir(parents=True, exist_ok=True)
CELL = mp.Vector3(10, 10, 4)
RESOLUTIONS = (12, 16)
THICKNESS = 0.4
WIDTH = 0.8
INDEX = 1.8
FREQ = 0.8
RADIUS_SET = (1.0, 2.0)
RUN_UNTIL = 80
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


def run_case(radius, resolution):
    """Run the same 3D geometry with a specified grid resolution."""
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
        resolution=resolution,
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
    sim.run(until=RUN_UNTIL)
    incoming = float(mp.get_fluxes(input_monitor)[0])
    outgoing = float(mp.get_fluxes(output_monitor)[0])
    elapsed = time.perf_counter() - start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    sim.reset_meep()
    if not all(map(math.isfinite, (incoming, outgoing))):
        raise ValueError("Non-finite 3D flux at resolution " + str(resolution))
    return {
        "radius_meep_units": radius,
        "resolution": resolution,
        "input_aperture_flux": incoming,
        "output_aperture_flux": outgoing,
        "wall_seconds": elapsed,
        "process_peak_rss_bytes": rss,
    }


measurements = {}
ratios = {}
for resolution in RESOLUTIONS:
    key = str(resolution)
    straight = run_case(None, resolution)
    if straight["input_aperture_flux"] <= 0:
        raise ValueError("Non-positive straight reference input at " + key)
    bends = {str(radius): run_case(radius, resolution) for radius in RADIUS_SET}
    measurements[key] = {"straight": straight, "bends": bends}
    ratios[key] = {
        str(radius): bends[str(radius)]["output_aperture_flux"] /
        straight["input_aperture_flux"]
        for radius in RADIUS_SET
    }

absolute_changes = {
    str(radius): abs(
        ratios[str(RESOLUTIONS[1])][str(radius)] -
        ratios[str(RESOLUTIONS[0])][str(radius)]
    )
    for radius in RADIUS_SET
}
target_tolerance = 0.02
report = {
    "experiment": "OPA-FDTD-009",
    "goal": "Measure spatial-resolution sensitivity of 3D bend aperture ratios",
    "resolutions": list(RESOLUTIONS),
    "cell_meep_units": [CELL.x, CELL.y, CELL.z],
    "duration_meep_units": RUN_UNTIL,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "measurements": measurements,
    "aperture_relative_output_ratios": ratios,
    "absolute_ratio_changes": absolute_changes,
    "target_absolute_change": target_tolerance,
    "within_target": all(value <= target_tolerance for value in absolute_changes.values()),
    "limitations": [
        "Two resolutions do not prove spatial convergence or permit extrapolation to infinite resolution",
        "Ratios are aperture-relative, not guided-mode-specific bend transmission",
        "A fixed-duration run was tested for temporal stability previously at resolution 12 only",
        "No PML-thickness, monitor-position, or source-backaction study",
        "No calibrated LNOI geometry or measured material parameters",
    ],
}
(OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
if not report["within_target"]:
    print("WARNING: spatial-resolution target not yet met; further convergence work needed")
