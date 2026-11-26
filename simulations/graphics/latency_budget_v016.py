"""C3B.2: conditional dependency-aware batch latency, not hardware timing."""
import argparse
import csv
import heapq
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from energy_budget_v015 import load, verified, require, write_csv, MATCHED
from audit_c2_geometry_v012 import vec, topology
from audit_c2_fp64_v013 import guard_sides

# Explicit hypothetical service times in ns; no inference from modulator bandwidth.
# One electronic sequencer, one memory port, L parallel complete side lanes.
PROFILES={
    "optimistic":dict(memory=1,pre=1,drive=.5,propagation=.5,read=.5,aggregate=1,
                      fallback=5,triangle=5,stack=1,dispatch=0,output=1),
    "moderate":dict(memory=5,pre=5,drive=2,propagation=1,read=2,aggregate=3,
                    fallback=15,triangle=15,stack=2,dispatch=50,output=3),
    "conservative":dict(memory=20,pre=15,drive=10,propagation=2,read=10,aggregate=10,
                        fallback=40,triangle=40,stack=5,dispatch=200,output=10),
}
LANES=(1,2,4,8,16)
CONTEXTS=(1,8,32)


def trace_panels(c2,rows):
    """Reconstruct per-ray ordered nodes from archived decisions, not optical rerun."""
    scenes=json.loads((c2/"workload.json").read_text())["scenes"]
    labels=json.loads((c2/"labels.json").read_text())
    eligible={(l["scene"],l["ray"]) for l in labels if not l["excluded"]}
    geom={}
    for s in scenes:
        tris,bounds=topology(s)
        for i,(o,d) in enumerate(s["rays"]):
            if (s["name"],i) in eligible:
                geom[s["name"],i]=(s["nodes"],[guard_sides(vec(o),vec(d),*b) for b in bounds])
    require(set(geom)==eligible,"eligible geometry coverage")
    def key(x):
        return x["scenario"],int(x["repeat"]),x["scene"],int(x["ray"]),x["policy"]
    out=defaultdict(list)
    totals=defaultdict(Counter)
    seen=set()
    with (c2/"node-results.csv").open(newline="") as f,(c2/"results.csv").open(newline="") as g:
        groups=iter(itertools.groupby(csv.DictReader(f),key=key))
        for row in csv.DictReader(g):
            k=key(row)
            group=next(groups,None)
            require(group is not None and group[0]==k,"node group identity")
            if k[-1] not in MATCHED:
                # Exhaust skipped group before reading the next.
                for _ in group[1]:
                    pass
                continue
            require(k not in seen and (k[2],k[3]) in eligible,"hybrid ray identity")
            seen.add(k)
            nodes,guards=geom[k[2],k[3]]
            stack=[0]
            trace=[]
            vis,acc,tests=[],[],[]
            c=Counter(rays=1)
            for x in group[1]:
                j=int(x["node"])
                require(stack and j==stack.pop(),"DFS order")
                g,ns=guards[j]
                fb=int(x["fallback"])
                decision=int(x["decision"])
                require(int(x["guard"])==g and fb in (0,1) and decision in (0,1)
                        and (not g or not fb),"guard/fallback")
                nt=0
                vis.append(j)
                if decision:
                    acc.append(j)
                    node=nodes[j]
                    stack.extend(reversed(node["children"]))
                    tests.extend(node["primitives"])
                    nt=len(node["primitives"])
                    c["leaves"]+=int(not node["children"])
                trace.append((ns,fb,nt))
                c.update(nodes=1,accepted=decision,triangles=nt,guards=int(g!=0),
                         optical=int(g==0),fallback=fb,sides=ns,driven_operands=4*ns)
            require(not stack and vis==json.loads(row["visited_ids"])
                    and acc==json.loads(row["accepted_ids"])
                    and tests==json.loads(row["tested_ids"]),"trace coverage")
            for field in ("nodes","accepted","leaves","triangles","guards","optical",
                          "fallback","sides","driven_operands"):
                require(c[field]==int(row[field]),"ray count "+field)
            panel=k[:3]+(k[-1],)
            out[panel].append((k[3],tuple(trace)))
            totals[panel].update(c)
        require(next(groups,None) is None,"extra node groups")
    expected={k for k in rows if k[-1] in MATCHED}
    require(set(out)==expected and len(seen)==249*50*2,"panel/ray coverage")
    for k,c in totals.items():
        require(all(c[x]==rows[k][x] for x in ("rays","nodes","accepted","leaves","triangles",
                    "guards","optical","fallback","sides","driven_operands")),"panel counts")
    return {k:[t for _,t in sorted(v)] for k,v in out.items()}


def schedule(traces,p,lanes,contexts):
    """Deterministic event scheduler with finite in-flight rays.

    Each ray follows archived DFS order. One memory port and one electronic
    sequencer serialize requests; optical lanes run complete drive/prop/read
    transactions without pipelining. A node waits for all its sides, aggregation
    and fallback before its triangles and subsequent node can execute.
    """
    require(lanes>=1 and contexts>=1 and traces,"scheduler inputs")
    require(all(t for t in traces),"empty ray trace")
    events=[]
    seq=0
    cpu_free=mem_free=p["dispatch"]
    optical=[p["dispatch"]]*lanes
    heapq.heapify(optical)
    busy=Counter()
    finishes=[]
    next_ray=0
    def push(t,r,i,stage):
        nonlocal seq
        seq+=1
        heapq.heappush(events,(t,seq,r,i,stage))
    def admit(t):
        nonlocal next_ray
        r=next_ray
        next_ray+=1
        push(t,r,0,0)
    for _ in range(min(contexts,len(traces))):
        admit(p["dispatch"])
    def cpu(t,d):
        nonlocal cpu_free
        if d==0:
            return t
        start=max(t,cpu_free)
        cpu_free=start+d
        busy["cpu"]+=d
        return cpu_free
    def mem(t,d):
        nonlocal mem_free
        if d==0:
            return t
        start=max(t,mem_free)
        mem_free=start+d
        busy["memory"]+=d
        return mem_free
    side_ns=p["drive"]+p["propagation"]+p["read"]
    while events:
        t,_,r,i,stage=heapq.heappop(events)
        ns,fb,nt=traces[r][i]
        if stage==0:
            # One stack pop / node access. Child push and traversal update
            # charged in the final electronic stage of every visited node.
            push(mem(t,p["memory"]),r,i,1)
        elif stage==1:
            push(cpu(t,p["pre"]),r,i,2)
        elif stage==2:
            end=t
            for _ in range(ns):
                free=heapq.heappop(optical)
                done=max(t,free)+side_ns
                heapq.heappush(optical,done)
                end=max(end,done)
                busy["side"]+=side_ns
            push(end,r,i,3)
        elif stage==3:
            push(cpu(t,(p["aggregate"] if ns else 0)+fb*p["fallback"]),r,i,4)
        elif stage==4:
            # Primitive accesses and triangle work charged even after fallback.
            push(mem(t,nt*p["memory"]),r,i,5)
        elif stage==5:
            end=cpu(t,nt*p["triangle"]+p["stack"])
            if i+1<len(traces[r]):
                push(end,r,i+1,0)
            else:
                push(cpu(end,p["output"]),r,i,6)
        else:
            finishes.append(t)
            if next_ray<len(traces):
                admit(t)
    require(len(finishes)==len(traces),"completion coverage")
    makespan=max(finishes)
    require(math.isfinite(makespan) and makespan>0,"invalid makespan")
    lower=p["dispatch"]+max(busy["cpu"],busy["memory"],busy["side"]/lanes)
    require(makespan+1e-8>=lower,"resource lower bound")
    return makespan,lower,busy


def run(c2,fp,cpu,energy,out):
    rows,byscene=load(c2,fp,cpu)
    er=verified(energy)
    require(er["passed"] and er["grid_rows"]==28800,"energy archive gate")
    traces=trace_panels(c2,rows)
    grid=[]
    totals=defaultdict(Counter)
    for k,raytraces in sorted(traces.items()):
        scenario,rep,scene,policy=k
        n=rows[k]["rays"]
        reference=byscene[scene]["p50_batch_ns"]
        for profile,p in PROFILES.items():
            for lanes,contexts in itertools.product(LANES,CONTEXTS):
                elapsed,lower,busy=schedule(raytraces,p,lanes,contexts)
                remaining=reference-elapsed
                grid.append(dict(scenario=scenario,repeat=rep,scene=scene,policy=policy,
                    profile=profile,lanes=lanes,contexts=contexts,rays=n,
                    modeled_batch_ns=elapsed,resource_lower_bound_ns=lower,
                    cpu_busy_ns=busy["cpu"],memory_busy_ns=busy["memory"],
                    side_lane_busy_ns=busy["side"],cpu_p50_batch_ns=reference,
                    remaining_overhead_ns=remaining,conditional_speed_ratio=reference/elapsed,
                    modeled_rays_per_s=n*1e9/elapsed,positive_budget=remaining>0))
                a=totals[scenario,policy,profile,lanes,contexts]
                a.update(panels=1,positive_panels=int(remaining>0),rays=n,
                         modeled_ns=elapsed,cpu_reference_ns=reference)
    summaries=[]
    for k,a in sorted(totals.items()):
        scenario,policy,profile,lanes,contexts=k
        summaries.append(dict(scenario=scenario,policy=policy,profile=profile,lanes=lanes,
            contexts=contexts,**a,remaining_overhead_ns=a["cpu_reference_ns"]-a["modeled_ns"],
            conditional_speed_ratio=a["cpu_reference_ns"]/a["modeled_ns"]))
    require(len(grid)==18000 and len(summaries)==450,"latency grid coverage")
    write_csv(out/"panel-latency.csv",grid)
    write_csv(out/"scenario-latency.csv",summaries)
    return dict(passed=True,stage="C3B.2 dependency-aware conditional latency",
                panels=len(traces),grid_rows=len(grid),scenario_rows=len(summaries),
                positive_panel_grid_rows=sum(x["positive_budget"] for x in grid),
                nonpositive_panel_grid_rows=sum(not x["positive_budget"] for x in grid),
                profiles_ns=PROFILES,lanes=list(LANES),contexts=list(CONTEXTS),
                reference="archived measured single-thread resident CPU p50 batch latency",
                model="one electronic sequencer, one memory port, parallel non-pipelined complete side lanes, finite ray contexts, archived per-ray DFS order",
                energy="not_measured",photonic_latency="not_measured",gpu="not_run",
                limitations=["All hybrid service times hypothetical, not derived from modulator bandwidth",
                    "Modeled batch times include assumed memory, electronic preprocessing, conversion, propagation, readout, aggregation, fallback, triangle and stack/output service",
                    "Unmodeled contention, interconnect, tuning, host transfer and system overhead must fit remaining budget",
                    "Dispatch sensitivity is illustrative; measured CPU reference excludes host dispatch and packing",
                    "Positive budget is conditional, not demonstrated speedup; no FPS or GPU claims",
                    "Raw optical policy excluded; frozen matched-quality decisions are not new physical measurements"])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("c2","fp64","cpu","energy"):
        p.add_argument(name,type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    try:
        report=run(a.c2,a.fp64,a.cpu,a.energy,a.output)
    except Exception as exc:
        report=dict(passed=False,error=str(exc),photonic_latency="not_measured")
    (a.output/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__=="__main__":
    raise SystemExit(main())
