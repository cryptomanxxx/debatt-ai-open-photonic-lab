"""Tests that layout/port_check.py finds broken optical connections (ubcpdk env).

    python layout/test_port_check.py
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mzi_2x2_ubc_v002  # noqa: E402,F401  (sets the lab username, activates the PDK)
import gdsfactory as gf  # noqa: E402
from port_check import optical_port_check  # noqa: E402

XS = "strip"


def chain(name, gap_nm=0, width2=None, drop_middle=False):
    """Three straights in a row, exported at both ends; optionally broken."""
    c = gf.Component(name)
    a = c << gf.components.straight(length=10, cross_section=XS)
    b = c << gf.components.straight(length=10, cross_section=XS,
                                    width=width2) if width2 else \
        c << gf.components.straight(length=10, cross_section=XS)
    d = c << gf.components.straight(length=10, cross_section=XS)
    b.connect("o1", a.ports["o2"], allow_width_mismatch=True)
    d.connect("o1", b.ports["o2"], allow_width_mismatch=True)
    if gap_nm:
        d.dmovex(gap_nm / 1000)
    if drop_middle:
        del c.insts[b]
    c.add_port("o1", port=a.ports["o1"])
    c.add_port("o2", port=d.ports["o2"])
    return c


class PortCheckTest(unittest.TestCase):
    def test_connected_chain(self):
        checked, problems = optical_port_check(chain("pc_ok"))
        self.assertEqual(checked, 6)
        self.assertEqual(problems, [])

    def test_gap_of_one_nanometre(self):
        _, problems = optical_port_check(chain("pc_gap", gap_nm=1))
        self.assertTrue(any("not connected" in p for p in problems), problems)

    def test_width_mismatch(self):
        _, problems = optical_port_check(chain("pc_width", width2=0.45))
        self.assertTrue(any("width" in p for p in problems), problems)

    def test_missing_waveguide(self):
        _, problems = optical_port_check(chain("pc_missing", drop_middle=True))
        self.assertTrue(any("not connected" in p for p in problems), problems)

    def test_unexported_end(self):
        c = gf.Component("pc_unexported")
        c << gf.components.straight(length=10, cross_section=XS)
        _, problems = optical_port_check(c)
        self.assertEqual(len(problems), 2, problems)


if __name__ == "__main__":
    unittest.main()
