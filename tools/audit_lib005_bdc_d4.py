"""OPA-LIB-005-D4: replay reviewed D3, classify each diagnostic, preserve quarantine."""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"components/comparison/lib005-bdc-d4-decision.json"
OUT=ROOT/"results/opa-lib-005-d4"

def ensure(flag,message):
    if not flag: raise ValueError(message)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def equivalent(a,b,path=""):
    if isinstance(a,bool) or isinstance(b,bool) or a is None or b is None:
        ensure(type(a) is type(b) and a==b,"type "+path)
    elif isinstance(a,(float,int)) and isinstance(b,(float,int)):
        ensure(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12),"number "+path)
    elif isinstance(a,dict) and isinstance(b,dict):
        ensure(a.keys()==b.keys(),"fields "+path)
        for k in a: equivalent(a[k],b[k],path+"/"+k)
    elif isinstance(a,list) and isinstance(b,list):
        ensure(len(a)==len(b),"length "+path)
        for i,(x,y) in enumerate(zip(a,b)): equivalent(x,y,path+"/"+str(i))
    else:
        ensure(type(a) is type(b) and a==b,"value "+path)

def main():
    m=json.loads(SPEC.read_text())
    ensure(m["experiment"]=="OPA-LIB-005-D4" and m["source_ci_run"]==44799618360 and m["source_pr"]==248,"source metadata")
    for path,pin in [(m["source_script"],m["source_script_git_blob_sha1"]),
                     (m["archived_d1_d2_provenance_path"],m["archived_d1_d2_provenance_git_blob_sha1"])]:
        ensure(git_blob((ROOT/path).read_bytes())==pin,"pinned immutable review source "+path)
    original_archive=json.loads((ROOT/m["archived_d1_d2_provenance_path"]).read_text())
    ensure(original_archive["classification"]=="quarantined_nonpassive" and original_archive["checks"]==16,"original D1/D2 archive")
    subprocess.run([sys.executable,str(ROOT/m["source_script"])],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    d3=json.loads((ROOT/"results/opa-lib-005-d3/result.json").read_text())
    ensure(d3["experiment"]=="OPA-LIB-005-D3" and all(d3["checks"].values()),"D3 execution")
    for key in ("coherent_multiport","variants","controls","status","checks"):
        equivalent(d3[key],m["expected_d3_observations"][key],key)
    p=d3["variants"]
    ensure(p["as_tabulated"]["violating_frequency_points"]==50,"original negative classification")
    ensure(p["reciprocity_symmetrized_counterfactual"]["violating_frequency_points"]==49,"reciprocity outcome")
    ensure(p["same_side_port_blocks_removed_counterfactual"]["violating_frequency_points"]==28,"same-side outcome")
    ensure(p["forward_2x2_submatrix_diagnostic"]["violating_frequency_points"]==9,"forward outcome")
    ensure(p["backward_2x2_submatrix_diagnostic"]["violating_frequency_points"]==28,"backward outcome")
    ensure(p["all_phases_zero_counterfactual"]["violating_frequency_points"]==51,"zero phase outcome")
    ensure(p["unitary_port_phase_control"]["violating_frequency_points"]==50 and d3["controls"]["port_phase_gauge_max_sigma_difference"]<1e-12,"gauge invariant")
    ensure(d3["coherent_multiport"]["violating_samples_despite_all_input_columns_at_most_one"]==50,"single-port insufficiency")
    ensure(len(m["decisions"])==8 and len(set(x["test"] for x in m["decisions"]))==8,"decision coverage")
    scope=m["scientific_scope"]
    ensure(all(scope[x] is False for x in ("root_cause_determined","measurement_independent","exact_gds_and_model_equivalence","source_port_normalization_verified","reference_planes_verified","physical_optical_amplification_claim")),"no unsupported claim")
    ensure(scope["model_status"]=="quarantined_nonpassive" and scope["counterfactuals_must_not_replace_source"] is True and scope["soi_tfln_processes_kept_separate"] is True,"remain quarantine")
    report={
        "experiment":m["experiment"],
        "original_source":{"ci_run":m["source_ci_run"],"head_sha":m["source_head_sha"],"source_artifact_sha256":m["source_artifact_sha256"],"original_pdk_blob":m["source_original_pdk_git_blob_sha1"]},
        "original_nonpassivity":{"samples":51,"violations":50,"max_singular_value":p["as_tabulated"]["max_sigma"],"max_coherent_output_power_ratio":d3["coherent_multiport"]["max_optimal_coherent_power_ratio"],"individual_input_power_max":d3["coherent_multiport"]["max_single_input_collected_power"]},
        "decisions":m["decisions"],
        "scientific_scope":scope,
        "next_actions":m["next_actions"],
        "checks":{"pinned_reviewer_code_and_archive":True,"exact_D3_summary_replayed":True,"all_variants_reconciled":True,"multiport_column_test_retained":True,"port_phase_invariance_retained":True,"negative_result_unchanged":True,"eight_decisions_covered":True,"no_uncorroborated_physical_claim":True}
    }
    ensure(all(report["checks"].values()),"full checks")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"decision.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))

if __name__=="__main__":main()
