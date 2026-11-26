import unittest
import numpy as np
from adaptive_calibration_v005 import trajectory, corrections, evaluate, DEV, TEST, STEPS


class AdaptiveTests(unittest.TestCase):
    def test_seed_split(self):
        self.assertFalse(set(DEV)&set(TEST))

    def test_ideal(self):
        bounds,data,changes,clip,common,_=trajectory(TEST[0],0,0,0,0,0,8)
        off,on=corrections(changes,clip,4,4,2)
        self.assertFalse(on.any())
        self.assertEqual(evaluate(bounds,data,off)["ser"],0)

    def test_causal(self):
        changes=np.full((STEPS,16),.03)
        clip=np.zeros((STEPS,16,8),dtype=bool)
        off,on=corrections(changes,clip,4,4,2)
        changes[9:]=-.05
        newer,_=corrections(changes,clip,4,4,2)
        np.testing.assert_array_equal(off[:12],newer[:12])
        self.assertAlmostEqual(newer[12],-.05)
        self.assertTrue(on.all())

    def test_clipped_and_disagreement(self):
        changes=np.zeros((STEPS,16))
        changes[:,0]=.08
        clip=np.zeros((STEPS,16,8),dtype=bool)
        fixed,_=corrections(changes,clip,4,1,None)
        gated,_=corrections(changes,clip,4,1,2)
        self.assertAlmostEqual(fixed[0],.02)
        self.assertEqual(gated[0],0)
        clip[0,0,0]=True
        fixed,_=corrections(changes,clip,4,4,None)
        np.testing.assert_array_equal(fixed[:4],np.zeros(4))


if __name__=="__main__":
    unittest.main()
