import unittest
import numpy as np
from state_replay_v007 import score, state_stats, verify_source
from adaptive_calibration_v005 import trajectory, STEPS

class ReplayTests(unittest.TestCase):
    def test_source(self):
        verify_source()

    def test_ideal(self):
        b,d,*_=trajectory(22001,0,0,0,0,0,8)
        m,c,s,f=score(b,d,np.zeros(STEPS))
        self.assertEqual(m["symbol_errors"],0)
        self.assertEqual(int(c.sum()),0)
        self.assertEqual(int(s.sum()),0)
        self.assertEqual(int(f.sum()),32768)

    def test_ties_and_regressions(self):
        b=np.zeros(16,dtype=int);b[0]=3
        c=np.zeros(16,dtype=int);c[1:3]=4
        fail,new,rescued,worst=state_stats(c,b)
        self.assertEqual(np.flatnonzero(fail).tolist(),[1,2])
        self.assertEqual(np.flatnonzero(new).tolist(),[1,2])
        self.assertEqual(np.flatnonzero(rescued).tolist(),[0])
        self.assertEqual(np.flatnonzero(worst).tolist(),[1,2])

if __name__=="__main__":
    unittest.main()
