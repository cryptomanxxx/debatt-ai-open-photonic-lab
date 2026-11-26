import unittest
import tempfile
from audit_c2_fp64_v013 import guard_sides, decisions, kernels, near
from audit_c2_geometry_v012 import vec

class AuditTests(unittest.TestCase):
    def test_guards(self):
        lo,hi=vec((0,0,1)),vec((1,1,2))
        cases=[((2,0,0),(0,0,1),(-1,0)),
               ((0,0,3),(0,0,1),(-1,0)),
               ((0,0,0),(0,0,1),(1,0)),
               ((0,0,0),(1,0,1),(0,2)),
               ((0,0,0),(1,1,1),(0,6)),
               ((1,1,3),(-1,-1,-1),(0,6))]
        for o,d,want in cases:
            self.assertEqual(guard_sides(vec(o),vec(d),lo,hi),want)

    def test_decisions(self):
        self.assertEqual(decisions("electronic_only",0,1,None,.2),(1,0,1))
        self.assertEqual(decisions("raw",-1,0,None,.2),(0,0,0))
        self.assertEqual(decisions("raw",0,1,-.2,.2),(0,0,0))
        self.assertEqual(decisions("max_min_125",0,1,-.2,.2),(0,1,1))
        self.assertEqual(decisions("max_min_125",0,1,-.21,.2),(0,0,0))
        self.assertEqual(decisions("all_optical_fallback",0,0,1.,.2),(1,1,0))
        with self.assertRaises(ValueError):
            decisions("raw",0,1,float("nan"),.2)

    def test_compiled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tri,box=kernels(tmp)
            o,d=vec((.5,.5,0)),vec((0,0,1))
            v=tuple(map(vec,[(0,0,1),(1,0,1),(0,1,1)]))
            self.assertEqual(tri(o,d,v),(1,1.))
            self.assertEqual(box(o,d,vec((0,0,1)),vec((1,1,1))),1)
            self.assertEqual(box(vec((2,0,0)),d,vec((0,0,1)),vec((1,1,1))),0)
        self.assertTrue(near(1.,1.))
        self.assertFalse(near(float("nan"),1.))

if __name__=="__main__":
    unittest.main()
