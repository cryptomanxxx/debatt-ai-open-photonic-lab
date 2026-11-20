"""Audit process-separated passive test plans, not fabrication-ready GDS."""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"components/comparison/lib005-passive-test-plan.json"
OUT=ROOT/"results/opa-lib-005-b"
def req(t,s):
 if not t: raise ValueError(s)
def main():
 p=json.loads(FILE.read_text())
 d={}
 for name,e in p["source_pins"].items():
  b=(ROOT/e["path"]).read_bytes()
  req(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()==e["git_blob_sha1"],"pinned "+name)
  d[name]=json.loads(b)
 req(p["experiment"]=="OPA-LIB-005-B" and len(d["lib005"]["comparisons"])==10,"LIB005 handoff")
 req(len(p["structures"])==10 and len(p["platforms"])==2,"inventory")
 req({x["id"] for x in p["platforms"]}=={"soi","tfln"},"platform separation")
 soi={x["cell"] for x in d["soi"]["components"]}
 tfln={x["factory"] for x in d["tfln"]["components"]}
 req(len(soi)==3 and len(tfln)==7,"original inventory")
 req(d["si_layout"]["drc"]["total_violations"]==0,"SOI parent DRC only")
 req(d["tfln_layout"]["modulator"]["modulation_length"]==5000,"TFLN parent MZM identity only")
 req(all(x["measurement"] is None and x["qualification"] is None and x["drc"] is None for x in d["tfln"]["components"]),"TFLN unqualified")
 req(all(x["measurement"] is None and x["qualification"] is None for x in d["soi"]["components"]),"SOI unqualified")
 req(all(x["access"]=="unconfirmed" for x in p["platforms"]),"no facility selection")
 ids=set()
 for x in p["structures"]:
  req(x["id"] not in ids,"duplicate id");ids.add(x["id"])
  req(x["platform"] in {"soi","tfln"} and x["id"].startswith(x["platform"]+"-"),"platform id")
  req(x["source_revision"]==d[x["platform"]]["revision"],"revision")
  candidates=soi if x["platform"]=="soi" else tfln
  req(set(x["reuse"])<=candidates,"unavailable source cell")
  req(x["measurement_readiness"]=="planning_only" and x["fabrication_status"]=="not_fabricated" and x["calibration_status"]=="not_calibrated","no promotion")
  req(x["qualification"] is None and x["measurement_uncertainty"] is None and x["acceptance_thresholds"] is None and x["footprint_um"] is None,"unknown field preserved")
  req(x["process_access"]=="unconfirmed" and x["license_or_process_permission"]=="not_confirmed","no access claim")
  req(all(x[k] for k in ("hypothesis","readouts","controls","required_metadata","pitfalls","design_action")),"complete study plan")
 req(ids=={a+"-"+b for a in ("soi","tfln") for b in ("cutback","bends","coupler","mzi","io")},"10 distinct templates")
 s=p["separation"]
 req(s["cross_platform_calibration"] is False and s["quarantined_tfln_dc_allowed"] is False,"no cross calibration/quarantine")
 req(s["integrated_sources_required"] is False and s["integrated_detectors_required"] is False and s["external_instruments_allowed"] is True,"passive tests")
 req([v["id"] for v in p["decision_gates"]]==["P0","P1","P2","P3"] and all(v["state"]=="open" for v in p["decision_gates"]),"unpassed readiness gates")
 req(len(p["global_measurement_protocol"]["preconditions"])>=5 and len(p["global_measurement_protocol"]["data_export"])>=5,"measurement protocol")
 out={"experiment":p["experiment"],"status":"planning_only","platforms":list(sorted({x["platform"] for x in p["structures"]})),"structures":len(p["structures"]),"categories":["cutback","bends","coupler","mzi","io"],"reuse_count":sum(bool(x["reuse"]) for x in p["structures"]),"gates":{x["id"]:x["state"] for x in p["decision_gates"]},"fabrication_ready":False,"exact_cell_calibration_count":0,"checks":{"source_identity":True,"prior_evidence_handoff":True,"platform_separation":True,"reuse_identity":True,"measurement_protocol_completeness":True,"fabrication_and_calibration_separation":True,"quarantine_and_source_scope":True,"readiness_gates_open":True},"limitations":["No GDS generated or DRC executed for these proposed test structures.","No process access, cost, wafer allocation, design rule approval, or lab instrument booking confirmed.","Quantitative test targets and replication/sample sizes require a selected process and facility constraints.","Parent MZI layouts are not replacements for passive test cells.","Results are a research measurement plan, not predictions or physical results."]}
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"result.json").write_text(json.dumps(out,indent=2)+"\n")
 with (OUT/"test-matrix.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["id","platform","source_revision","source_cells","design_status","readouts","controls","missing_readiness"])
  for x in p["structures"]: w.writerow([x["id"],x["platform"],x["source_revision"],";".join(x["reuse"]),x["design_status"],";".join(x["readouts"]),";".join(x["controls"]),"process access; exact layout; quantitative acceptance thresholds; instrumentation and uncertainty"])
 print(json.dumps(out,indent=2))
if __name__=="__main__": main()
