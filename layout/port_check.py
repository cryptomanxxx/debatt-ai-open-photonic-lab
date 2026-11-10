"""Optical connectivity check for gdsfactory/kfactory layouts.

SiEPIC-Tools builds its netlist from SiEPIC pins, which gdsfactory-generated
waveguides do not have, so its connectivity checks cover nothing on these
layouts (see tools/siepic_verify.py). This check works on the gdsfactory ports
instead. In every cell of the hierarchy, each optical port of each child
instance must

  - meet exactly one other instance port at the same position (in database
    units), pointing the opposite way and with the same width, or
  - meet no instance port and be exported by the cell (a cell port at the same
    position pointing the same way), so that the connection is made one level up.

Anything else is a problem: a dangling port (no partner, not exported), more
than one partner, or a partner with the wrong direction or width.
"""
import collections


def optical_port_check(top, port_types=("optical",)):
    """Return (number of instance ports checked, list of problems)."""
    problems, checked = [], 0
    cells = [top] + [top.kcl[ci] for ci in top.called_cells()]
    for cell in cells:
        inst_ports = collections.defaultdict(list)
        cell_ports = collections.defaultdict(list)
        for inst in cell.insts:
            for p in inst.ports:
                if p.port_type in port_types:
                    inst_ports[(p.x, p.y)].append((p.angle, p.width, f"{inst.cell.name}.{p.name}"))
        for p in cell.ports:
            if p.port_type in port_types:
                cell_ports[(p.x, p.y)].append((p.angle, p.width, f"{cell.name}<{p.name}>"))
        for pos, here in inst_ports.items():
            for angle, width, label in here:
                checked += 1
                partners = [q for q in here if q[2] != label]
                if len(partners) == 1:
                    o_angle, o_width, o_label = partners[0]
                    if o_angle != (angle + 2) % 4 or o_width != width:
                        problems.append(f"{cell.name}: {label} meets {o_label} with direction "
                                        f"{angle}/{o_angle} and width {width}/{o_width} (dbu)")
                elif not partners:
                    exported = [q for q in cell_ports.get(pos, []) if q[0] == angle and q[1] == width]
                    if len(exported) != 1:
                        problems.append(f"{cell.name}: {label} is not connected (no partner, "
                                        f"not exported)")
                else:
                    problems.append(f"{cell.name}: {label} meets {len(partners)} instance ports")
    return checked, problems
