"""OPA-COUPLER-003: wavelength and fabrication sensitivity of the layout coupler.

The coupler in OPA-LAYOUT-001 (500 x 220 nm silicon in SiO2, 236 nm gap,
23.0 um straight section, gdsfactory S-bends) splits 50:50 at 1.55 um
(OPA-COUPLER-002). This experiment asks how that split moves with wavelength
and with fabrication errors, for this exact geometry, bends included.

Method (coupled-mode / local supermode theory):

    kappa^2 = sin^2(phi_b + pi * L / (2 * L_c(g0))),
    phi_b   = integral over the S-bends of pi / (2 * L_c(g(x))) dx,

where L_c(g) is the coupling length of a straight pair with gap g from MPB
(100 px/um, as in OPA-COUPLER-001) and g(x) is the gap profile read from the
exported layout polygons (simulations/meep/geometry/coupler_gap0.236.json),
corrected from vertical to perpendicular gap. ln L_c is interpolated linearly
in g (evanescent coupling decays exponentially with the gap).

Validation, fixed before the first run: the modelled bend phase at 1.55 um
must lie within 20 % of the 3D FDTD value from OPA-COUPLER-002 (0.0906 rad at
24 px/um). The sweeps then anchor the bend phase to FDTD at 1.55 um and use the
model only for its change with wavelength or geometry.

Fabrication scenarios at 1.55 um, each +-10 nm:
    width only; gap only; and an etch bias that widens the waveguides and
    narrows the gap by the same amount (centre spacing fixed).
"""
import json
import math
from pathlib import Path
import sys
import time

import meep as mp
from meep import mpb

OUT = Path("results/opa-coupler-003")
GEOMETRY = Path("simulations/meep/geometry/coupler_gap0.236.json")
COUPLER_002 = Path("results/opa-coupler-002/result.json")
WL0, WIDTH, HEIGHT, GAP0 = 1.55, 0.50, 0.22, 0.236
STRAIGHT = 23.0                      # um, OPA-LAYOUT-001
RES, CELL = 100, (6.0, 3.0)
GAP_GRID = (0.216, 0.236, 0.256, 0.30, 0.35, 0.45, 0.60, 0.80)
WAVELENGTHS = [round(1.50 + 0.01 * i, 2) for i in range(11)]
DELTA = 0.010
BEND_PHASE_TOLERANCE = 0.20          # pre-registered
TE_PAIR = (mp.EVEN_Z + mp.ODD_Y, mp.EVEN_Z + mp.EVEN_Y)


def n_si(wl):
    l2, l1 = wl * wl, 1.1071
    return math.sqrt(11.6858 + 0.939816 / l2 + 0.00810461 * l1 ** 2 / (l2 - l1 ** 2))


def n_sio2(wl):
    l2 = wl * wl
    return math.sqrt(1 + 0.6961663 * l2 / (l2 - 0.0684043 ** 2)
                     + 0.4079426 * l2 / (l2 - 0.1162414 ** 2)
                     + 0.8974794 * l2 / (l2 - 9.896161 ** 2))


def neff(wl, parity, gap, width):
    si = mp.Medium(index=n_si(wl))
    size = mp.Vector3(mp.inf, width, HEIGHT)
    offset = (width + gap) / 2
    geometry = [mp.Block(center=mp.Vector3(0, s * offset, 0), size=size, material=si)
                for s in (-1, 1)]
    ms = mpb.ModeSolver(geometry_lattice=mp.Lattice(size=mp.Vector3(0, *CELL)),
                        geometry=geometry, default_material=mp.Medium(index=n_sio2(wl)),
                        resolution=RES, num_bands=1)
    ms.verbose = False
    f = 1 / wl
    k = ms.find_k(parity, f, 1, 1, mp.Vector3(1), 1e-10, f * 2.4, f * n_sio2(wl), f * n_si(wl))
    return float(k[0] / f)


def coupling_length(wl, gap, width):
    ns, na = (neff(wl, p, gap, width) for p in TE_PAIR)
    return wl / (2 * abs(ns - na))


class LcTable:
    """ln L_c interpolated linearly in gap, extrapolated beyond the grid."""

    def __init__(self, wl, width):
        self.gaps = list(GAP_GRID)
        self.ln_lc = [math.log(coupling_length(wl, g, width)) for g in self.gaps]

    def __call__(self, gap):
        g, y = self.gaps, self.ln_lc
        i = 0 if gap <= g[0] else len(g) - 2 if gap >= g[-1] else \
            max(k for k in range(len(g) - 1) if g[k] <= gap)
        t = (gap - g[i]) / (g[i + 1] - g[i])
        return math.exp(y[i] + t * (y[i + 1] - y[i]))


def gap_profile(step=0.01):
    """(x, perpendicular gap) along the L = 0 coupler, from the layout polygons."""
    data = json.loads(GEOMETRY.read_text())["lengths"]["0"]
    polys = data["polygons"]

    def yrange(poly, x):
        ys = []
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            if (x1 - x) * (x2 - x) <= 0 and x1 != x2:
                ys.append(y1 + (y2 - y1) * (x - x1) / (x2 - x1))
        return min(ys), max(ys)

    centre_y = [sum(p[1] for p in poly) / len(poly) for poly in polys]
    top, bot = (polys[0], polys[1]) if centre_y[0] > centre_y[1] else (polys[1], polys[0])
    x0, x1 = data["ports"]["o1"][0], data["ports"]["o3"][0]
    profile, n = [], int(round((x1 - x0) / step))
    for i in range(n + 1):
        x = x0 + i * step
        t_lo, t_hi = yrange(top, x)
        b_lo, b_hi = yrange(bot, x)
        cos_angle = WIDTH / (t_hi - t_lo)       # vertical width = w / cos(angle)
        profile.append((x, (t_lo - b_hi) * cos_angle))
    return profile, step


def bend_phase(table, profile, step, gap_shift=0.0):
    """Coupled-mode phase accumulated over the S-bends (L = 0 coupler)."""
    return sum(math.pi / (2 * table(g + gap_shift)) * step for _, g in profile)


def kappa2(phi_b, lc, length=STRAIGHT):
    return math.sin(phi_b + math.pi * length / (2 * lc)) ** 2


checks, failures = {}, []


def check(name, ok, detail):
    checks[name] = {"passed": bool(ok), "detail": detail}
    if not ok:
        failures.append(name)


start = time.time()
profile, step = gap_profile()
fdtd = json.loads(COUPLER_002.read_text())
phi_fdtd = fdtd["bend_phase_from_L0_rad"]["24"]

# Nominal at 1.55 um and validation of the bend model
table0 = LcTable(WL0, WIDTH)
lc0 = table0(GAP0)
phi_model0 = bend_phase(table0, profile, step)
rel = abs(phi_model0 - phi_fdtd) / phi_fdtd
check("bend_model_matches_fdtd", rel < BEND_PHASE_TOLERANCE,
      f"modelled bend phase {phi_model0:.4f} rad vs 3D FDTD {phi_fdtd:.4f} rad "
      f"({rel:.1%}; limit {BEND_PHASE_TOLERANCE:.0%}, fixed before the first run)")
scale = phi_fdtd / phi_model0      # anchor the model to FDTD at 1.55 um
nominal = kappa2(phi_fdtd, lc0)
check("nominal_is_fifty_fifty", abs(nominal - 0.5) < 0.01,
      f"23.0 um coupler at 1.55 um splits {nominal:.4f} (limit 0.5 +- 0.01)")

# Wavelength sweep
spectrum = []
for wl in WAVELENGTHS:
    table = table0 if wl == WL0 else LcTable(wl, WIDTH)
    lc = table(GAP0)
    phi = bend_phase(table, profile, step) * scale
    k2 = kappa2(phi, lc)
    spectrum.append({"wavelength_um": wl, "coupling_length_um": lc, "bend_phase_rad": phi,
                     "cross_fraction": k2, "split_error": abs(k2 - 0.5)})
k2s = [r["cross_fraction"] for r in spectrum]
check("cross_fraction_monotonic_in_wavelength",
      all(a < b for a, b in zip(k2s, k2s[1:])),
      "coupling strengthens with wavelength, so the cross fraction rises across the band")
band = [r["wavelength_um"] for r in spectrum if r["split_error"] <= 0.05]

# Fabrication at 1.55 um
tables = {WIDTH: table0}
for w in (WIDTH - DELTA, WIDTH + DELTA):
    tables[w] = LcTable(WL0, w)
scenarios = {
    "width -10 nm": (WIDTH - DELTA, 0.0), "width +10 nm": (WIDTH + DELTA, 0.0),
    "gap -10 nm": (WIDTH, -DELTA), "gap +10 nm": (WIDTH, +DELTA),
    "etch bias +10 nm (wider, smaller gap)": (WIDTH + DELTA, -DELTA),
    "etch bias -10 nm (narrower, larger gap)": (WIDTH - DELTA, +DELTA),
}
fabrication = []
for label, (w, dg) in scenarios.items():
    table = tables[w]
    lc = table(GAP0 + dg)
    phi = bend_phase(table, profile, step, dg) * scale
    k2 = kappa2(phi, lc)
    fabrication.append({"scenario": label, "width_um": w, "gap_shift_um": dg,
                        "coupling_length_um": lc, "bend_phase_rad": phi,
                        "cross_fraction": k2, "split_error": abs(k2 - 0.5),
                        "mzi_naive_matrix_error_estimate": 1.3 * abs(k2 - 0.5)})

report = {
    "experiment": "OPA-COUPLER-003",
    "goal": "Wavelength and fabrication sensitivity of the OPA-LAYOUT-001 coupler "
            "(236 nm gap, 23.0 um straight section, S-bends included)",
    "method": "Local supermode (coupled-mode) theory: straight L_c from MPB at "
              f"{RES} px/um; bend phase integrated over the layout gap profile and "
              "anchored to the 3D FDTD bend phase at 1.55 um",
    "meep_version": str(getattr(mp, "__version__", "unknown")),
    "python_version": sys.version.split()[0],
    "geometry": str(GEOMETRY),
    "straight_length_um": STRAIGHT,
    "gap_grid_um": list(GAP_GRID),
    "bend_phase_1550": {"model_rad": phi_model0, "fdtd_rad": phi_fdtd,
                        "model_over_fdtd": phi_model0 / phi_fdtd},
    "nominal_cross_fraction_1550": nominal,
    "wavelength_response": spectrum,
    "wavelengths_within_5pct_of_50_50_um": band,
    "fabrication_1550": fabrication,
    "checks": checks,
    "failures": failures,
    "runtime_seconds": time.time() - start,
    "limitations": [
        "Coupled-mode theory with local straight-pair supermodes; bend curvature and "
        "mode mismatch in the S-bends are ignored apart from the FDTD anchoring",
        "Fabrication changes are uniform (whole coupler); real wafers vary across the die",
        "Thickness, sidewall angle and refractive-index variation are not included",
        "MZI matrix error uses the OPA-MZI-002 rule of thumb (about 1.3 x split error, "
        "without calibration)",
    ],
}
OUT.mkdir(parents=True, exist_ok=True)
text = json.dumps(report, indent=2) + "\n"
(OUT / "result.json").write_text(text, encoding="utf-8")
print(text)
if failures:
    raise SystemExit("OPA-COUPLER-003 failed checks: " + ", ".join(failures))
