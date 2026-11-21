"""OPA-LOGIC-001: passive add-drop ring, two-resolution 2D effective-index FDTD."""
import csv
import json
from pathlib import Path

import meep as mp
import numpy as np


OUT = Path("results/opa-logic-001")
RADIUS_UM = 1.8
WIDTH_UM = 0.40
GAP_UM = 0.15
INDEX = 2.8
CELL = mp.Vector3(14, 10)
PML_UM = 1
Y = RADIUS_UM + WIDTH_UM + GAP_UM
FMIN, FMAX = 1 / 1.60, 1 / 1.50
FCEN = (FMIN + FMAX) / 2
BAND = FMAX - FMIN
POINTS = 301


def simulate(resolution, add_ring):
    mp.verbosity(0)
    core = mp.Medium(index=INDEX)
    geometry = [mp.Block(size=mp.Vector3(mp.inf, WIDTH_UM, mp.inf),
                         center=mp.Vector3(0, -Y), material=core)]
    if add_ring:
        geometry += [
            mp.Block(size=mp.Vector3(mp.inf, WIDTH_UM, mp.inf),
                     center=mp.Vector3(0, Y), material=core),
            mp.Cylinder(radius=RADIUS_UM + WIDTH_UM / 2, material=core),
            mp.Cylinder(radius=RADIUS_UM - WIDTH_UM / 2, material=mp.air),
        ]
    source = mp.EigenModeSource(
        src=mp.GaussianSource(FCEN, fwidth=2 * BAND), center=mp.Vector3(-4.75, -Y),
        size=mp.Vector3(0, 2), direction=mp.X, eig_band=1,
        eig_parity=mp.ODD_Z, eig_match_freq=True,
    )
    sim = mp.Simulation(
        cell_size=CELL, boundary_layers=[mp.PML(PML_UM)], resolution=resolution,
        sources=[source], geometry=geometry, dimensions=2,
    )
    through = sim.add_mode_monitor(FCEN, BAND, POINTS,
                                   mp.ModeRegion(center=mp.Vector3(4.75, -Y), size=mp.Vector3(0, 2)))
    drop = None
    if add_ring:
        drop = sim.add_mode_monitor(FCEN, BAND, POINTS,
                                    mp.ModeRegion(center=mp.Vector3(-4.75, Y), size=mp.Vector3(0, 2)))
    # Fixed post-pulse duration resolves the loaded linewidth in this deliberately
    # low-Q, small 2D ring. Cross-resolution comparison screens the peak location.
    sim.run(until_after_sources=650)
    frequencies = np.array(mp.get_flux_freqs(through))
    def guided_power(monitor, direction_index):
        coefficients = sim.get_eigenmode_coefficients(
            monitor, [1], eig_parity=mp.ODD_Z, direction=mp.X,
        )
        return np.abs(coefficients.alpha[0, :, direction_index]) ** 2
    transmitted = guided_power(through, 0)
    dropped = guided_power(drop, 1) if drop is not None else None
    sim.reset_meep()
    return frequencies, transmitted, dropped


def characterize(resolution):
    freqs, launch, _ = simulate(resolution, add_ring=False)
    _, through, drop = simulate(resolution, add_ring=True)
    if np.min(launch) <= 0 or np.min(launch) < 0.02 * np.max(launch):
        raise ValueError("Insufficient straight-guide reference power for this scan")
    through /= launch
    drop /= launch
    missing = 1 - through - drop
    wavelength_nm = 1000 / freqs
    data = zip(wavelength_nm[::-1], through[::-1], drop[::-1], missing[::-1])
    with (OUT / f"spectrum-{resolution}px-per-um.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["wavelength_nm", "through_flux_ratio", "drop_flux_ratio", "uncollected_fraction"])
        writer.writerows(data)
    peak = int(np.argmax(drop))
    if not 0 < peak < POINTS - 1:
        raise ValueError("Strongest drop peak occurs at scan boundary")
    half_peak = drop[peak] / 2
    lower = next((i for i in range(peak - 1, -1, -1) if drop[i] < half_peak), None)
    upper = next((i for i in range(peak + 1, POINTS) if drop[i] < half_peak), None)
    if lower is None or upper is None:
        raise ValueError("Scan does not bracket the drop peak")
    def half_wavelength(index, neighbor):
        return np.interp(half_peak, [drop[index], drop[neighbor]],
                         [wavelength_nm[index], wavelength_nm[neighbor]])
    linewidth = float(half_wavelength(lower, lower + 1) - half_wavelength(upper, upper - 1))
    return {
        "resolution_px_per_um": resolution, "peak_nm": float(wavelength_nm[peak]),
        "drop_ratio": float(drop[peak]), "through_ratio": float(through[peak]),
        "linewidth_nm": linewidth, "loaded_q_estimate": float(wavelength_nm[peak] / linewidth),
        "uncollected_at_peak": float(missing[peak]), "min_uncollected": float(min(missing)),
        "off_resonance_through_ratio": float(max(through)),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = [characterize(resolution) for resolution in (24, 32)]
    coarse, fine = results
    shift = abs(coarse["peak_nm"] - fine["peak_nm"])
    screens = {
        "drop_peak_above_10_percent": all(r["drop_ratio"] > 0.10 for r in results),
        "through_falls_by_10_percentage_points_at_peak": all(
            r["off_resonance_through_ratio"] - r["through_ratio"] > 0.10 for r in results),
        "flux_normalization_excess_below_5_percent": all(r["min_uncollected"] >= -0.05 for r in results),
        "peak_shift_below_10_nm": shift <= 10,
    }
    report = {
        "experiment": "OPA-LOGIC-001", "evidence": "2D effective-index electromagnetic simulation",
        "physical_measurement": False, "meep_version": mp.__version__,
        "geometry": {"radius_um": RADIUS_UM, "waveguide_width_um": WIDTH_UM,
                     "gap_um": GAP_UM, "effective_index": INDEX, "cladding_index": 1.0},
        "results": results, "resolution_peak_shift_nm": shift, "screens": screens,
        "scope": "Lossless materials. Uncollected power includes other ports, reflection, radiation and numerical error. These data do not calibrate the browser ring or a fabricated device.",
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not all(screens.values()):
        raise SystemExit("One or more predeclared FDTD screens failed")


if __name__ == "__main__":
    main()
