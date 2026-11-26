import unittest
import numpy as np
from drift_compensation_v003 import samples, prepare, correction, score, paired_outcome


class DriftTests(unittest.TestCase):
    def test_exact_offset(self):
        stored=np.full((16,1),.5)
        z=np.zeros((16,8))
        ref_cal=np.full((16,8),.5)
        # 0.5 is not exactly representable; construct calibration via same ADC.
        from multilevel_cell_v001 import observe
        ref_cal,_=observe(stored,z,0,12)
        estimate,clip=correction(stored,ref_cal,z,np.zeros((16,1)),0,.04,0,12,4)
        self.assertAlmostEqual(estimate,.04,delta=1/4095)
        self.assertEqual(clip,0)

    def test_ideal(self):
        d=samples(11001)
        bounds,values,truth,drift,clip,stored,cal=prepare(0,0,0,8,d)
        estimate,_=correction(stored,cal,d[7],d[8],0,drift,0,8,16)
        self.assertEqual(estimate,0)
        self.assertEqual(score(values,truth,bounds,estimate)["ser"],0)

    def test_mismatch_and_pairing(self):
        stored=np.full((16,1),.5)
        z=np.zeros((16,8))
        from multilevel_cell_v001 import observe
        cal,_=observe(stored,z,0,12)
        estimate,_=correction(stored,cal,z,np.ones((16,1)),0,0,.02,12,4)
        self.assertAlmostEqual(estimate,.02,delta=1/4095)
        self.assertEqual([paired_outcome(a,b) for a,b in [(True,True),(False,True),(True,False),(False,False)]],
                         ["both_pass","rescued","regressed","both_fail"])

    def test_reproducibility(self):
        a,b=samples(11001),samples(11001)
        for x,y in zip(a,b):
            np.testing.assert_array_equal(x,y)


if __name__=="__main__":
    unittest.main()
