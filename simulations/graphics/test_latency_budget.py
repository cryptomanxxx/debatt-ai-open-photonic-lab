import unittest
from latency_budget_v016 import schedule

P=dict(memory=1,pre=1,drive=1,propagation=1,read=1,aggregate=1,
       fallback=5,triangle=5,stack=1,dispatch=0,output=1)

class LatencyTests(unittest.TestCase):
    def test_serial_guard(self):
        t,lb,b=schedule([[(0,0,0)]],P,1,1)
        self.assertEqual(t,4)
        self.assertEqual(b["side"],0)
        self.assertLessEqual(lb,t)

    def test_parallel_sides(self):
        trace=[[(6,0,0)]]
        a,_,b=schedule(trace,P,1,1)
        c,_,d=schedule(trace,P,4,1)
        self.assertEqual(a-c,12)
        self.assertEqual(b["side"],18)
        self.assertEqual(b,d)

    def test_fallback_charged_after_optics(self):
        a,_,_=schedule([[(2,0,1)]],P,2,1)
        b,_,_=schedule([[(2,1,1)]],P,2,1)
        self.assertEqual(b-a,5)

    def test_serial_ray_dependency(self):
        a,_,_=schedule([[(2,1,1),(2,0,0)]],P,16,1)
        b,_,_=schedule([[(2,1,1)],[(2,0,0)]],P,16,1)
        self.assertEqual(b-a,1)

    def test_zero_work_bypasses_memory_queue(self):
        # Ray 0 needs no primitive fetch, while ray 1 occupies memory.
        # All zero-cost stages must advance without reserving or waiting
        # on a resource. Ray 0 finishes at 10 ns, ray 1 at 20 ns.
        p=dict(P,memory=10,pre=0,stack=0,output=0)
        t,lb,b=schedule([[(0,0,0)],[(0,0,0)]],p,1,1)
        self.assertEqual(t,20)
        self.assertEqual(lb,20)
        self.assertEqual(b["memory"],20)

    def test_zero_work_does_not_delay_other_context(self):
        # At t=1 the first ray has no aggregate/fallback or primitive
        # work. The second ray starts a long memory request at t=1.
        # The first context must become available immediately.
        p=dict(P,memory=1,pre=0,stack=0,output=0)
        traces=[[(0,0,0)],[(0,0,3)],[(0,0,0)]]
        t,lb,b=schedule(traces,p,1,2)
        self.assertEqual(t,20)
        self.assertEqual(b["memory"],6)
        self.assertEqual(b["cpu"],15)
        self.assertLessEqual(lb,t)

    def test_context_overlap(self):
        traces=[[(6,0,0)]]*8
        a,_,_=schedule(traces,P,8,1)
        b,lb,_=schedule(traces,P,8,8)
        self.assertLess(b,a)
        self.assertGreaterEqual(b,lb)

if __name__=="__main__":
    unittest.main()
