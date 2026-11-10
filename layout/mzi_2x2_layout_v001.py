"""OPA-LAYOUT-001: GDS layout of the programmable 2x2 MZI from OPA-MZI-001.

Builds the circuit that OPA-MZI-001 models, in gdsfactory's generic PDK:

    in_top --[phi heater]---\\                  /--[theta heater]--\\                  /--[a heater]-- out_top
                            coupler (50:50)                       coupler (50:50)
    in_bot --[dummy heater]-/                  \\--[dummy heater]--/                  \\--[b heater]-- out_bot

Every phase shifter has an identical unpowered heater on the other waveguide,
so both paths see the same heater loss. OPA-MZI-002 showed that unbalanced arm
loss is the one error that calibration cannot remove.

The script writes the GDS file, a PNG preview and a JSON report, and checks:
  1. four optical ports (two inputs west, two outputs east), all 0.5 um wide,
  2. the expected building blocks: 2 directional couplers and 6 identical heaters,
  3. equal optical path length through the two internal arms (a balanced MZI),
  4. equal path length from each input to the first coupler and from the
     second coupler to each output,
  5. the fan-out S-bends do not cross, and no two heater footprints overlap,
  6. the GDS file is byte-for-byte reproducible.

The generic PDK is gdsfactory's example technology, not a foundry process:
layer numbers, the coupler gap and the heater are placeholders until a real
PDK (for example an open silicon-photonics PDK) is chosen.
"""
import hashlib
import json
from pathlib import Path
import platform
import sys

import gdsfactory as gf

OUT = Path("results/opa-layout-001")
HEATER_LENGTH = 100.0      # um
COUPLER_GAP = 0.236        # um, generic-PDK default
COUPLER_LENGTH = 20.0      # um; the 50:50 length must come from simulation
FANOUT = (40.0, 28.0)      # (dx, dy) of the S-bends that separate the heaters
LENGTH_TOLERANCE = 1e-3    # um

gf.gpdk.PDK.activate()


def coupler():
    return gf.components.coupler(gap=COUPLER_GAP, length=COUPLER_LENGTH)


def core_mzi() -> gf.Component:
    """Balanced MZI: two directional couplers, a heater on each internal arm."""
    return gf.components.mzi2x2_2x2(
        delta_length=0, length_x=HEATER_LENGTH,
        splitter=coupler(), combiner=coupler(),
        straight_x_top="straight_heater_metal",
        straight_x_bot="straight_heater_metal",
    )


@gf.cell
def programmable_mzi_2x2() -> gf.Component:
    """MZI with phase shifters for phi (input), theta (internal) and a, b (outputs)."""
    c = gf.Component()
    core = c << core_mzi()
    core.name = "core_mzi"
    # Coupler and core port names: o2 = top-left, o1 = bottom-left,
    # o3 = top-right, o4 = bottom-right.
    sides = {
        "in_top": ("o2", +1, "phi"), "in_bot": ("o1", -1, "dummy_in"),
        "out_top": ("o3", +1, "a"), "out_bot": ("o4", -1, "b"),
    }
    for name, (core_port, sign, heater_name) in sides.items():
        # An input bend is connected by its o2 port, which turns it by 180 degrees
        # and flips its y offset; pre-flip it so the top input still ends up on top.
        dy = sign * FANOUT[1] if name.startswith("out") else -sign * FANOUT[1]
        bend = c << gf.components.bend_s(size=(FANOUT[0], dy))
        heater = c << gf.components.straight_heater_metal(length=HEATER_LENGTH)
        if name.startswith("in"):
            bend.connect("o2", core.ports[core_port])
            heater.connect("o2", bend.ports["o1"])
            c.add_port(name, port=heater.ports["o1"])
        else:
            bend.connect("o1", core.ports[core_port])
            heater.connect("o1", bend.ports["o2"])
            c.add_port(name, port=heater.ports["o2"])
        heater.name = f"heater_{heater_name}"
        bend.name = f"fanout_{name}"
        for port in heater.ports:
            if port.port_type == "electrical" and port.name in ("l_e2", "r_e2"):
                c.add_port(f"{heater_name}_{port.name}", port=port)
    for port in core.ports:
        if port.port_type == "electrical":
            c.add_port(f"core_{port.name}", port=port)
    return c


def instance_length(component):
    info = component.info
    for key in ("length", "path_length"):
        if key in info:
            return float(info[key])
    return None


def arm_lengths(core):
    """Optical path length of the top and bottom arms between the two couplers.

    Traces the netlist of the core MZI from each output port of the first
    coupler (cp1) to the second coupler (cp2), summing the length of every
    two-port instance on the way.
    """
    netlist = core.get_netlist()
    links = {}
    for net in netlist["nets"]:
        links[net["p1"]] = net["p2"]
        links[net["p2"]] = net["p1"]
    instances = {name: core.insts[name] for name in netlist["instances"]}
    lengths = {}
    for arm, start in (("top", "cp1,o3"), ("bottom", "cp1,o4")):
        total, here, path = 0.0, start, []
        while True:
            there = links[here]
            name, port = there.split(",")
            if name == "cp2":
                break
            inst = instances[name]
            total += instance_length(inst.cell)
            optical = [p.name for p in inst.ports if p.port_type == "optical"]
            other = [p for p in optical if p != port]
            path.append(name)
            here = f"{name},{other[0]}"
        lengths[arm] = {"length_um": total, "instances": path}
    return lengths


def overlapping_heaters(component):
    """Pairs of heater instances whose bounding boxes overlap."""
    boxes = []
    for inst in component.insts:
        if inst.name.startswith("heater_"):
            boxes.append((inst.name, inst.dbbox()))
    core = next(i for i in component.insts if i.name == "core_mzi")
    for inst in core_mzi().insts:
        if inst.cell.name.startswith("straight_heater"):
            box = inst.dbbox().transformed(core.dcplx_trans)
            boxes.append((f"core_{inst.name}", box))
    overlaps = []
    for i, (n1, b1) in enumerate(boxes):
        for n2, b2 in boxes[i + 1:]:
            if b1.overlaps(b2):
                overlaps.append([n1, n2])
    return overlaps, [name for name, _ in boxes]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = programmable_mzi_2x2()
    gds = OUT / "programmable_mzi_2x2.gds"
    c.write_gds(gds, with_metadata=False)
    sha = hashlib.sha256(gds.read_bytes()).hexdigest()

    checks, failures = {}, []

    def check(name, ok, detail):
        checks[name] = {"passed": bool(ok), "detail": detail}
        if not ok:
            failures.append(name)

    optical = [p for p in c.ports if p.port_type == "optical"]
    ports = {p.name: {"x_um": p.dcenter[0], "y_um": p.dcenter[1],
                      "orientation_deg": p.orientation, "width_um": p.dwidth}
             for p in optical}
    check("four_optical_ports",
          sorted(ports) == ["in_bot", "in_top", "out_bot", "out_top"]
          and all(ports[n]["orientation_deg"] == 180 for n in ("in_top", "in_bot"))
          and all(ports[n]["orientation_deg"] == 0 for n in ("out_top", "out_bot"))
          and all(abs(p["width_um"] - 0.5) < 1e-9 for p in ports.values()),
          "inputs face west, outputs face east, all 0.5 um wide")
    check("port_order_matches_model",
          ports["in_top"]["y_um"] > ports["in_bot"]["y_um"]
          and ports["out_top"]["y_um"] > ports["out_bot"]["y_um"],
          "in_top/out_top are waveguide 0 of the circuit model (phi and a act on it)")

    core = core_mzi()
    cells = [i.cell.name for i in core.insts] + [i.cell.name for i in c.insts]
    n_couplers = sum(name.startswith("coupler") for name in cells)
    n_heaters = sum(name.startswith("straight_heater") for name in cells)
    check("building_blocks", n_couplers == 2 and n_heaters == 6,
          f"2 directional couplers and 6 heaters (found {n_couplers} and {n_heaters})")
    heater_cells = {name for name in cells if name.startswith("straight_heater")}
    check("identical_heaters", len(heater_cells) == 1,
          "all six heaters are the same cell, so powered and dummy heaters add the same loss")

    arms = arm_lengths(core)
    delta = abs(arms["top"]["length_um"] - arms["bottom"]["length_um"])
    check("balanced_internal_arms", delta < LENGTH_TOLERANCE,
          f"top and bottom arms differ by {delta:.2e} um (tolerance {LENGTH_TOLERANCE} um)")

    io_lengths = {
        name: HEATER_LENGTH + float(inst.cell.info["length"])
        for name, inst in ((i.name.removeprefix("fanout_"), i) for i in c.insts)
        if inst.name.startswith("fanout_")
    }
    check("balanced_input_output_paths",
          abs(io_lengths["in_top"] - io_lengths["in_bot"]) < LENGTH_TOLERANCE
          and abs(io_lengths["out_top"] - io_lengths["out_bot"]) < LENGTH_TOLERANCE,
          "heater plus fan-out length is equal on both inputs and on both outputs")

    bends = [(i.name, i.dbbox()) for i in c.insts if i.name.startswith("fanout_")]
    bend_overlaps = [[n1, n2] for k, (n1, b1) in enumerate(bends)
                     for n2, b2 in bends[k + 1:] if b1.overlaps(b2)]
    check("fanouts_do_not_cross", not bend_overlaps and len(bends) == 4,
          f"the four fan-out S-bends do not overlap or cross (overlaps: {bend_overlaps})")

    overlaps, heater_names = overlapping_heaters(c)
    check("heaters_do_not_overlap", not overlaps and len(heater_names) == 6,
          f"no overlapping heater footprints among {len(heater_names)} heaters")

    png = OUT / "programmable_mzi_2x2.png"
    fig = c.plot()
    if fig is not None and hasattr(fig, "savefig"):
        fig.savefig(png, dpi=150, bbox_inches="tight")
    else:
        import matplotlib.pyplot as plt
        plt.gcf().savefig(png, dpi=150, bbox_inches="tight")
    footprint = [round(c.dxsize, 3), round(c.dysize, 3)]

    # Regenerate from scratch (cache cleared); c must not be used after this.
    regenerated = OUT / "programmable_mzi_2x2.check.gds"
    gf.clear_cache()
    programmable_mzi_2x2().write_gds(regenerated, with_metadata=False)
    same = hashlib.sha256(regenerated.read_bytes()).hexdigest() == sha
    regenerated.unlink()
    check("gds_reproducible", same, "regenerating the cell gives an identical GDS file")

    report = {
        "experiment": "OPA-LAYOUT-001",
        "goal": "GDS layout of the programmable 2x2 MZI modelled in OPA-MZI-001, with "
                "balanced dummy heaters following OPA-MZI-002",
        "pdk": "gdsfactory generic PDK (example technology, not a foundry process)",
        "gdsfactory_version": gf.__version__,
        "python_version": sys.version.split()[0],
        "platform": platform.machine(),
        "gds_file": gds.name,
        "gds_sha256": sha,
        "footprint_um": footprint,
        "parameters": {"heater_length_um": HEATER_LENGTH, "coupler_gap_um": COUPLER_GAP,
                       "coupler_length_um": COUPLER_LENGTH, "fanout_um": list(FANOUT)},
        "optical_ports": ports,
        "circuit_model_mapping": {
            "waveguide_0": "in_top / out_top", "waveguide_1": "in_bot / out_bot",
            "phi": "heater_phi on in_top", "theta": "top internal-arm heater of the core MZI",
            "a": "heater_a on out_top", "b": "heater_b on out_bot",
            "dummies": "heater_dummy_in and the bottom internal-arm heater are unpowered "
                       "and balance the heater loss",
        },
        "internal_arms": arms,
        "input_output_path_lengths_um": io_lengths,
        "checks": checks,
        "failures": failures,
        "limitations": [
            "Generic example PDK: layers, design rules and heater geometry are not a foundry's",
            "The coupler length is a placeholder; the 50:50 length for a real stack must "
            "come from simulation (next step: Meep or a mode solver)",
            "No foundry DRC deck has been run; checks are geometric sanity checks only",
            "No electrical routing to bond pads and no grating or edge couplers yet",
            "Heater phase per milliwatt and thermal crosstalk are not modelled",
        ],
    }
    (OUT / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit("OPA-LAYOUT-001 failed checks: " + ", ".join(failures))


if __name__ == "__main__":
    main()
