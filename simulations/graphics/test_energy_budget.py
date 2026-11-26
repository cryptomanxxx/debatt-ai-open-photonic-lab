import unittest
from energy_budget_v015 import budget,GRID

class EnergyTests(unittest.TestCase):
    def test_grid(self):
        self.assertEqual(len(GRID),72)
        self.assertEqual(len(set(GRID)),72)

    def test_units(self):
        b=budget(100,100,20,60,100,1,10,.01,1)
        self.assertAlmostEqual(b["static_service_pj"],600)
        self.assertAlmostEqual(b["remaining_pj"],6700)
        self.assertAlmostEqual(b["max_dynamic_side_pj"],7300/60)
        self.assertTrue(b["positive"])

    def test_no_optics(self):
        b=budget(21,21,0,0,10,1,1,.1,.1)
        self.assertIsNone(b["max_dynamic_side_pj"])
        self.assertEqual(b["static_service_pj"],0)
        self.assertEqual(b["remaining_pj"],189)

    def test_all_fallback(self):
        b=budget(100,100,100,600,1000,1,1,.01,1)
        self.assertFalse(b["positive"])
        self.assertLess(b["remaining_pj"],0)

    def test_utilization(self):
        a=budget(100,100,20,60,100,1,10,.01,1)
        b=budget(100,100,20,60,100,1,10,.01,.1)
        self.assertAlmostEqual(b["static_service_pj"],10*a["static_service_pj"])
        self.assertLess(b["remaining_pj"],a["remaining_pj"])

if __name__=="__main__":
    unittest.main()
