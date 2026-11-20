"""Formal LIB005-D2 conservative gate: replay pinned D1 without editing upstream model."""
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"components/comparison/lib005-bdc-decision.json"
OUT=ROOT/"results/opa-lib-005-d2"

def require(test, msg):
    if not test:
        raise ValueError(msg)

def compare(a,b,path=""):
    if type(a) is bool or type(b) is bool or a is None or b is None:
        require(type(a) is type(b) and a==b,"type/value "+path)
    elif isinstance(a,(int,float)) and isinstance(b,(int,float)):
        require(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10),"numeric "+path)
    elif isinstance(a,dict) and isinstance(b,dict):
        require(a.keys()==b.keys(),"keys "+path)
        for k in a:compare(a[k],b[k],path+"/"+k)
    elif isinstance(a,list) and isinstance(b,list):
        require(len(a)==len(b),"list length "+path)
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+"/"+str(i))
    else:
        require(type(a) is type(b) and a==b,"type/value "+path)

def main():
    m=json.loads(SPEC.read_text())
    require(m["experiment"]=="OPA-LIB-005-D2" and m["original_pr"]==244,"report identity")
    require(m["original_run"]==44792693356 and m["original_artifact_id"]==14656862431,"CI source reference")
    require(m["original_artifact_sha256"]=="76892cda933dd3831c809aa14adb622b7fe19ae95fa5131a9fa250e6ced6cb0f","original artifact digest")
    subprocess.run([sys.executable,str(ROOT/"tools/audit_lib005_bdc.py")],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    result=json.loads((ROOT/"results/opa-lib-005-d1/result.json").read_text())
    compare(result,m["original_report"])
    require(all(result["checks"].values()) and len(result["checks"])==8,"8 successful analysis checks")
    p=result["passivity"]
    require(p["nonpassive_frequencies"]==50 and result["samples"]==51 and result["complex_values"]==816,"full sample status")
    require(not p["all_samples_pass_conditional_screen"] and p["conditional_numerical_usage"]=="quarantined_nonpassive","quarantine from full SVD")
    require(p["max_sigma_global"]>1+1e-9,"violating S norm")
    require(result["scope"]["calibration_eligible"] is False and result["scope"]["measured_complex_s"] is False,"not measured/calibrated")
    decision=m["decision"]
    require(decision["status"]=="quarantined_nonpassive" and decision["usable_for_passive_circuit"] is False,"fail closed")
    require(decision["source_revision"]==result["source"]["revision"] and decision["model_file_hash"]==result["source"]["git_blob_sha1"],"pinned original model")
    require(decision["independent_corrected_model_available"] is False and decision["exact_geometry_calibrated"] is False,"cannot rehabilitate")
    # Independent column-norm check cannot replace full SVD and must not be substituted for it.
    require(result["center"]["input1_collected_power"]<1 and result["center"]["sigma_max"]>1,"coherent multiple-port counterexample")
    out={"experiment":"OPA-LIB-005-D2","source_pr":244,"original_ci_run":m["original_run"],"source_artifact_id":m["original_artifact_id"],"passivity":p,
         "center":{"wavelength_nm":result["center"]["wavelength_nm"],"input1_collected_power":result["center"]["input1_collected_power"],"sigma_max":result["center"]["sigma_max"]},
         "decision":decision,"checks":{"source_run_pinned":True,"full_report_replayed":True,"eight_d1_checks":True,"negative_passivity_retained":True,"source_model_identity":True,"no_data_promotion":True,"multiport_counterexample":True,"future_gate_fail_closed":True},
         "limitations":["CI green verifies the correct calculation and conservatively stated negative classification, not component passivity.","No experiment shows optical amplification or a measured loss at this PDK cell.","No normalization or renormalization of the source model was performed.","This gate does not infer all five other untested PDK models' suitability.","Original D1 ZIP remains a temporary GitHub Actions artifact until separately archived."]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"decision.json").write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print(json.dumps(out,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
