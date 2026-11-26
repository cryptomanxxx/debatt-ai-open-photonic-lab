import unittest
import numpy as np
from tail_calibration_v008 import tail_offsets, objective, choose, DEV, TEST, STEPS

class TailTests(unittest.TestCase):
    def test_causal(self):
        x=np.full((STEPS,16),.03)
        clip=np.zeros((STEPS,16,8),dtype=bool)
        a=tail_offsets(x,clip,4,4,(2.,.5,.95))
        self.assertAlmostEqual(a[0],.013)
        self.assertAlmostEqual(a[1],.013*.95)
        x[9:]=-.05
        b=tail_offsets(x,clip,4,4,(2.,.5,.95))
        np.testing.assert_array_equal(a[:12],b[:12])
        self.assertLess(b[12],0)
        clip[12,0,0]=True
        b=tail_offsets(x,clip,4,4,(2.,.5,.95))
        np.testing.assert_array_equal(b[12:16],np.zeros(4))
        np.testing.assert_array_equal(tail_offsets(x,clip,4,4,(0.,0.,0.)),np.zeros(STEPS))

    def test_objective(self):
        a=objective(dict(worst_state_ser=2/2048,symbol_errors=20),np.full(16,2),True)
        b=objective(dict(worst_state_ser=3/2048,symbol_errors=3),np.array([3]+[0]*15),True)
        self.assertEqual(choose({(1,1,1):a,(2,1,1):b}),(1,1,1))
        self.assertFalse(set(DEV)&set(TEST))
        self.assertFalse((set(DEV)|set(TEST))&set(range(21001,22017)))

if __name__=="__main__":
    unittest.main()
