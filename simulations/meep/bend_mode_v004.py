"""OPA-FDTD-004: guided-mode power audit for illustrative 90-degree bends.

Meep eigenmode decomposition: squared modal amplitudes represent modal power.
Results are *not* validated physical bend losses or an LNOI PDK model.
"""
import json
import math
from pathlib import Path

import meep as mp

OUTPUT = Path("results/opa-fdtd-004")
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
    """Polygonal constant-width centerline; both leads extend through the PML."""
    centerline = [(0.0, -4.6), (0.0, -radius)]
    for step in range(1, 33):
        theta = math.pi - (math.pi / 2) * step / 32
        centerline.append((radius + radius * math.cos(theta),
                           -radius + radius * math.sin(theta)))
    centerline.append((4.6, 0.0))
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
        sources=[mp.EigenModeSource(
            src=mp.GaussianSource(FREQ, fwidth=BANDWIDTH),
            center=SOURCE,
            size=mp.Vector3(2.0, 0),
            direction=mp.Y,
            eig_band=1,
            eig_parity=mp.ODD_Z,
            eig_match_freq=True,
        )],
    )


def modal_powers(sim, monitor):
    """Forward and backward power in band 1 at a transverse monitor."""
    coeff = sim.get_eigenmode_coefficients(
        monitor, [1], eig_parity=mp.ODD_Z
    ).alpha[0, 0]
    return float(abs(coeff[0]) ** 2), float(abs(coeff[1]) ** 2)


def run_reference(duration):
    sim = simulation()
    input_monitor = sim.add_flux(FREQ, 0, 1, IN_REGION)
    sim.run(until=duration)
    forward, backward = modal_powers(sim, input_monitor)
    aperture = float(mp.get_fluxes(input_monitor)[0])
    reference_fields = sim.get_flux_data(input_monitor)
    sim.reset_meep()
    if not math.isfinite(forward) or forward <= 0:
        raise ValueError("Invalid forward input modal reference")
    return {"guided_forward": forward, "guided_backward": backward,
            "aperture_flux": aperture}, reference_fields


def run_bend(radius, duration, reference, reference_fields):
    sim = simulation(radius)
    input_monitor = sim.add_flux(FREQ, 0, 1, IN_REGION)
    reflection_monitor = sim.add_flux(FREQ, 0, 1, IN_REGION)
    output_monitor = sim.add_flux(FREQ, 0, 1, OUT_REGION)
    sim.load_minus_flux_data(reflection_monitor, reference_fields)
    sim.run(until=duration)
    incident_mode, raw_backward_mode = modal_powers(sim, input_monitor)
    _, reflected_mode = modal_powers(sim, reflection_monitor)
    transmitted_mode, output_backward_mode = modal_powers(sim, output_monitor)
    output_aperture = float(mp.get_fluxes(output_monitor)[0])
    sim.reset_meep()
    den = reference["guided_forward"]
    metrics = {
        "input_forward_guided_ratio": incident_mode / den,
        "input_backward_guided_ratio": reflected_mode / den,
        "input_backward_total_fields_ratio": raw_backward_mode / den,
        "output_forward_guided_ratio": transmitted_mode / den,
        "output_backward_guided_ratio": output_backward_mode / den,
        "output_aperture_flux_ratio": output_aperture / den,
    }
    if not all(math.isfinite(v) for v in metrics.values()):
        raise ValueError("Non-finite guided-mode measurement")
    return {
        "radius_meep_units": radius,
        "duration_meep_units": duration,
        "modal_reference_power": den,
        "modal_ratios": metrics,
        "reference_based_guided_remainder": 1.0 -
            metrics["input_backward_guided_ratio"] -
            metrics["output_forward_guided_ratio"],
        "net_directional_guided_balance":
            metrics["input_forward_guided_ratio"] -
            metrics["input_backward_guided_ratio"] -
            metrics["output_forward_guided_ratio"] +
            metrics["output_backward_guided_ratio"],
    }


references = {}
results = {}
for duration in DURATIONS:
    reference, reference_fields = run_reference(duration)
    references[str(duration)] = reference
    results[str(duration)] = {
        str(radius): run_bend(radius, duration, reference, reference_fields)
        for radius in RADII
    }

metrics_to_compare = (
    "input_backward_guided_ratio",
    "output_forward_guided_ratio",
    "output_aperture_flux_ratio",
)
changes = {}
for radius in RADII:
    key = str(radius)
    changes[key] = {
        metric: abs(
            results[str(DURATIONS[1])][key]["modal_ratios"][metric] -
            results[str(DURATIONS[0])][key]["modal_ratios"][metric]
        )
        for metric in metrics_to_compare
    }

report = {
    "experiment": "OPA-FDTD-004",
    "model": "illustrative 2D index-guided slab bend, not LNOI",
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "resolution": RESOLUTION,
    "radii_meep_units": list(RADII),
    "durations_meep_units": list(DURATIONS),
    "input_references": references,
    "results": results,
    "temporal_convergence_absolute_change": changes,
    "limitations": [
        "Power ratios refer to one guided mode, not total optical transmission",
        "Reference-based guided remainder and net directional guided balance are algebraic diagnostics, not independently measured radiation",
        "Input reflection uses complex reference-field subtraction before modal decomposition; total-field backward power retained as a diagnostic",
        "Only temporal convergence tested; spatial resolution and PML sensitivity untested",
        "Illustrative 2D scalar-like model, not validated LNOI bend-loss prediction",
    ],
}
(OUTPUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
if any(value > 0.02 for row in changes.values() for value in row.values()):
    raise SystemExit("Modal-ratio temporal convergence failed")
for result in results[str(DURATIONS[-1])].values():
    values = result["modal_ratios"]
    for metric in metrics_to_compare:
        if not (0 <= values[metric] <= 1.2):
            raise SystemExit(f"Modal-ratio sanity check failed: {metric}")
