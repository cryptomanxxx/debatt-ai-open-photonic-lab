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


def run_to_decay(sim):
    sim.run(
        until_after_sources=mp.stop_when_fields_decayed(
            40, mp.Ez, mp.Vector3(2.5, 0), 1e-5
        )
    )


reference = create_simulation(with_gap=False)
reflected_monitor = reference.add_flux(FREQUENCY, 0, 1, REFLECT_PLANE)
transmitted_monitor = reference.add_flux(FREQUENCY, 0, 1, TRANSMIT_PLANE)
run_to_decay(reference)
incident_reflection_plane = float(mp.get_fluxes(reflected_monitor)[0])
incident_transmission_plane = float(mp.get_fluxes(transmitted_monitor)[0])
incident_field_data = reference.get_flux_data(reflected_monitor)
reference.reset_meep()

scattering = create_simulation(with_gap=True)
gap_reflection_monitor = scattering.add_flux(FREQUENCY, 0, 1, REFLECT_PLANE)
gap_transmission_monitor = scattering.add_flux(FREQUENCY, 0, 1, TRANSMIT_PLANE)
scattering.load_minus_flux_data(gap_reflection_monitor, incident_field_data)
run_to_decay(scattering)
reflected_scattered_flux = float(mp.get_fluxes(gap_reflection_monitor)[0])
transmitted_gap_flux = float(mp.get_fluxes(gap_transmission_monitor)[0])

values = [
    incident_reflection_plane,
    incident_transmission_plane,
    reflected_scattered_flux,
    transmitted_gap_flux,
]
if not all(math.isfinite(v) for v in values):
    raise SystemExit("Non-finite flux detected")
if incident_reflection_plane <= 0 or incident_transmission_plane <= 0:
    raise SystemExit("Reference guided-flux normalization failed")

reflectance = -reflected_scattered_flux / incident_reflection_plane
transmittance = transmitted_gap_flux / incident_transmission_plane
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
    "reference_flux_reflection_plane": incident_reflection_plane,
    "reference_flux_transmission_plane": incident_transmission_plane,
    "scattered_reflection_flux": reflected_scattered_flux,
    "gap_transmission_flux": transmitted_gap_flux,
    "normalized_reflectance": reflectance,
    "normalized_transmittance": transmittance,
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "limitations": [
        "2D effective-index demonstration, not calibrated to Luxtelligence lnoi400",
        "No mode-selective port decomposition; flux planes include radiation",
        "No claim of fabrication readiness, propagation-loss dB/cm or energy efficiency",
    ],
}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
if not (-0.05 <= reflectance <= 1.2 and -0.05 <= transmittance <= 1.2):
    raise SystemExit("Normalized flux outside broad numerical sanity bounds")
