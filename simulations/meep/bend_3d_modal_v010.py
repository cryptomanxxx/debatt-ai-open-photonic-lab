"""OPA-FDTD-010: exploratory 3D guided-mode output power in two bends.

Measured aperture flux is not guided-mode transmission and is not a validated
bend loss. The same finite-size source is used in a straight reference.
"""
import json
import math
from pathlib import Path
import resource
import time

import meep as mp

OUT = Path("results/opa-fdtd-010")
OUT.mkdir(parents=True, exist_ok=True)
CELL = mp.Vector3(10, 10, 4)
RESOLUTION = 12
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


def run_case(radius):
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
    incident_monitor = sim.add_mode_monitor(FREQ, 0, 1, INPUT)
    output_monitor = sim.add_mode_monitor(FREQ, 0, 1, OUTPUT)
    sim.run(until=RUN_UNTIL)
    incident = float(mp.get_fluxes(incident_monitor)[0])
    outgoing = float(mp.get_fluxes(output_monitor)[0])
    input_coefficients = sim.get_eigenmode_coefficients(
        incident_monitor, [1], eig_parity=mp.NO_PARITY
    ).alpha[0, 0]
    output_coefficients = sim.get_eigenmode_coefficients(
        output_monitor, [1], eig_parity=mp.NO_PARITY
    ).alpha[0, 0]
    input_forward_guided = float(abs(input_coefficients[0]) ** 2)
    input_backward_guided = float(abs(input_coefficients[1]) ** 2)
    output_forward_guided = float(abs(output_coefficients[0]) ** 2)
    output_backward_guided = float(abs(output_coefficients[1]) ** 2)
    elapsed = time.perf_counter() - start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    sim.reset_meep()
    if not all(map(math.isfinite, (incident, outgoing, input_forward_guided,
                                 output_forward_guided, input_backward_guided,
                                 output_backward_guided))):
        raise ValueError("Non-finite flux")
    return {
        "radius_meep_units": radius,
        "input_aperture_flux": incident,
        "output_aperture_flux": outgoing,
        "input_forward_band1_power": input_forward_guided,
        "input_backward_band1_power": input_backward_guided,
        "output_forward_band1_power": output_forward_guided,
        "output_backward_band1_power": output_backward_guided,
        "elapsed_wall_seconds": elapsed,
        "process_peak_rss_bytes": rss,
    }


reference = run_case(None)
if reference["input_aperture_flux"] <= 0 or reference["input_forward_band1_power"] <= 0:
    raise SystemExit("Straight reference had non-positive incident modal or aperture power")
cases = {}
for radius in RADIUS_SET:
    case = run_case(radius)
    case["output_flux_over_straight_input"] = (
        case["output_aperture_flux"] / reference["input_aperture_flux"]
    )
    case["output_forward_band1_over_straight_input_band1"] = (
        case["output_forward_band1_power"] / reference["input_forward_band1_power"]
    )
    cases[str(radius)] = case

report = {
    "experiment": "OPA-FDTD-010",
    "model": "Illustrative 3D dielectric slab in air; not an LNOI stack",
    "cell_meep_units": [CELL.x, CELL.y, CELL.z],
    "resolution": RESOLUTION,
    "core_width_meep_units": WIDTH,
    "core_thickness_meep_units": THICKNESS,
    "core_refractive_index": INDEX,
    "run_until_meep_units": RUN_UNTIL,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "straight_reference": reference,
    "bend_cases": cases,
    "limitations": [
        "Finite-size source launches an unknown mix of modes, even though band-1 modal coefficients are measured",
        "Aperture flux includes radiation and possibly other modes; band 1 requires independent guided-mode classification",
        "Reference input flux does not correct source back-action in bends",
        "Previous temporal/spatial tests covered aperture flux only, not band-1 modal power convergence",
        "Output ratio is not a physical bend-loss or energy-efficiency measurement",
    ],
}
(OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
