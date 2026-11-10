"""OPA-EO-002: how short can the Pockels phase shifters of an MZI mesh get?

OPA-EO-001 found that X-cut TFLN phase shifters hold their phase without power
but make a 64x64 Clements mesh 0.6-3 m long. This experiment quantifies the
ways to shorten them, each with its cost:

1. Electrode gap. A smaller gap raises the field and lowers V_pi*L, but brings
   the gold closer to the mode and adds absorption. V_pi*L comes from the
   OPA-EO-001 chain (MPB mode, electrostatics, perturbation); the absorption
   from a semi-vectorial finite-difference mode solver with the complex
   permittivity of gold (Johnson and Christy, n = 0.559 + 9.81i at 1.55 um).
2. Push-pull drive: both arms, opposite phase, half the length.
3. Folding: the mesh is folded into rows, which turns a length limit into an
   area limit. The area is compared with one 26 x 33 mm reticle.
4. Resonant enhancement: a racetrack ring (all-pass) multiplies the phase
   change near resonance. Analytic model with self-coupling r and round-trip
   loss; the cost is a phase range limit, amplitude ripple and bandwidth.
5. A stronger material: barium titanate in the same rib, as an illustrative
   material swap (r_eff 100-923 pm/V, DC permittivity 1000). Real BTO devices
   use other geometries; this only shows the scaling and the capacitance cost.

Mesh-level comparison for N = 64 (Haar-random unitaries, Clements).

Assumptions, fixed before the first run:
  waveguide loss 0.3 dB/cm (TFLN, UV lithography; 0.027 dB/cm is the best published)
  waveguide pitch = gap + 10 um electrode; area = N * pitch * path * 1.2
  ring bends: radius 50 um
  gap rule: the smallest gap in the sweep whose metal loss is at most 10 % of the
  waveguide loss (0.03 dB/cm)

Pre-registered checks (fixed before the first run):
  sv_solver_tm_slab            semi-vectorial solver vs analytic TM slab, < 0.3 %
  sv_matches_mpb_no_metal      semi-vectorial n_eff vs MPB without electrodes, < 1.5 %
  eo001_reproduced             dn_eff/dV at 5 um gap equals OPA-EO-001 within 0.5 %
  metal_loss_converged         loss at 5 um gap changes < 15 % from 20 to 10 nm grid
  metal_loss_decreases_with_gap
  vpil_increases_with_gap
  ring_model_lossless          |t| = 1 for a lossless ring; phase covers 2 pi per FSR
  mesh_decomposition_exact     every decomposed mesh reproduces its unitary to 1e-9
  metal_loss_literature_range  (non-blocking) loss at 5 um gap in 0.001-0.1 dB/cm;
                               published simulations give 0.005-0.035 dB/cm at
                               4.8-6.5 um gaps
"""
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import scipy
import meep as mp

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "circuit"))
import eo_common as ec  # noqa: E402
from eo_common import LN, Film, WL  # noqa: E402
from mesh import clements_decompose, mesh_matrix  # noqa: E402
from mzi import haar_unitary  # noqa: E402

OUT = Path("results/opa-eo-002")
EO001 = Path("results/opa-eo-001/result.json")
GAPS = (3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
GOLD = complex(0.559, 9.81) ** 2
ALPHA_WG = 0.3                  # dB/cm
METAL_LIMIT = 0.1 * ALPHA_WG    # gap rule
RETICLE_MM2 = 26 * 33
AREA_OVERHEAD = 1.2
COUPLER_OVERHEAD = 100.0        # um per column
BEND_R = 50.0                   # um
RING_R = (0.8, 0.9, 0.95)       # self-coupling of the ring
N_MESH = 64
V_MAX = (5.0, 10.0)
BTO = Film("BaTiO3 (illustrative swap)", 2.28, 2.28, 1000.0, 1000.0, 1e-12)  # r per pm/V
BTO_R = (100.0, 300.0, 923.0)

NON_BLOCKING = {"metal_loss_literature_range"}
checks, failures = {}, []


def check(name, ok, detail):
    checks[name] = {"passed": bool(ok), "blocking": name not in NON_BLOCKING, "detail": detail}
    if not ok:
        failures.append(name)
    print(("PASS " if ok else "FAIL ") + name + ": " + json.dumps(detail), flush=True)


# ---------------------------------------------------------------------------
# Semi-vectorial loss model
# ---------------------------------------------------------------------------
Y_HALF, Z_LO, Z_HI = 9.0, -1.5, 1.4


def eps_grid(film, gap, h, metal=True, sub=5):
    """Node permittivity (E_y component), averaged over sub x sub samples."""
    y = np.arange(-Y_HALF, Y_HALF + h / 2, h)
    z = np.arange(Z_LO, Z_HI + h / 2, h)
    off = (np.arange(sub) + 0.5) / sub - 0.5
    eps = np.zeros((len(y), len(z)), complex)
    for oy in off:
        for oz in off:
            Y, Z = np.meshgrid(y + oy * h, z + oz * h, indexing="ij")
            e = np.where(Z < 0, ec.N_SIO2 ** 2, 1.0).astype(complex)
            fm = ((Z >= 0) & (Z < ec.SLAB)) | ((Z >= ec.SLAB) & (Z < ec.FILM)
                                               & (np.abs(Y) < ec.RIB_W / 2))
            e = np.where(fm, film.n_e ** 2, e)
            if metal:
                gold = ((np.abs(Y) >= gap / 2) & (Z >= ec.SLAB)
                        & (Z < ec.SLAB + ec.ELECTRODE_T))
                e = np.where(gold, GOLD, e)
            eps += e
    return y, z, eps / sub ** 2


def rib_score(y, z):
    Y, Z = np.meshgrid(y, z, indexing="ij")
    core = (np.abs(Y) < 1.0) & (Z > 0) & (Z < ec.FILM)

    def score(f):
        p = np.abs(f) ** 2
        return float(p[core].sum() / p.sum())
    return score


def sv_mode(film, gap, h, metal=True, n_guess=1.9):
    y, z, eps = eps_grid(film, gap, h, metal)
    n, f = ec.sv_te_mode(eps, h, n_guess, k=4, select=rib_score(y, z))
    return n, rib_score(y, z)(f)


def tm_slab_check():
    from scipy.optimize import brentq
    n1, n2, d, h = 2.2, 1.444, 0.6, 0.02
    k0 = 2 * math.pi / WL

    def tm(n):
        kx, g = k0 * math.sqrt(n1 ** 2 - n ** 2), k0 * math.sqrt(n ** 2 - n2 ** 2)
        return kx * math.sin(kx * d / 2) - (n1 ** 2 / n2 ** 2) * g * math.cos(kx * d / 2)
    ns = np.linspace(n2 + 1e-6, n1 - 1e-6, 2000)
    v = [tm(x) for x in ns]
    i = max(i for i in range(len(v) - 1) if v[i] * v[i + 1] < 0)
    n_exact = brentq(tm, ns[i], ns[i + 1])
    y = np.arange(-3.0, 3.0 + h / 2, h)
    z = np.arange(h, 1.0, h)
    sub = np.linspace(-h / 2, h / 2, 9)
    frac = np.array([np.mean(np.abs(yy + sub) < d / 2) for yy in y])
    eps = (frac * n1 ** 2 + (1 - frac) * n2 ** 2)[:, None] * np.ones(len(z))
    n, _ = ec.sv_te_mode(eps.astype(complex), h, n_exact, k=1)
    lz = (len(z) + 1) * h                         # Dirichlet just outside the grid
    n_slab = math.sqrt((k0 * n.real) ** 2 + (math.pi / lz) ** 2) / k0
    return n_slab, n_exact


# ---------------------------------------------------------------------------
# Ring (racetrack, all-pass) model
# ---------------------------------------------------------------------------
def ring_t(theta, r, a):
    e = np.exp(1j * theta)
    return (r - a * e) / (1 - r * a * e)


def ring_window(r, a, target):
    """Smallest symmetric round-trip detuning window around resonance whose
    phase response spans `target`; returns (window, ripple_dB, slope_max)."""
    def span(w):
        th = np.linspace(-w / 2, w / 2, 4001)
        ph = np.unwrap(np.angle(ring_t(th, r, a)))
        return ph.max() - ph.min(), th
    lo, hi = 1e-6, 2 * math.pi - 1e-6
    if span(hi)[0] < target:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if span(mid)[0] < target else (lo, mid)
    _, th = span(hi)
    p = np.abs(ring_t(th, r, a)) ** 2
    ph = np.unwrap(np.angle(ring_t(th, r, a)))
    slope = float(np.max(np.abs(np.gradient(ph, th))))
    return hi, float(10 * np.log10(p.max() / p.min())), slope


def ring_shifter(r, target, a_eo, vmax, ng):
    """Electrode length on a racetrack (both straights) that reaches `target`
    phase range with +-vmax, iterating on the round-trip loss."""
    ls = 1000.0                                   # um, start
    for _ in range(30):
        l_rt = 2 * ls + 2 * math.pi * BEND_R
        a = 10 ** (-ALPHA_WG * l_rt * 1e-4 / 20)  # field round-trip transmission
        res = ring_window(r, a, target)
        if res is None:
            return None
        window, ripple, slope = res
        # +-vmax over both straights gives a round-trip detuning of window
        ls_new = window * WL / (2 * math.pi * a_eo * 2 * vmax * 2) * 1.0
        if abs(ls_new - ls) < 1e-3:
            break
        ls = ls_new
    l_rt = 2 * ls + 2 * math.pi * BEND_R
    fsr_nm = WL ** 2 / (ng * l_rt) * 1e3
    bw_nm = 0.05 / (slope * 2 * math.pi * ng * l_rt / WL ** 2) * 1e3   # 0.05 rad error
    return {"electrode_length_per_straight_um": ls, "round_trip_um": l_rt,
            "detuning_window_rad": window, "amplitude_ripple_dB": ripple,
            "fsr_nm": fsr_nm, "bandwidth_nm_for_0.05rad": bw_nm,
            "footprint_um": [ls + 2 * BEND_R, 2 * BEND_R]}


# ---------------------------------------------------------------------------
start = time.time()
OUT.mkdir(parents=True, exist_ok=True)
result = {"experiment": "OPA-EO-002",
          "goal": "Ways to shorten Pockels phase shifters in an MZI mesh, and their costs",
          "versions": {"meep": mp.__version__, "numpy": np.__version__, "scipy": scipy.__version__},
          "assumptions": {"waveguide_loss_dB_per_cm": ALPHA_WG, "gold_eps": [GOLD.real, GOLD.imag],
                          "pitch": "gap + 10 um", "area_overhead": AREA_OVERHEAD,
                          "coupler_overhead_um_per_column": COUPLER_OVERHEAD,
                          "ring_bend_radius_um": BEND_R, "reticle_mm2": RETICLE_MM2,
                          "gap_rule": f"smallest gap with metal loss <= {METAL_LIMIT} dB/cm"}}

n_slab, n_exact = tm_slab_check()
check("sv_solver_tm_slab", abs(n_slab / n_exact - 1) < 3e-3,
      {"semi_vectorial": n_slab, "analytic": n_exact})

mode = ec.film_mode(LN, 48)
n_sv0, score0 = sv_mode(LN, 5.0, 0.02, metal=False, n_guess=mode.neff)
check("sv_matches_mpb_no_metal", abs(n_sv0.real / mode.neff - 1) < 0.015,
      {"semi_vectorial": n_sv0.real, "mpb": mode.neff, "rib_power_fraction": score0})

# ---- 1. gap sweep -----------------------------------------------------------
eo001 = json.loads(EO001.read_text())["pockels"]
sweep = []
for gap in GAPS:
    es = ec.electrostatics(LN, gap, 0.02)
    a = ec.eo_dneff_per_volt(mode, es, LN)
    n_m, score = sv_mode(LN, gap, 0.02, n_guess=mode.neff)
    loss = ec.loss_db_per_cm(n_m)
    vpil = WL * 1e-6 / (2 * a) * 100
    row = {"gap_um": gap, "dneff_per_V": a, "vpi_L_single_V_cm": vpil,
           "vpi_L_push_pull_V_cm": vpil / 2, "metal_loss_dB_per_cm": loss,
           "fom_push_pull_V_dB": vpil / 2 * loss, "capacitance_pF_per_mm": es["cap"] * 1e9,
           "rib_power_fraction": score}
    sweep.append(row)
    print(json.dumps(row), flush=True)
g5 = next(r for r in sweep if r["gap_um"] == 5.0)
check("eo001_reproduced", abs(g5["dneff_per_V"] / eo001["dneff_per_V"] - 1) < 5e-3,
      {"this_run": g5["dneff_per_V"], "opa_eo_001": eo001["dneff_per_V"]})
n_fine, _ = sv_mode(LN, 5.0, 0.01, n_guess=mode.neff)
loss_fine = ec.loss_db_per_cm(n_fine)
check("metal_loss_converged", abs(g5["metal_loss_dB_per_cm"] / loss_fine - 1) < 0.15,
      {"loss_20nm": g5["metal_loss_dB_per_cm"], "loss_10nm": loss_fine})
losses = [r["metal_loss_dB_per_cm"] for r in sweep]
vpils = [r["vpi_L_single_V_cm"] for r in sweep]
check("metal_loss_decreases_with_gap", all(x > y for x, y in zip(losses, losses[1:])),
      {"loss_dB_per_cm": losses})
check("vpil_increases_with_gap", all(x < y for x, y in zip(vpils, vpils[1:])),
      {"vpi_L_V_cm": vpils})
check("metal_loss_literature_range", 0.001 <= loss_fine <= 0.1,
      {"loss_dB_per_cm_at_5um": loss_fine, "range": [0.001, 0.1]})
ok_gaps = [r for r in sweep if r["metal_loss_dB_per_cm"] <= METAL_LIMIT]
chosen = min(ok_gaps, key=lambda r: r["gap_um"]) if ok_gaps else g5
result["gap_sweep"] = {"rows": sweep, "loss_5um_10nm_grid": loss_fine,
                       "chosen_gap_um": chosen["gap_um"]}

# ---- 4. ring ----------------------------------------------------------------
th = np.linspace(-math.pi, math.pi, 2001)
t0 = ring_t(th, 0.9, 1.0)
lossless_ok = np.max(np.abs(np.abs(t0) - 1)) < 1e-12
span = np.unwrap(np.angle(t0))
check("ring_model_lossless", lossless_ok and abs(abs(span[-1] - span[0]) - 2 * math.pi) < 1e-2,
      {"max_abs_t_minus_1": float(np.max(np.abs(np.abs(t0) - 1))),
       "phase_span_per_fsr": float(abs(span[-1] - span[0]))})
a_c = chosen["dneff_per_V"]
ring = {}
for r in RING_R:
    for name, target in (("pi", math.pi), ("2pi_minus_0.1", 2 * math.pi - 0.1)):
        res = ring_shifter(r, target, a_c, 5.0, mode.ng)
        if res:
            # straight push-pull shifter with the same range and drive: +-V gives +-pi
            # over L_pi = lambda / (2 a V), push-pull halves it
            straight_um = WL / (2 * a_c * 5.0) * target / (2 * math.pi) / 2
            res["straight_push_pull_length_um_same_range"] = straight_um
            res["footprint_length_reduction"] = straight_um / res["footprint_um"][0]
        ring[f"r{r}_{name}"] = res
        print(f"r{r}_{name}", json.dumps(res), flush=True)
result["ring"] = {"vmax_V": 5.0, "gap_um": chosen["gap_um"], "cases": ring}

# ---- 5. BTO swap ------------------------------------------------------------
bmode = ec.film_mode(BTO, 48)
bes = ec.electrostatics(BTO, 5.0, 0.02)
b_per_pm = ec.eo_dneff_per_volt(bmode, bes, BTO)
result["bto_swap"] = {
    "note": "Same rib with BaTiO3 optical index 2.28 and DC permittivity 1000; r_eff is "
            "a parameter. Illustrative only: published BTO devices use other geometries.",
    "n_eff": bmode.neff, "capacitance_pF_per_mm": bes["cap"] * 1e9,
    "cases": {f"r{r:g}pm_per_V": {"vpi_L_push_pull_V_cm": WL * 1e-6 / (2 * b_per_pm * r) * 100 / 2}
              for r in BTO_R}}
print(json.dumps(result["bto_swap"]), flush=True)

# ---- mesh level --------------------------------------------------------------
rng = np.random.default_rng(2026)
fracs, worst, thetas = [], 0.0, []
for _ in range(2):
    u = haar_unitary(N_MESH, rng)
    ops, out = clements_decompose(u)
    worst = max(worst, float(np.max(np.abs(mesh_matrix(ops, out) - u))))
    ph = np.array([p for _, t, f in ops for p in (t, f)] + list(out))
    fracs.append(np.abs(np.angle(np.exp(1j * ph))) / np.pi)
check("mesh_decomposition_exact", worst < 1e-9, {"max_abs_error": worst})
frac = np.concatenate(fracs)
n_shifters = len(frac) // 2


def mesh_config(name, gap_row, push_pull, vmax, folded, theta_len_um=None, ring_loss_db=0.0,
                film_cap=None, a=None):
    a = a or gap_row["dneff_per_V"]
    straight = WL / (2 * a * vmax) / (2 if push_pull else 1)          # um for +-pi
    l_theta = theta_len_um if theta_len_um is not None else straight
    path_um = N_MESH * (l_theta + straight + COUPLER_OVERHEAD) + straight
    alpha = ALPHA_WG + gap_row["metal_loss_dB_per_cm"]
    loss_db = path_um * 1e-4 * alpha + N_MESH * ring_loss_db
    pitch = gap_row["gap_um"] + ec.ELECTRODE_W
    area = N_MESH * pitch * path_um * 1e-6 * AREA_OVERHEAD                 # mm^2
    cap = (film_cap or gap_row["capacitance_pF_per_mm"]) * 1e-12 / 1e-3   # F/m
    arms = 2 if push_pull else 1
    energy = float(np.sum(cap * straight * 1e-6 * arms * (frac * vmax) ** 2) / len(fracs))
    return {"config": name, "gap_um": gap_row["gap_um"], "push_pull": push_pull, "vmax_V": vmax,
            "folded": folded, "shifter_length_mm": straight / 1e3,
            "theta_shifter_length_mm": l_theta / 1e3, "path_length_mm": path_um / 1e3,
            "path_loss_dB": loss_db, "area_mm2": area,
            "fits_one_reticle": bool(folded and area <= RETICLE_MM2),
            "straight_mesh_length_mm": path_um / 1e3, "program_energy_nJ": energy * 1e9}


configs = []
for vmax in V_MAX:
    configs.append(mesh_config("EO-001 baseline (5 um gap, one arm)", g5, False, vmax, False))
    configs.append(mesh_config("push-pull", g5, True, vmax, False))
    configs.append(mesh_config(f"push-pull, {chosen['gap_um']:g} um gap", chosen, True, vmax, False))
    configs.append(mesh_config(f"push-pull, {chosen['gap_um']:g} um gap, folded", chosen, True,
                               vmax, True))
    rc = ring.get("r0.9_pi")
    if rc and vmax == 5.0:
        configs.append(mesh_config(
            f"push-pull, {chosen['gap_um']:g} um gap, folded, ring-assisted theta (r = 0.9)",
            chosen, True, vmax, True, theta_len_um=rc["footprint_um"][0],
            ring_loss_db=rc["amplitude_ripple_dB"]))
    bto = result["bto_swap"]["cases"]["r300pm_per_V"]["vpi_L_push_pull_V_cm"]
    a_bto = WL * 1e-6 / (2 * bto * 2 / 100)
    configs.append(mesh_config("BTO swap, r_eff 300 pm/V, push-pull, folded (illustrative)",
                               g5 | {"metal_loss_dB_per_cm": g5["metal_loss_dB_per_cm"]}, True,
                               vmax, True, film_cap=result["bto_swap"]["capacitance_pF_per_mm"],
                               a=a_bto))
for c in configs:
    print(json.dumps(c), flush=True)
result["mesh"] = {"N": N_MESH, "phase_shifters": n_shifters,
                  "notes": ["path: N columns of a theta and a phi shifter plus 100 um, plus the "
                            "output phases", "ring ripple counted once per column as worst-case "
                            "excess loss", "single-arm shifters need an equal dummy arm, so the "
                            "area uses the same pitch"],
                  "configs": configs}

blocking = [f for f in failures if f not in NON_BLOCKING]
result["checks"] = checks
result["passed_all_preregistered"] = not failures
result["passed_blocking"] = not blocking
result["non_blocking_failures"] = [f for f in failures if f in NON_BLOCKING]
result["runtime_s"] = round(time.time() - start, 1)
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(f"{len(checks) - len(failures)}/{len(checks)} checks passed in {result['runtime_s']} s")
sys.exit(1 if blocking else 0)
