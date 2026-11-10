"""Shared helpers for Debatt-AI Open Photonic Lab Meep experiments.

Experiments up to OPA-FDTD-009 are kept self-contained as historical records.
New experiments import geometry and measurement helpers from this module so
that a fix or improvement is made in one place.
"""
import json
import math
from pathlib import Path
import resource

import meep as mp


def bend_centerline(radius, lead_end, segments=48):
    """Centerline of a 90-degree circular bend from -y to +x.

    The input lead runs along x=0 from y=-lead_end to y=-radius, the arc has
    its center at (radius, -radius), and the output lead runs along y=0 from
    x=radius to x=lead_end. Leads should extend through the PML.
    """
    points = [(0.0, -lead_end), (0.0, -radius)]
    for i in range(1, segments + 1):
        theta = math.pi - 0.5 * math.pi * i / segments
        points.append((radius + radius * math.cos(theta),
                       -radius + radius * math.sin(theta)))
    points.append((lead_end, 0.0))
    return points


def ribbon_polygon(centerline, width, z=0.0):
    """Constant-width polygon around a centerline, as Meep vertices at height z."""
    left, right = [], []
    for i, (x, y) in enumerate(centerline):
        ax, ay = centerline[max(0, i - 1)]
        bx, by = centerline[min(len(centerline) - 1, i + 1)]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        nx, ny = -dy / length, dx / length
        left.append(mp.Vector3(x + nx * width / 2, y + ny * width / 2, z))
        right.append(mp.Vector3(x - nx * width / 2, y - ny * width / 2, z))
    return left + right[::-1]


def modal_powers(sim, monitor, parity, band=1):
    """Forward and backward power in one eigenmode band at a flux monitor.

    Returns (forward, backward, n_eff) for the first monitor frequency.
    """
    result = sim.get_eigenmode_coefficients(monitor, [band], eig_parity=parity)
    coeff = result.alpha[0, 0]
    kdom = result.kdom[0]
    freq = mp.get_flux_freqs(monitor)[0]
    n_eff = float(abs(kdom.norm()) / freq) if freq else float("nan")
    return float(abs(coeff[0]) ** 2), float(abs(coeff[1]) ** 2), n_eff


def peak_rss_bytes():
    """Peak resident memory of this process (Linux reports KiB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def write_report(out_dir, report):
    """Write result.json and echo it to stdout for the CI log."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2) + "\n"
    (out / "result.json").write_text(text, encoding="utf-8")
    print(text)
