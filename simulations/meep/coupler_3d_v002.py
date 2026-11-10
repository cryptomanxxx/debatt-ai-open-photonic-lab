"""OPA-COUPLER-002: 3D FDTD of the complete directional coupler, including its S-bends.

OPA-COUPLER-001 used two-mode (supermode) theory for the straight section only.
This experiment simulates the full coupler of OPA-LAYOUT-001 in 3D: the
waveguide polygons are exported from gdsfactory
(simulations/meep/geometry/coupler_gap0.236.json), extruded to 220 nm silicon
in silicon dioxide, and excited with the TE-like mode of the top waveguide at
1.55 um. Mode decomposition at the two outputs gives the cross fraction
kappa^2 = P_cross / (P_cross + P_through).

Two-mode theory with an extra bend phase phi_b predicts

    kappa^2(L) = sin^2(phi_b + pi * L / (2 * L_c)),

where L is the straight length. Fitting three lengths (0, 8, 16 um) gives L_c
and phi_b, and tests whether the model holds (two parameters, three points).

Usage:
    python coupler_3d_v002.py case LENGTH RESOLUTION   # one simulation
    python coupler_3d_v002.py aggregate                # fit, checks, report

CI runs the four cases in parallel (one per CPU core), then aggregates.
"""
import json
import math
from pathlib import Path
import resource
import sys
import time

OUT = Path("results/opa-coupler-002")
GEOMETRY = Path("simulations/meep/geometry/coupler_gap0.236.json")
COUPLER_001 = Path("results/opa-coupler-001/result.json")
WL = 1.55
HEIGHT = 0.22
WIDTH = 0.50
PML = 1.0
LEAD = 2.0              # straight waveguide beyond each coupler port, um
MARGIN_Y = 1.0
MARGIN_Z = 0.8
CASES = [(0.0, 16), (8.0, 16), (16.0, 16), (0.0, 24)]
MPB_SAME_RESOLUTION = {16: 56.361, 24: 54.052}   # L_c from MPB at the FDTD grid (gap 0.236)


def n_si(wl):
    l2, l1 = wl * wl, 1.1071
    return math.sqrt(11.6858 + 0.939816 / l2 + 0.00810461 * l1 ** 2 / (l2 - l1 ** 2))


def n_sio2(wl):
    l2 = wl * wl
    return math.sqrt(1 + 0.6961663 * l2 / (l2 - 0.0684043 ** 2)
                     + 0.4079426 * l2 / (l2 - 0.1162414 ** 2)
                     + 0.8974794 * l2 / (l2 - 9.896161 ** 2))


def case_path(length, res):
    return OUT / f"case_L{length:g}_res{res}.json"


def run_case(length, res):
    import meep as mp

    geo_data = json.loads(GEOMETRY.read_text())["lengths"][f"{length:g}"]
    ports = geo_data["ports"]
    x0, x1 = ports["o1"][0], ports["o3"][0]
    y_bot, y_top = ports["o1"][1], ports["o2"][1]
    xc, yc = (x0 + x1) / 2, (y_bot + y_top) / 2
    si, ox = mp.Medium(index=n_si(WL)), mp.Medium(index=n_sio2(WL))
    cell = mp.Vector3((x1 - x0) + 2 * (LEAD + PML),
                      (y_top - y_bot) + WIDTH + 2 * (MARGIN_Y + PML),
                      HEIGHT + 2 * (MARGIN_Z + PML))
    geometry = [mp.Prism([mp.Vector3(x - xc, y - yc, -HEIGHT / 2) for x, y in poly],
                         height=HEIGHT, material=si) for poly in geo_data["polygons"]]
    for y in (y_bot, y_top):              # input and output leads through the PML
        for xa, sign in ((x0, -1), (x1, 1)):
            geometry.append(mp.Block(
                center=mp.Vector3(xa - xc + sign * (LEAD + PML) / 2, y - yc, 0),
                size=mp.Vector3(LEAD + PML + 0.02, WIDTH, HEIGHT), material=si))
    f = 1 / WL
    port_size = mp.Vector3(0, 2.0, HEIGHT + 2 * MARGIN_Z)
    sim = mp.Simulation(
        cell_size=cell, resolution=res, geometry=geometry, default_material=ox,
        boundary_layers=[mp.PML(PML)], symmetries=[mp.Mirror(mp.Z, phase=+1)],
        sources=[mp.EigenModeSource(
            mp.GaussianSource(f, fwidth=0.25 * f),
            center=mp.Vector3(x0 - xc - 1.2, y_top - yc, 0), size=port_size,
            direction=mp.X, eig_band=1, eig_parity=mp.EVEN_Z, eig_match_freq=True)],
    )
    region = lambda x, y: mp.FluxRegion(center=mp.Vector3(x, y - yc, 0), size=port_size)
    m_in = sim.add_mode_monitor(f, 0, 1, region(x0 - xc - 0.8, y_top))
    m_thru = sim.add_mode_monitor(f, 0, 1, region(x1 - xc + 0.8, y_top))
    m_cross = sim.add_mode_monitor(f, 0, 1, region(x1 - xc + 0.8, y_bot))
    start = time.time()
    sim.run(until_after_sources=mp.stop_when_dft_decayed(1e-5, 20, 500))

    def forward(monitor):
        return float(abs(sim.get_eigenmode_coefficients(
            monitor, [1], eig_parity=mp.EVEN_Z).alpha[0, 0, 0]) ** 2)

    p_in, p_thru, p_cross = forward(m_in), forward(m_thru), forward(m_cross)
    result = {
        "length_um": length, "resolution": res,
        "cell_um": [cell.x, cell.y, cell.z],
        "input_power": p_in, "through": p_thru / p_in, "cross": p_cross / p_in,
        "kappa2": p_cross / (p_thru + p_cross),
        "excess_loss": 1 - (p_thru + p_cross) / p_in,
        "meep_time": float(sim.meep_time()), "wall_seconds": time.time() - start,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "meep_version": str(getattr(mp, "__version__", "unknown")),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    case_path(length, res).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def aggregate():
    import numpy as np
    from scipy.optimize import least_squares

    cases = {(L, r): json.loads(case_path(L, r).read_text()) for L, r in CASES}
    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    lengths = np.array([L for L, r in CASES if r == 16])
    k2 = np.array([cases[(L, 16)]["kappa2"] for L in lengths])

    def residual(p):
        lc, phi = p
        return np.sin(phi + np.pi * lengths / (2 * lc)) ** 2 - k2

    fit = least_squares(residual, [MPB_SAME_RESOLUTION[16], 0.1])
    lc_fdtd, phi_b16 = map(float, fit.x)
    max_residual = float(np.abs(fit.fun).max())
    check("two_mode_model_fits", max_residual < 0.01,
          f"sin^2(phi_b + pi L / 2 L_c) fits the three lengths with max residual "
          f"{max_residual:.4f} (limit 0.01)")
    rel = abs(lc_fdtd - MPB_SAME_RESOLUTION[16]) / MPB_SAME_RESOLUTION[16]
    check("fdtd_matches_mpb_same_grid", rel < 0.05,
          f"FDTD L_c = {lc_fdtd:.2f} um vs MPB {MPB_SAME_RESOLUTION[16]:.2f} um at "
          f"16 px/um ({rel:.1%}, limit 5 %)")
    losses = [c["excess_loss"] for c in cases.values()]
    check("low_excess_loss", max(losses) < 0.05,
          f"excess loss at most {max(losses):.2%} (limit 5 %)")

    # Bend phase from L = 0 alone, at two resolutions
    phi_b = {r: float(math.asin(math.sqrt(cases[(0.0, r)]["kappa2"]))) for r in (16, 24)}
    phi_change = abs(phi_b[24] - phi_b[16]) / phi_b[24]
    check("bend_phase_resolution_stable", phi_change < 0.2,
          f"bend phase {phi_b[16]:.4f} rad at 16 px/um vs {phi_b[24]:.4f} rad at 24 px/um "
          f"({phi_change:.1%}, limit 20 %)")

    # Layout recommendation: converged L_c from OPA-COUPLER-001, bend phase from FDTD
    c001 = json.loads(COUPLER_001.read_text())
    lc_conv = next(r for r in c001["D_gap_sweep"] if abs(r["gap_um"] - 0.236) < 1e-9)[
        "coupling_length_um"]
    phi = phi_b[24]
    recommended = (math.pi / 4 - phi) * 2 * lc_conv / math.pi
    layout_now = math.sin(phi + math.pi * 20.0 / (2 * lc_conv)) ** 2
    check("recommendation_shorter_than_straight_only",
          recommended < lc_conv / 2,
          f"the bends add coupling, so the recommended straight length {recommended:.2f} um "
          f"is shorter than the straight-only 50:50 length {lc_conv / 2:.2f} um")

    report = {
        "experiment": "OPA-COUPLER-002",
        "goal": "3D FDTD of the full OPA-LAYOUT-001 directional coupler (gap 0.236 um, "
                "S-bends included) to test two-mode theory and measure the bend coupling",
        "geometry": str(GEOMETRY),
        "waveguide": {"width_um": WIDTH, "height_um": HEIGHT, "core": "Si", "cladding": "SiO2",
                      "wavelength_um": WL, "polarization": "TE-like (EVEN_Z)"},
        "cases": [cases[k] for k in CASES],
        "fit_16px": {"coupling_length_um": lc_fdtd, "bend_phase_rad": phi_b16,
                     "max_residual": max_residual},
        "mpb_same_resolution_coupling_length_um": MPB_SAME_RESOLUTION,
        "bend_phase_from_L0_rad": {str(k): v for k, v in phi_b.items()},
        "bend_equivalent_straight_length_um": 2 * lc_conv * phi / math.pi,
        "layout": {
            "converged_coupling_length_um": lc_conv,
            "recommended_straight_length_um": recommended,
            "current_straight_length_um": 20.0,
            "current_cross_fraction_with_bends": layout_now,
            "method": "straight length = (pi/4 - phi_b) * 2 L_c / pi, with L_c converged "
                      "from MPB (OPA-COUPLER-001, 100 px/um) and phi_b from FDTD at 24 px/um",
        },
        "checks": checks,
        "failures": failures,
        "limitations": [
            "FDTD at 16 and 24 px/um only (3D cost); absolute L_c is therefore taken from "
            "the converged MPB result, and FDTD is compared with MPB on the same grid",
            "Single wavelength (1.55 um) and TE-like polarization",
            "Generic-PDK S-bend shape; a foundry PDK coupler will have different bends",
            "No sidewall angle, roughness or fabrication variation",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit("OPA-COUPLER-002 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    if sys.argv[1] == "case":
        run_case(float(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == "aggregate":
        aggregate()
    else:
        raise SystemExit(__doc__)
