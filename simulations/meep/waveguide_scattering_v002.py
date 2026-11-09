"""OPA-FDTD-002: normalized 2D straight-waveguide/air-gap scattering experiment.

This is a pedagogical effective-index model, not an lnoi400/LNOI PDK simulation.
Unit lengths are Meep distance units; material properties are illustrative.
"""
import json
import math
from pathlib import Path

import meep as mp

OUT = Path("results/opa-fdtd-002")
OUT.mkdir(parents=True, exist_ok=True)

FREQUENCY = 0.8
BANDWIDTH = 0.2
WAVEGUIDE_WIDTH = 0.8
CORE_INDEX = 1.8
AIR_GAP_LENGTH = 0.45
RESOLUTION = 20
CELL = mp.Vector3(12, 5, 0)
PML = [mp.PML(1.0)]
REFLECT_PLANE = mp.FluxRegion(center=mp.Vector3(-2.5, 0), size=mp.Vector3(0, 2))
TRANSMIT_PLANE = mp.FluxRegion(center=mp.Vector3(2.5, 0), size=mp.Vector3(0, 2))


def create_simulation(with_gap: bool):
    geometry = [
        mp.Block(
            size=mp.Vector3(mp.inf, WAVEGUIDE_WIDTH, mp.inf),
            material=mp.Medium(index=CORE_INDEX),
        )
    ]
    if with_gap:
        geometry.append(
            mp.Block(
                size=mp.Vector3(AIR_GAP_LENGTH, WAVEGUIDE_WIDTH, mp.inf),
                material=mp.air,
            )
        )
    return mp.Simulation(
        cell_size=CELL,
        geometry=geometry,
        resolution=RESOLUTION,
        dimensions=2,
        boundary_layers=PML,
        sources=[
            mp.Source(
                src=mp.GaussianSource(FREQUENCY, fwidth=BANDWIDTH),
                component=mp.Ez,
                center=mp.Vector3(-3.5, 0),
                size=mp.Vector3(0, WAVEGUIDE_WIDTH),
            )
        ],
    )


def measure(duration):
    """Run matched reference and scattering simulations to a fixed duration."""
    reference = create_simulation(with_gap=False)
    refl = reference.add_flux(FREQUENCY, 0, 1, REFLECT_PLANE)
    tran = reference.add_flux(FREQUENCY, 0, 1, TRANSMIT_PLANE)
    reference.run(until=duration)
    incident_power = float(mp.get_fluxes(refl)[0])
    reference_transmitted_flux = float(mp.get_fluxes(tran)[0])
    incident_field_data = reference.get_flux_data(refl)
    reference.reset_meep()

    scattering = create_simulation(with_gap=True)
    gap_refl = scattering.add_flux(FREQUENCY, 0, 1, REFLECT_PLANE)
    gap_tran = scattering.add_flux(FREQUENCY, 0, 1, TRANSMIT_PLANE)
    scattering.load_minus_flux_data(gap_refl, incident_field_data)
    scattering.run(until=duration)
    scattered_reflection_flux = float(mp.get_fluxes(gap_refl)[0])
    gap_transmitted_flux = float(mp.get_fluxes(gap_tran)[0])
    scattering.reset_meep()

    raw = [incident_power, reference_transmitted_flux,
           scattered_reflection_flux, gap_transmitted_flux]
    if not all(math.isfinite(v) for v in raw) or incident_power <= 0:
        raise ValueError(f"Invalid reference/scattered flux at t={duration}: {raw}")
    # Both ratios use the same incident-power monitor and reference run.
    return {
        "duration_meep_units": duration,
        "incident_power_reflection_plane": incident_power,
        "reference_transmission_plane_flux": reference_transmitted_flux,
        "gap_reflection_scattered_flux": scattered_reflection_flux,
        "gap_transmission_plane_flux": gap_transmitted_flux,
        "aperture_relative_reflection_ratio": -scattered_reflection_flux / incident_power,
        "aperture_relative_transmission_ratio": gap_transmitted_flux / incident_power,
    }


short = measure(140)
long = measure(200)
R_KEY = "aperture_relative_reflection_ratio"
T_KEY = "aperture_relative_transmission_ratio"
delta_R = abs(short[R_KEY] - long[R_KEY])
delta_T = abs(short[T_KEY] - long[T_KEY])
CONVERGENCE_ABS_TOL = 0.02
result = {
    "experiment": "OPA-FDTD-002",
    "model": "2D illustrative index-guided slab with central air gap",
    "is_lnoi400_model": False,
    "frequency_meep_units": FREQUENCY,
    "bandwidth_meep_units": BANDWIDTH,
    "core_index": CORE_INDEX,
    "waveguide_width_meep_units": WAVEGUIDE_WIDTH,
    "air_gap_length_meep_units": AIR_GAP_LENGTH,
    "resolution": RESOLUTION,
    "short_run": short,
    "long_run": long,
    "absolute_change_reflection_ratio": delta_R,
    "absolute_change_transmission_ratio": delta_T,
    "convergence_absolute_tolerance": CONVERGENCE_ABS_TOL,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "limitations": [
        "2D illustrative slab, not calibrated to Luxtelligence lnoi400",
        "Ratios are aperture-relative flux measurements; not guided-mode S-parameters",
        "Radiation may leave the flux apertures; R+T is not a validated energy budget",
        "Convergence tested by extending both simulations; spatial resolution not converged",
        "No claim of fabrication readiness, propagation-loss dB/cm or energy efficiency",
    ],
}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
if max(delta_R, delta_T) > CONVERGENCE_ABS_TOL:
    raise SystemExit("Aperture flux ratios did not converge at extended duration")
if not all(-0.05 <= long[k] <= 1.2 for k in (R_KEY, T_KEY)):
    raise SystemExit("Aperture-relative flux ratios outside broad sanity bounds")
