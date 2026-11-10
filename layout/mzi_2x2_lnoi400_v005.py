"""OPA-LAYOUT-005: electro-optic 2x2 MZI in Luxtelligence lnoi400 (thin-film lithium niobate).

Supersedes OPA-LAYOUT-004, the passive chip sent to EuroCDP (as OPA 0.24) and
rebuilt from the PDK. This version makes the MZI active and fixes the unequal
routes of 0.24:

  - the PDK's push-pull Mach-Zehnder modulator (mzm_unbalanced) with 2x2 MMI
    couplers, balanced arms (length_imbalance = 0) and a 5 mm ground-signal-ground
    (GSG) travelling-wave electrode with RF pads at both ends: the Pockels effect
    sets the MZI phase theta,
  - the PDK's thermal bias heater on one arm, with two DC pads, for slow bias
    without DC drift,
  - the modulator centred between the facet pairs, so the two inputs and the two
    outputs reach it through mirror-image S-bends of equal length,
  - the PDK chip frame (10 x 5 mm), edge couplers at 127 um pitch, and labels at
    every optical and electrical port.

Checks:
  1. four facet ports on the two chip edges, 127 um apart on each,
  2. the expected PDK cells: 4 edge couplers, 1 modulator,
  3. every optical port of every instance connected (layout/port_check.py),
  4. all LN inside the chip frame, only edge couplers in the exclusion zone, and
     all metal inside the chip contour,
  5. only lnoi400 layers,
  6. a label at every optical and electrical port,
  7. equal route lengths for the two inputs and for the two outputs,
  8. electrodes: three separate GSG conductors with two RF pads, one heater with
     two pads, and no metal shared between them,
  9. V_pi from the PDK's own compact model (sax) of the push-pull modulator,
 10. a byte-for-byte reproducible GDS.

Not done: the lnoi400 DRC (its runset is distributed by Luxtelligence on
request), RF design (impedance, velocity matching, termination), simulation of
the chip, and any foundry review. Only theta is tunable (EO and thermal); there
are no phi, a or b phase shifters.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import gdsfactory as gf
import klayout.db as kdb
import lnoi400
from lnoi400 import cells
from lnoi400.tech import LAYER
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from port_check import optical_port_check  # noqa: E402

OUT = Path("results/opa-layout-005")
NAME = "OPA_LAYOUT_005"
PDK_COMMIT = "d16db6a4882657feb1ce696c16c604ff6cb7ccfa"
XS = "xs_rwg1000"
DIE = (10_000.0, 5_000.0)
FIBER_PITCH = 127.0
LN_LAYERS = ((2, 0), (3, 0), (3, 1))
TL, HT = (21, 0), (21, 1)
CONTOUR, EXCLUSION, LABELS = (6, 0), (6, 1), (4, 0)
MODULATION_LENGTH = 5000.0
MZM = dict(modulation_length=MODULATION_LENGTH, length_imbalance=0.0,
           splitter="mmi2x2_optimized1550", with_heater=True)
SBEND_LENGTH = 600.0
TOL = 1e-3
MZI_MARKER_PORTS = ("upper_taper_start", "short_bias_branch_start", "long_bias_branch_start")
PAD_NAMES = {"e1": "rf_in", "e2": "rf_out", "e3": "heater_1", "e4": "heater_2"}


def chip():
    c = gf.Component(NAME)
    c << gf.get_component("chip_frame", size=DIE, center=(DIE[0] / 2, DIE[1] / 2))
    mzm = c << cells.mzm_unbalanced(**MZM)
    ec = gf.get_component("double_linear_inverse_taper")
    ec_len = ec.ports["o2"].dcenter[0] - ec.ports["o1"].dcenter[0]
    y0 = DIE[1] / 2
    span = ec_len + SBEND_LENGTH
    straight = (DIE[0] - 2 * span - mzm.dxsize) / 2
    mzm.dmove((ec_len + straight + SBEND_LENGTH - mzm.ports["o1"].dcenter[0], y0))
    routes = {}
    for side, ports in (("in", ("o1", "o2")), ("out", ("o4", "o3"))):
        for k, name in enumerate(ports, start=1):
            facet_y = y0 + (k - 1.5) * FIBER_PITCH
            p = mzm.ports[name]
            # the S-bend leaves the modulator port in its own frame: towards -x (rotated
            # 180 degrees) on the input side, so its local offset has the opposite sign
            dy = (facet_y - p.dcenter[1]) * (-1 if side == "in" else 1)
            bend = c << gf.components.bend_s(size=(SBEND_LENGTH, dy), cross_section=XS)
            bend.connect("o1", p)
            s = c << gf.components.straight(length=straight, cross_section=XS)
            s.connect("o1", bend.ports["o2"])
            e = c << ec
            e.connect("o2", s.ports["o2"])
            c.add_port(f"{side}{k}", port=e.ports["o1"])
            routes[f"{side}{k}"] = [bend, s, e]
    for name, label in PAD_NAMES.items():
        c.add_port(label, port=mzm.ports[name])
    for p in c.ports:
        c.add_label(text=p.name, position=p.dcenter, layer=LABELS)
    return c, routes


def route_length(parts):
    total = 0.0
    for inst in parts:
        info = inst.cell.info
        if "length" in info:
            total += float(info["length"])
        elif "route_info_length" in info:
            total += float(info["route_info_length"])
        else:                                   # edge coupler: port-to-port distance
            a, b = inst.ports["o1"].dcenter, inst.ports["o2"].dcenter
            total += float(np.hypot(a[0] - b[0], a[1] - b[1]))
    return total


def region(layout, cell, layer):
    li = layout.find_layer(*layer)
    if li is None:
        return kdb.Region()
    return kdb.Region(cell.begin_shapes_rec(li)).merged()


def count_cells(component):
    counts = {}

    def walk(cell):
        for inst in cell.insts:
            counts[inst.cell.name] = counts.get(inst.cell.name, 0) + 1
            walk(inst.cell)
    walk(component)
    return counts


def model_vpi():
    """Push-pull V_pi of the PDK's sax model: the smallest V_dc with minimum transmission."""
    from lnoi400 import models
    v = np.linspace(0.0, 20.0, 2001)
    t = np.array([abs(complex(models.mzm_unbalanced(
        wl=1.55, length_imbalance=0.0, modulation_length=MODULATION_LENGTH, V_dc=float(x))
        ["o1", "o2"])) ** 2 for x in v])
    i = int(np.argmin(t[: int(len(v) * 0.75)]))
    return float(v[i]), float(t[0]), float(t[i])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c, routes = chip()
    gds = OUT / "mzi_2x2_lnoi400_eo.gds"
    c.write_gds(gds, with_metadata=False)
    sha = hashlib.sha256(gds.read_bytes()).hexdigest()
    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    ly = kdb.Layout()
    ly.read(str(gds))
    top = ly.top_cells()[0]
    contour = region(ly, top, CONTOUR)
    exclusion = region(ly, top, EXCLUSION)
    cbox = contour.bbox().to_dtype(ly.dbu)

    optical = {p.name: p for p in c.ports if p.port_type == "optical"}
    left = sorted(p.dcenter[1] for p in optical.values() if abs(p.dcenter[0] - cbox.left) < TOL)
    right = sorted(p.dcenter[1] for p in optical.values() if abs(p.dcenter[0] - cbox.right) < TOL)
    check("facet_ports",
          len(optical) == 4 and len(left) == 2 and len(right) == 2
          and abs(left[1] - left[0] - FIBER_PITCH) < TOL
          and abs(right[1] - right[0] - FIBER_PITCH) < TOL,
          f"optical ports {[(n, [round(v, 3) for v in p.dcenter]) for n, p in sorted(optical.items())]}")

    counts = count_cells(c)
    n_ec = sum(n for k, n in counts.items() if k.startswith("double_linear_inverse_taper"))
    n_mzm = sum(n for k, n in counts.items() if k.startswith("mzm_unbalanced"))
    check("pdk_cells", n_ec == 4 and n_mzm == 1,
          f"{n_ec} double_linear_inverse_taper, {n_mzm} mzm_unbalanced (expected 4, 1)")

    n_ports, port_problems = optical_port_check(c, ignore_ports=MZI_MARKER_PORTS)
    check("optical_ports_connected", n_ports > 0 and not port_problems,
          f"{n_ports} optical instance ports checked in every cell (ignoring the MZI's "
          f"marker ports {list(MZI_MARKER_PORTS)}); problems: {port_problems or 'none'}")

    ln = kdb.Region()
    for layer in LN_LAYERS:
        ln += region(ly, top, layer)
    ln.merge()
    metal = (region(ly, top, TL) + region(ly, top, HT)).merged()
    ec_boxes = kdb.Region()
    for inst in top.each_inst():
        if inst.cell.name.startswith("double_linear_inverse_taper"):
            ec_boxes.insert(inst.bbox())
    ln_out = ln - (contour + exclusion).merged()
    ln_excl = (ln - contour) - ec_boxes
    metal_out = metal - contour
    a = ly.dbu ** 2
    check("inside_chip_frame", ln_out.is_empty() and ln_excl.is_empty() and metal_out.is_empty(),
          f"LN outside the frame {ln_out.area() * a:.3f} um2; non-edge-coupler LN in the exclusion "
          f"zone {ln_excl.area() * a:.3f} um2; metal outside the contour {metal_out.area() * a:.3f} um2")

    pdk_layers = {(layer.layer, layer.datatype) for layer in LAYER}
    used = sorted({(ly.get_info(i).layer, ly.get_info(i).datatype) for i in ly.layer_indexes()
                   if not top.begin_shapes_rec(i).at_end()})
    unknown = [lay for lay in used if lay not in pdk_layers]
    check("only_lnoi400_layers", not unknown, f"layers used {used}; unknown {unknown}")

    labels = {}
    it = top.begin_shapes_rec(ly.find_layer(*LABELS))
    while not it.at_end():
        if it.shape().is_text():
            t = it.shape().text.transformed(it.trans())
            labels[it.shape().text_string] = (t.x * ly.dbu, t.y * ly.dbu)
        it.next()
    label_ok = len(c.ports) == 8 and all(
        p.name in labels and abs(labels[p.name][0] - p.dcenter[0]) < TOL
        and abs(labels[p.name][1] - p.dcenter[1]) < TOL for p in c.ports)
    check("port_labels", label_ok, f"labels {sorted(labels)}")

    lengths = {k: round(route_length(v), 6) for k, v in routes.items()}
    check("balanced_routes",
          abs(lengths["in1"] - lengths["in2"]) < TOL and abs(lengths["out1"] - lengths["out2"]) < TOL,
          f"route lengths facet to modulator (um): {lengths}")

    tl_nets = list(region(ly, top, TL).each())
    ht_nets = list(region(ly, top, HT).each())
    shared = (region(ly, top, TL) & region(ly, top, HT)).area() * a
    electrical = {p.name: p for p in c.ports if p.port_type == "electrical"}
    rf_on_tl = all(any(kdb.Region(n).interacting(kdb.Region(kdb.DBox(
        electrical[k].dcenter[0] - 1, electrical[k].dcenter[1] - 1,
        electrical[k].dcenter[0] + 1, electrical[k].dcenter[1] + 1).to_itype(ly.dbu))).count()
        for n in tl_nets) for k in ("rf_in", "rf_out"))
    check("electrodes",
          len(tl_nets) == 3 and len(ht_nets) == 1 and shared == 0 and len(electrical) == 4
          and rf_on_tl,
          f"{len(tl_nets)} GSG conductors (TL), {len(ht_nets)} heater (HT), shared metal "
          f"{shared:.3f} um2, electrical ports {sorted(electrical)}, RF pads on TL: {rf_on_tl}")

    vpi, t_0, t_pi = model_vpi()
    vpi_formula = 3.3e4 / MODULATION_LENGTH        # PDK: 2*3.3e4/L per arm, halved by push-pull
    check("vpi_from_pdk_model", abs(vpi - vpi_formula) < 0.05 and t_pi < 0.01 * t_0,
          f"push-pull V_pi = {vpi:.2f} V from the PDK's sax model (transmission {t_0:.3f} -> "
          f"{t_pi:.2e}); formula {vpi_formula:.2f} V, i.e. V_pi*L = 3.3 V cm")

    regenerated = OUT / "mzi_2x2_lnoi400_eo.check.gds"
    subprocess.run([sys.executable, __file__, "--write-gds", str(regenerated)], check=True,
                   capture_output=True)
    same = hashlib.sha256(regenerated.read_bytes()).hexdigest() == sha
    regenerated.unlink()
    check("gds_reproducible", same, "a fresh Python process regenerates a byte-identical GDS file")

    png = OUT / "mzi_2x2_lnoi400_eo.png"
    fig = c.plot()
    import matplotlib.pyplot as plt
    (fig if fig is not None and hasattr(fig, "savefig") else plt.gcf()).savefig(
        png, dpi=150, bbox_inches="tight")
    frame = [round(cbox.width(), 3), round(cbox.height(), 3)]
    eo002 = json.loads(Path("results/opa-eo-002/result.json").read_text())
    gap4 = next(r for r in eo002["gap_sweep"]["rows"] if r["gap_um"] == 4.0)

    report = {
        "experiment": "OPA-LAYOUT-005",
        "goal": "Electro-optic 2x2 MZI in Luxtelligence lnoi400 with balanced routes, "
                "superseding the passive OPA-LAYOUT-004",
        "supersedes": "OPA-LAYOUT-004",
        "pdk": f"lxt_pdk_gf 2.0 at commit {PDK_COMMIT} (MIT)",
        "gdsfactory_version": gf.__version__,
        "python_version": sys.version.split()[0],
        "gds_file": gds.name,
        "gds_sha256": sha,
        "chip_frame_um": frame,
        "modulator": MZM | {"rf_gap_um": 4.0, "rf_central_conductor_width_um": 10.0,
                            "rf_ground_planes_width_um": 180.0},
        "ports": {p.name: {"type": p.port_type, "center_um": [round(v, 3) for v in p.dcenter]}
                  for p in sorted(c.ports, key=lambda q: q.name)},
        "route_lengths_um": lengths,
        "vpi": {"pdk_model_V": round(vpi, 3), "pdk_vpi_L_push_pull_V_cm": 3.3,
                "opa_eo_002_vpi_L_push_pull_V_cm_at_4um_gap": round(gap4["vpi_L_push_pull_V_cm"], 3),
                "note": "OPA-EO-002 modelled a 600 nm film with a 300 nm etch and a 1.2 um rib; "
                        "lnoi400 has its own stack and a 2.5 um modulator rib, so the two numbers "
                        "are not the same device"},
        "cell_counts": {"double_linear_inverse_taper": n_ec, "mzm_unbalanced": n_mzm},
        "layers": used,
        "checks": checks,
        "failures": failures,
        "limitations": [
            "Not checked against the lnoi400 DRC; Luxtelligence distributes the runset on request",
            "No RF design: impedance, velocity matching and termination are the PDK defaults and "
            "have not been simulated",
            "V_pi is the PDK's compact model, not a measurement or a simulation of this chip",
            "Only theta is tunable (Pockels and thermal bias); no phi, a or b phase shifters",
            "No optical simulation of the chip",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sheet = {
        "id": "OPA-LAYOUT-005",
        "title": "Electro-optic 2x2 MZI with GSG electrodes and thermal bias (Luxtelligence lnoi400)",
        "function": "push-pull electro-optic 2x2 MZI (theta), thermal bias",
        "status": "exploratory",
        "supersedes": "OPA-LAYOUT-004",
        "pdk": {"name": "Luxtelligence lnoi400 (lxt_pdk_gf)", "version": f"2.0 @ {PDK_COMMIT[:7]}",
                "open_source": True, "platform": "X-cut thin-film lithium niobate on insulator"},
        "wavelength_um": {"design": 1.55},
        "footprint_um": frame,
        "optical_ports": {"inputs": 2, "outputs": 2, "type": "edge coupler (inverse taper)",
                          "pitch_um": FIBER_PITCH},
        "controls": {"GSG electrodes": 1, "RF pads": 2, "heaters": 1, "DC pads": 2},
        "files": {"gds": gds.name, "preview": png.name},
        "generator": {"script": "layout/mzi_2x2_lnoi400_v005.py",
                      "environment": "layout/requirements-lock-lnoi400.txt"},
        "checks": {"passed": len(checks) - len(failures), "total": len(checks)},
        "key_results": [
            {"name": "Modulator", "value": "PDK push-pull MZM, 2x2 MMIs, 5 mm GSG electrode "
             "(4 um gap)", "source": "OPA-LAYOUT-005"},
            {"name": "V_pi", "value": f"{vpi:.1f} V (V_pi*L 3.3 V cm, PDK compact model)",
             "source": "lnoi400 models.mzm_unbalanced"},
            {"name": "Routes", "value": f"inputs {lengths['in1']:.3f} / {lengths['in2']:.3f} um, "
             f"outputs {lengths['out1']:.3f} / {lengths['out2']:.3f} um", "source": "OPA-LAYOUT-005"},
            {"name": "Optical connectivity", "value": f"{n_ports} instance ports, all connected",
             "source": "layout/port_check.py"},
        ],
        "limitations": ["lnoi400 DRC not run (runset on request)", "no RF design or simulation",
                        "V_pi from the PDK model", "theta only"],
        "tags": ["mzi", "2x2", "electro-optic", "pockels", "push-pull", "mmi", "edge-coupler",
                 "heater", "lnoi400", "tfln", "lithium-niobate", "luxtelligence", "open-pdk"],
    }
    (OUT / "design.json").write_text(json.dumps(sheet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "limitations"}, indent=2))
    if failures:
        raise SystemExit("OPA-LAYOUT-005 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write-gds":
        chip()[0].write_gds(sys.argv[2], with_metadata=False)
    else:
        main()
