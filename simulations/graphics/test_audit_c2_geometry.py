import unittest
from fractions import Fraction as F
from audit_c2_geometry_v012 import vec, triangle, box, topology, closest

class GeometryTests(unittest.TestCase):
    def test_triangle(self):
        v=tuple(map(vec,[(0,0,1),(1,0,1),(0,1,1)]))
        for p in [(0,0,0),(.5,.5,0),(.25,.25,1)]:
            self.assertEqual(triangle(vec(p),vec((0,0,1)),v),(1,F(1-p[2])))
        self.assertEqual(triangle(vec((.75,.75,0)),vec((0,0,1)),v),(0,None))
        self.assertEqual(triangle(vec((.25,.25,2)),vec((0,0,1)),v),(0,None))
        self.assertEqual(triangle(vec((.25,.25,1)),vec((1,0,0)),v),(-1,None))
        self.assertEqual(triangle(vec((.25,.25,0)),vec((1,0,0)),v),(0,None))
        self.assertEqual(triangle(vec((0,0,0)),vec((0,0,1)),(v[0],v[0],v[1])),(0,None))
        self.assertEqual(triangle(vec((0,0,2)),vec((0,0,-1)),v[::-1]),(1,F(1)))
        self.assertEqual(closest([(1,F(1)),(1,F(1))],[1,0]),(0,F(1)))

    def test_box(self):
        lo,hi=vec((0,0,1)),vec((1,1,2))
        for o,d,want in [((0,0,0),(0,0,1),True),
                         ((1,1,2),(0,0,1),True),
                         ((2,0,0),(0,0,1),False),
                         ((0,0,3),(0,0,1),False),
                         ((2,0,3),(-1,0,-1),True)]:
            self.assertEqual(box(vec(o),vec(d),lo,hi),want)
        self.assertFalse(box(vec((1+2**-40,0,0)),vec((0,0,1)),lo,hi))

    def test_topology(self):
        s={"triangles":[[[0,0,1],[1,0,1],[0,1,1]]],
           "nodes":[{"lo":[0,0,1],"hi":[1,1,1],"children":[],"primitives":[0]}]}
        topology(s)
        s["nodes"][0]["hi"]=[.5,1,1]
        with self.assertRaises(ValueError):
            topology(s)

if __name__=="__main__":
    unittest.main()
