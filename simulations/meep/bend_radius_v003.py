"""OPA-FDTD-003: exploratory 2D 90-degree bend-radius sweep.

Illustrative dielectric slab waveguide; not calibrated to the lnoi400 PDK.
Flux values are aperture-relative and cannot be interpreted as bend loss in dB/cm.
"""
import json
import math
from pathlib import Path

import meep as mp

OUTPUT = Path("results/opa-fdtd-003")
OUTPUT.mkdir(parents=True, exist_ok=True)

FREQ = 0.8
BANDWIDTH = 0.2
INDEX = 1.8
WIDTH = 0.8
RESOLUTION = 18
RADII = (1.0, 2.0)
DURATIONS = (160, 220)
CELL = mp.Vector3(9, 9, 0)
SOURCE = mp.Vector3(0, -3.0)
IN_REGION = mp.FluxRegion(center=mp.Vector3(0, -2.6), size=mp.Vector3(2, 0), direction=mp.Y)
OUT_REGION = mp.FluxRegion(center=mp.Vector3(2.6, 0), size=mp.Vector3(0, 2), direction=mp.X)


def curved_polygon(radius):
    """Polygonal constant-width centerline with vertical and horizontal leads."""
    centerline = [(0.0, -3.3), (0.0, -radius)]
    for step in range(1, 33):
        theta = math.pi - (math.pi / 2) * step / 32
        centerline.append((radius + radius * math.cos(theta),
                           -radius + radius * math.sin(theta)))
    centerline.append((3.3, 0.0))
    left, right = [], []
    for i, (x, y) in enumerate(centerline):
        ax, ay = centerline[max(0, i - 1)]
        bx, by = centerline[min(len(centerline) - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        nx, ny = -dy / norm, dx / norm
        left.append(mp.Vector3(x + nx * WIDTH / 2, y + ny * WIDTH / 2))
        right.append(mp.Vector3(x - nx * WIDTH / 2, y - ny * WIDTH / 2))
    return left + list(reversed(right))


def simulation(radius=None):
    if radius is None:
        geometry = [mp.Block(size=mp.Vector3(WIDTH, mp.inf, mp.inf),
                             material=mp.Medium(index=INDEX))]
    else:
        geometry = [mp.Prism(vertices=curved_polygon(radius),
                             height=mp.inf, material=mp.Medium(index=INDEX))]
    return mp.Simulation(
        cell_size=CELL,
        dimensions=2,
        resolution=RESOLUTION,
        boundary_layers=[mp.PML(1.0)],
        geometry=geometry,
        sources=[mp.Source(mp.GaussianSource(FREQ, fwidth=BANDWIDTH),
                           component=mp.Ez, center=SOURCE,
                           size=mp.Vector3(WIDTH, 0))],
    )


def run_reference(duration):
    sim = simulation()
    incident = sim.add_flux(FREQ, 0, 1, IN_REGION)
    sim.run(until=duration)
    power = float(mp.get_fluxes(incident)[0])
    fields = sim.get_flux_data(incident)
    sim.reset_meep()
    if not math.isfinite(power) or power <= 0:
        raise ValueError(f"Invalid incident reference power: {power}")
    return power, fields


def run_bend(radius, duration, power, fields):
    sim = simulation(radius)
    reflected = sim.add_flux(FREQ, 0, 1, IN_REGION)
    transmitted = sim.add_flux(FREQ, 0, 1, OUT_REGION)
    sim.load_minus_flux_data(reflected, fields)
    sim.run(until=duration)
    reflected_flux = float(mp.get_fluxes(reflected)[0])
    output_flux = float(mp.get_fluxes(transmitted)[0])
    sim.reset_meep()
    if not all(map(math.isfinite, (reflected_flux, output_flux))):
        raise ValueError("Non-finite flux in bend simulation")
    return {
        "radius_meep_units": radius,
        "duration_meep_units": duration,
        "incident_reference_flux": power,
        "scattered_reflection_flux": reflected_flux,
        "output_aperture_flux": output_flux,
        "aperture_relative_reflection_ratio": -reflected_flux / power,
        "aperture_relative_transmission_ratio": output_flux / power,
    }


results = {}
for duration in DURATIONS:
    power, fields = run_reference(duration)
    results[str(duration)] = {
        str(radius): run_bend(radius, duration, power, fields)
        for radius in RADII
    }

tol = 0.02
changes = {}
for radius in RADII:
    key = str(radius)
    early = results[str(DURATIONS[0])][key]
    late = results[str(DURATIONS[1])][key]
    changes[key] = {
        metric: abs(late[metric] - early[metric])
        for metric in ("aperture_relative_reflection_ratio",
                       "aperture_relative_transmission_ratio")
    }

report = {
    "experiment": "OPA-FDTD-003",
    "model": "2D illustrative index-guided 90-degree bends",
    "is_lnoi400_model": False,
    "frequency_meep_units": FREQ,
    "core_index": INDEX,
    "waveguide_width_meep_units": WIDTH,
    "resolution": RESOLUTION,
    "radii_meep_units": list(RADII),
    "durations_meep_units": list(DURATIONS),
    "results": results,
    "absolute_convergence_changes": changes,
    "temporal_convergence_tolerance": tol,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "limitations": [
        "2D illustrative effective-index model; no LNOI material stack or PDK bend",
        "Aperture flux includes radiated power and is not guided-mode-specific",
        "No spatial-resolution convergence or fabricated bend-loss prediction",
        "Two bend radii alone do not establish an optimal radius",
    ],
}
(OUTPUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
if any(value > tol for item in changes.values() for value in item.values()):
    raise SystemExit("Temporal convergence test failed")
if any(not (-0.05 <= item[metric] <= 1.2)
       for item in results[str(DURATIONS[-1])].values()
       for metric in ("aperture_relative_reflection_ratio",
                      "aperture_relative_transmission_ratio")):
    raise SystemExit("Bend aperture ratios outside broad sanity bounds")
