"""OPA-LIB-005-E: offline evidence-pinned LIB006 handoff and fail-closed safety gates."""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"components/comparison/lib005-final-evidence.json"
OUT=ROOT/"results/opa-lib-005-e"

def require(value,label):
    if not value: raise ValueError(label)

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def model_entry(models,key):
    return next(x for x in models if x["id"]==key)

def same_float(actual,expect):
    return math.isfinite(actual) and math.isclose(actual,expect,rel_tol=1e-12,abs_tol=1e-12)

def main():
    summary=json.loads(SPEC.read_text())
    require(summary["experiment"]=="OPA-LIB-005-E" and summary["stage"]=="evidence_summary_and_LIB006_handoff","summary identity")
    expected_keys={"comparability","passive_plan","discovery","soi_original_bdc","soi_negative_archive","soi_diagnostics","tfln_passivity","tfln_manifest"}
    pins=summary["source_pins"]
    require(set(pins)==expected_keys,"must pin all eight source artifacts")
    sources={}
    for key,p in pins.items():
        path=ROOT/p["path"]
        raw=path.read_bytes()
        require(git_blob(raw)==p["git_blob_sha1"],"pinned Git identity "+key)
        sources[key]=json.loads(raw)
    a,b,c=sources["comparability"],sources["passive_plan"],sources["discovery"]
    soi,arch,d4=sources["soi_original_bdc"],sources["soi_negative_archive"],sources["soi_diagnostics"]
    tfln,tfln_manifest=sources["tfln_passivity"],sources["tfln_manifest"]
    require(a["experiment"]=="OPA-LIB-005" and b["experiment"]=="OPA-LIB-005-B" and c["experiment"]=="OPA-LIB-005-C","phase identity")
    require(len(a["comparisons"])==10 and a["policy"]["exact_cell_promotions"]==0,"ten comparisons without calibration")
    require(len(b["structures"])==10 and len([x for x in b["structures"] if x["platform"]=="soi"])==5 and len([x for x in b["structures"] if x["platform"]=="tfln"])==5,"process-separated test structures")
    require(all(x["fabrication_status"]=="not_fabricated" and x["calibration_status"]=="not_calibrated" and x["qualification"] is None for x in b["structures"]),"no fabricated or qualified structures")
    require(all(x["process_access"]=="unconfirmed" for x in b["structures"]),"access unconfirmed")
    require(len(c["assessments"])==6 and c["policy"]["exact_cell_calibrations"]==0 and all(x["calibration_eligible"] is False for x in c["assessments"]),"no matching measured cell")
    require(soi["experiment"]=="OPA-LIB-005-D1" and arch["classification"]=="quarantined_nonpassive" and arch["checks"]==16,"permanent SOI negative evidence")
    require(d4["experiment"]=="OPA-LIB-005-D4" and d4["scientific_scope"]["model_status"]=="quarantined_nonpassive" and d4["scientific_scope"]["root_cause_determined"] is False,"D4 negative root-cause scope")
    require(tfln["experiment"]=="OPA-LIB-003" and tfln_manifest["experiment"]=="OPA-LIB-003","original TFLN source")
    require(tfln["revision"]==tfln_manifest["revision"] and len(tfln["components"])==2,"TFLN PDK identity")
    models=summary["models"]
    require(len(models)==4 and len({m["id"] for m in models})==4,"model universe")
    expected={"siepic-bdc-te1550","lnoi400-mmi2x2","lnoi400-directional-coupler","siepic-grating-te1550"}
    require({m["id"] for m in models}==expected,"model identity")
    bdc=model_entry(models,"siepic-bdc-te1550")
    sp=soi["passivity"]
    require(bdc["platform"]=="soi" and bdc["usage"]=="quarantined_nonpassive","SOI BDC retained quarantine")
    require(bdc["source_revision"]==soi["source"]["revision"]==c["upstream_revision"],"SOI model revision")
    require(bdc["samples"]==soi["samples"]==51 and bdc["nonpassive_samples"]==sp["nonpassive_frequencies"]==50,"SOI model violation count")
    require(same_float(bdc["max_sigma"],sp["max_sigma_global"]),"SOI singular value")
    tfln_by_id={x["component"]:x for x in tfln["components"]}
    for summary_id,pdk_id,status in [
        ("lnoi400-mmi2x2","mmi-2x2","conditional_numerical_only"),
        ("lnoi400-directional-coupler","directional-coupler","quarantined_nonpassive")
    ]:
        m=model_entry(models,summary_id);d=tfln_by_id[pdk_id]
        require(m["platform"]=="tfln" and m["source_revision"]==tfln["revision"],"TFLN revision "+summary_id)
        require(m["samples"]==d["samples"]==201 and m["nonpassive_samples"]==d["nonpassive_samples"],"TFLN sampled status "+summary_id)
        require(same_float(m["max_sigma"],d["max_sigma"]),"TFLN singular value "+summary_id)
        require(m["usage"]==d["usage"]==status,"TFLN model usage "+summary_id)
    gc=model_entry(models,"siepic-grating-te1550")
    gc_entry=next(x for x in c["assessments"] if x["id"]=="siepic-gc-te1550")
    require(gc["platform"]=="soi" and gc["source_revision"]==c["upstream_revision"] and gc["usage"]=="source_identified_not_passivity_screened","GC not promoted")
    require(gc["samples"] is None and gc["max_sigma"] is None and gc["nonpassive_samples"] is None and gc_entry["model_exact_gds_geometry_proven"] is False,"GC missing data stays missing")
    for m in models:
        require(m["exact_cell_raw_measurement"] is False and m["geometry_match_verified"] is False,"model calibration prohibited")
    coherent=summary["soi_coherence"]
    observed=d4["expected_d3_observations"]["coherent_multiport"]
    require(coherent["violations_with_individually_bounded_columns"]==observed["violating_samples_despite_all_input_columns_at_most_one"]==50,"coherent multiport proof")
    require(same_float(coherent["max_coherent_power_ratio"],observed["max_optimal_coherent_power_ratio"]) and same_float(coherent["max_single_port_power"],observed["max_single_input_collected_power"]),"coherent numerical values")
    require(coherent["source_phase_normalization_verified"] is False and coherent["physical_root_cause_identified"] is False and coherent["source_original_unchanged"] is True and coherent["unphysical_counterfactuals_qualified"] is False,"no invented cause")
    pol=summary["provenance_policy"]
    require(pol["distinct_platforms"]==["SiEPIC EBeam SOI","Luxtelligence lnoi400 TFLN"],"independent platform identity")
    for key in ("independent_matched_raw_measurements","exact_cell_calibrations","verified_fabricated_new_dies","foundry_drc_qualified_designs"):
        require(pol[key]==0,"no fictitious physical progress "+key)
    require(pol["physical_performance_claims"] is False and pol["local_original_gds_not_equivalent_to_measured_device"] is True and pol["never_substitute_adjacent_device_model"] is True,"no measurement promotion")
    p=summary["passive_test_plan"]
    require(p["structures"]==10 and p["soi"]==5 and p["tfln"]==5 and p["ready_to_manufacture"]==0 and p["status"]=="planning_only","all design gates open")
    require(p["design_gates"]==["P0 process access","P1 measurement plan freeze","P2 foundry layout review","P3 physical evidence"],"measurement gates order")
    handoff=summary["lib006_handoff"]
    expected_categorization={
        "conditional": {"lnoi400-mmi2x2"},
        "quarantined":{"siepic-bdc-te1550","lnoi400-directional-coupler"}
    }
    require(set(handoff["conditionally_use_model_for_numerical_sweep"])==expected_categorization["conditional"],"conditional model list")
    require(set(handoff["excluded_compact_models_for_passive_simulation"])==expected_categorization["quarantined"],"quarantined model list")
    require(handoff["soi_bdc_still_allowed_as_measurement_test_structure_not_certified_model"] is True,"experimental test distinction")
    require(handoff["platform_mixing_without_validated_heterogeneous_process"] is False and len(handoff["actions"])==5,"process decision gates")
    all_ids={x["id"] for x in b["structures"]}
    require(set(handoff["candidate_soi"]).issubset(all_ids) and set(handoff["candidate_tfln"]).issubset(all_ids),"only existing study categories")
    require(all(next(x for x in b["structures"] if x["id"]==key)["platform"]=="soi" for key in handoff["candidate_soi"]),"SOI handoff platform")
    require(all(next(x for x in b["structures"] if x["id"]==key)["platform"]=="tfln" for key in handoff["candidate_tfln"]),"TFLN handoff platform")
    checks={"all_eight_git_blob_source_pins":True,"ten_comparisons_zero_calibrations":True,"ten_not_fabricated_test_categories":True,"source_discovery_not_measurement":True,"SOI_full_complex_quarantine":True,"TFLN_two_distinct_model_screens":True,"coherent_numerical_result_not_physical_gain":True,"GC_no_unsupported_passivity":True,"model_qualification_fail_closed":True,"LIB006_process_and_foundry_gates_open":True}
    output={"experiment":"OPA-LIB-005-E","checks":checks,"source_refs":pins,"models":models,"passive_test_plan":p,"provenance_policy":pol,"lib006_handoff":handoff,"limitations":summary["limitations"]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"experiment":output["experiment"],"checks":checks,"models":[{"id":m["id"],"usage":m["usage"]} for m in models],"ready_to_manufacture":0,"exact_cell_calibrations":0},indent=2))

if __name__=="__main__":
    main()
