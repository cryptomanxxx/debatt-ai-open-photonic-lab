import unittest
from audit_drift_v004 import metric, outcome, cost, frontier, flag


class AuditTests(unittest.TestCase):
    def test_metric(self):
        r=dict(samples="65536",symbol_errors="4",bit_errors="8",
               ser=str(4/65536),ber=str(8/(4*65536)),worst_state_ser=str(4/4096))
        self.assertTrue(metric(r))
        r["ber"]="0"
        with self.assertRaises(ValueError):
            metric(r)

    def test_outcomes(self):
        self.assertEqual([outcome(a,b) for a,b in [(True,True),(False,True),(True,False),(False,False)]],
                         ["both_pass","rescued","regressed","both_fail"])
        with self.assertRaises(ValueError):
            flag("unknown")

    def test_cost(self):
        self.assertEqual(cost(16,256,2)["extra_reads"],32768)
        self.assertEqual(cost(16,256,2)["conditional_dynamic_read_energy_ratio"],2)
        self.assertEqual(cost(0,256,10)["extra_reads"],0)
        self.assertEqual(cost(1,65536,1)["extra_reads"],8)

    def test_frontier(self):
        a=dict(corrected_pass=10,regressed=0,extra_reads=0)
        b=dict(corrected_pass=9,regressed=1,extra_reads=8)
        c=dict(corrected_pass=12,regressed=1,extra_reads=8)
        self.assertEqual(frontier([a,b,c]),[a,c])


if __name__=="__main__":
    unittest.main()
