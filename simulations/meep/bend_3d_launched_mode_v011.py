"""OPA-FDTD-011: guided-mode transmission of 3D dielectric waveguide bends.

OPA-FDTD-007..010 excite the waveguide with a finite-size Ez current, so the
incident field is an unknown mix of modes and radiation (OPA-FDTD-010 decomposes
it into the odd-Z sector but must treat band 1 as a diagnostic candidate only).
This experiment instead launches the fundamental TE-like eigenmode with an
EigenModeSource and decomposes the input and output port fields into that same
mode. A straight reference validates the normalization, so the reported
transmission is guided-mode-to-guided-mode.

Results are illustrative: the material (index 1.8 core in air) and the
geometry are generic Meep-unit values, not a calibrated foundry platform.
"""
import math
import time

import meep as mp

from opa_common import (bend_centerline, modal_powers, peak_rss_bytes,
                        ribbon_polygon, write_report)

OUT = "results/opa-fdtd-011"
CELL = mp.Vector3(10, 10, 4)
PML = 1.0
RESOLUTIONS = (12, 16)
RADII = (1.0, 2.0)
THICKNESS = 0.4
WIDTH = 0.8
INDEX = 1.8
FREQ = 0.8
FWIDTH = 0.25
# TE-like modes are even under the z mirror. Using the symmetry halves the
# computational cell; the parity must match the source and decomposition.
PARITY = mp.EVEN_Z
SYMMETRIES = [mp.Mirror(mp.Z, phase=+1)]
PORT_SIZE = 2.4
PORT_HEIGHT = CELL.z - 2 * PML
SOURCE_Y = -3.5
PORT_OFFSET = 3.0
DFT_TOLERANCE = 1e-6
MIN_TIME = 50
MAX_TIME = 400
STRAIGHT_TOLERANCE = 0.03
ENERGY_TOLERANCE = 0.03
RESOLUTION_TARGET = 0.02


def port(center, direction):
    if direction == mp.Y:
        size = mp.Vector3(PORT_SIZE, 0, PORT_HEIGHT)
    else:
        size = mp.Vector3(0, PORT_SIZE, PORT_HEIGHT)
    return mp.FluxRegion(center=center, size=size, direction=direction)


def build(radius, resolution):
    medium = mp.Medium(index=INDEX)
    if radius is None:
        geometry = [mp.Block(size=mp.Vector3(WIDTH, mp.inf, THICKNESS),
                             material=medium)]
    else:
        lead_end = CELL.x / 2 + 0.2
        vertices = ribbon_polygon(bend_centerline(radius, lead_end), WIDTH,
                                  z=-THICKNESS / 2)
        geometry = [mp.Prism(vertices=vertices, height=THICKNESS,
                             axis=mp.Vector3(0, 0, 1), material=medium)]
    return mp.Simulation(
        cell_size=CELL,
        dimensions=3,
        resolution=resolution,
        boundary_layers=[mp.PML(PML)],
        geometry=geometry,
        symmetries=SYMMETRIES,
        sources=[mp.EigenModeSource(
            src=mp.GaussianSource(FREQ, fwidth=FWIDTH),
            center=mp.Vector3(0, SOURCE_Y, 0),
            size=mp.Vector3(PORT_SIZE, 0, PORT_HEIGHT),
            direction=mp.Y,
            eig_band=1,
            eig_parity=PARITY,
            eig_match_freq=True,
        )],
    )


def run_case(radius, resolution):
    start = time.perf_counter()
    sim = build(radius, resolution)
    input_monitor = sim.add_mode_monitor(
        FREQ, 0, 1, port(mp.Vector3(0, -PORT_OFFSET, 0), mp.Y))
    if radius is None:
        output_region = port(mp.Vector3(0, PORT_OFFSET, 0), mp.Y)
    else:
        output_region = port(mp.Vector3(PORT_OFFSET, 0, 0), mp.X)
    output_monitor = sim.add_mode_monitor(FREQ, 0, 1, output_region)
    sim.run(until_after_sources=mp.stop_when_dft_decayed(
        DFT_TOLERANCE, MIN_TIME, MAX_TIME))
    in_fwd, in_bwd, in_neff = modal_powers(sim, input_monitor, PARITY)
    out_fwd, out_bwd, out_neff = modal_powers(sim, output_monitor, PARITY)
    out_aperture = float(mp.get_fluxes(output_monitor)[0])
    meep_time = float(sim.meep_time())
    sim.reset_meep()
    values = (in_fwd, in_bwd, out_fwd, out_bwd, out_aperture)
    if not all(map(math.isfinite, values)):
        raise ValueError(f"Non-finite result, radius={radius}, res={resolution}")
    return {
        "radius_meep_units": radius,
        "resolution": resolution,
        "input_forward_modal_power": in_fwd,
        "input_backward_modal_power": in_bwd,
        "output_forward_modal_power": out_fwd,
        "output_backward_modal_power": out_bwd,
        "output_aperture_flux": out_aperture,
        "input_n_eff": in_neff,
        "output_n_eff": out_neff,
        "simulated_meep_time": meep_time,
        "wall_seconds": time.perf_counter() - start,
        "process_peak_rss_bytes": peak_rss_bytes(),
    }


def ratios(case, reference_power):
    transmission = case["output_forward_modal_power"] / reference_power
    reflection = case["input_backward_modal_power"] / reference_power
    return {
        "guided_transmission": transmission,
        "guided_reflection": reflection,
        "radiated_or_other_modes": 1.0 - transmission - reflection,
        "guided_transmission_dB": 10 * math.log10(transmission)
        if transmission > 0 else None,
        "output_aperture_flux_ratio": case["output_aperture_flux"] / reference_power,
    }


measurements, summary, failures = {}, {}, []
for resolution in RESOLUTIONS:
    key = str(resolution)
    straight = run_case(None, resolution)
    reference = straight["input_forward_modal_power"]
    if reference <= 0:
        raise ValueError("Non-positive straight reference at resolution " + key)
    straight_ratios = ratios(straight, reference)
    if abs(straight_ratios["guided_transmission"] - 1) > STRAIGHT_TOLERANCE:
        failures.append(f"straight waveguide transmission off by more than "
                        f"{STRAIGHT_TOLERANCE} at resolution {key}")
    bends = {str(r): run_case(r, resolution) for r in RADII}
    measurements[key] = {"straight": straight, "bends": bends}
    summary[key] = {"straight": straight_ratios,
                    **{str(r): ratios(bends[str(r)], reference) for r in RADII}}
    for r in RADII:
        row = summary[key][str(r)]
        if row["guided_transmission"] + row["guided_reflection"] > 1 + ENERGY_TOLERANCE:
            failures.append(f"T+R exceeds 1 for radius {r} at resolution {key}")

low, high = (str(r) for r in RESOLUTIONS)
resolution_changes = {
    str(r): abs(summary[high][str(r)]["guided_transmission"] -
                summary[low][str(r)]["guided_transmission"])
    for r in RADII
}
report = {
    "experiment": "OPA-FDTD-011",
    "goal": "Guided-mode (TE-like band 1) transmission of 3D 90-degree bends",
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "parameters": {
        "cell_meep_units": [CELL.x, CELL.y, CELL.z],
        "pml": PML,
        "resolutions": list(RESOLUTIONS),
        "radii": list(RADII),
        "core_index": INDEX,
        "cladding_index": 1.0,
        "width": WIDTH,
        "thickness": THICKNESS,
        "frequency": FREQ,
        "vacuum_wavelength": 1 / FREQ,
        "parity": "EVEN_Z (TE-like)",
        "z_mirror_symmetry": True,
        "dft_decay_tolerance": DFT_TOLERANCE,
    },
    "summary": summary,
    "resolution_transmission_changes": resolution_changes,
    "resolution_target_absolute_change": RESOLUTION_TARGET,
    "resolution_within_target": all(v <= RESOLUTION_TARGET
                                     for v in resolution_changes.values()),
    "failures": failures,
    "measurements": measurements,
    "limitations": [
        "Generic index-1.8 core in air in Meep units; not a calibrated foundry platform",
        "Single frequency; no spectral response",
        "Two resolutions do not prove spatial convergence",
        "Only the fundamental TE-like mode is decomposed; TM-like and higher-order "
        "mode content is lumped into radiated_or_other_modes",
        "No PML-thickness or port-size sensitivity study",
    ],
}
write_report(OUT, report)
if not report["resolution_within_target"]:
    print("WARNING: resolution target not met; finer grids are needed")
if failures:
    raise SystemExit("OPA-FDTD-011 validation failed: " + "; ".join(failures))
