import unittest
import numpy as np
from multilevel_cell_v001 import codebook, observe, thresholds, decode, metrics, draws, evaluate, WRITES, READS


class MemoryTests(unittest.TestCase):
    def test_codebook(self):
        for bits in (1,4):
            c=codebook(bits)
            self.assertEqual(len(c),2**bits)
            self.assertAlmostEqual(c[0],.2)
            self.assertAlmostEqual(c[-1],.8)
            np.testing.assert_array_equal(decode(c,thresholds(c)),np.arange(len(c)))

    def test_zero_margin(self):
        self.assertIsNone(thresholds([.2,.2]))
        self.assertIsNone(thresholds([.4,.2]))
        self.assertEqual(decode([.5],[.5])[0],1)

    def test_clipping(self):
        y,c=observe(np.array([-.1,.5,1.1]),0,0,8)
        np.testing.assert_array_equal(c,[True,False,True])
        self.assertEqual(y[0],0)
        self.assertEqual(y[-1],1)

    def test_bit_errors(self):
        c,m=metrics(np.arange(16),np.array([1,0]+list(range(2,16))),4)
        self.assertEqual(c.sum(),16)
        self.assertEqual(m["symbol_errors"],2)
        self.assertEqual(m["bit_errors"],2)
        self.assertEqual(m["ber"],2/64)

    def test_ideal_and_cluster_counts(self):
        for bits in (1,4):
            a,c,m=evaluate(bits,0,0,0,6,draws(bits,1027))
            self.assertTrue(a["calibration_valid"])
            self.assertEqual(m["ser"],0)
            self.assertEqual(m["writes"],2**bits*WRITES)
            self.assertEqual(m["samples"],2**bits*WRITES*READS)
            self.assertEqual(m["bad_writes"],0)
            self.assertGreater(m["zero_bad_write_upper95"],0)

    def test_shared_drift_and_reproducibility(self):
        randoms=draws(4,1027)
        a,c,m=evaluate(4,.01,.01,.02,8,randoms)
        b,d,n=evaluate(4,.01,.01,.02,8,draws(4,1027))
        self.assertEqual(a,b)
        self.assertEqual(m,n)
        np.testing.assert_array_equal(c,d)
        self.assertEqual(a["common_drift"],.02*randoms[-1])
        self.assertGreaterEqual(m["symbol_errors"],m["bad_writes"])
        self.assertLessEqual(m["symbol_errors"],m["bad_writes"]*READS)


if __name__=="__main__":
    unittest.main()
