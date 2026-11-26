import itertools
import unittest
from audit_adaptive_v006 import check_rates, selected_gates, compare, REFS, CADENCES, GATES, N


class AuditTests(unittest.TestCase):
    def test_rates(self):
        self.assertTrue(check_rates(2/N,2/(4*N),2/2048))
        self.assertFalse(check_rates(3/N,3/(4*N),3/2048))
        with self.assertRaises(ValueError):
            check_rates(.1,0,.2)
        with self.assertRaises(ValueError):
            check_rates(0,0,float("nan"))

    def test_gate_tie(self):
        rows=[dict(references=n,cadence=c,gate=g,symbol_errors=100,
                   selected=str(g==3)) for n,c,g in itertools.product(REFS,CADENCES,GATES)]
        self.assertEqual(set(selected_gates(rows).values()),{3.})
        rows[0]["selected"]="True"
        with self.assertRaises(ValueError):
            selected_gates(rows)

    def test_tail_tradeoff(self):
        a=dict(ser=4/N,worst=2/2048,passed=True,extra=32)
        b=dict(ser=3/N,worst=3/2048,passed=False,extra=32)
        x=compare([(a,b)])
        self.assertEqual(x["adaptive_lower_ser_lost_pass"],1)
        self.assertEqual(x["adaptive_lower_ser_higher_worst"],1)
        self.assertEqual(x["always_only_pass"],1)
        self.assertEqual(x["adaptive_only_pass"],0)


if __name__=="__main__":
    unittest.main()
