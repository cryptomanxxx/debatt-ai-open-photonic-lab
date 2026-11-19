"""OPA-LIB-005: evidence comparability audit, not hardware validation."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/opa-lib-005"
SPEC=ROOT/"components/comparison/lib005-spec.json"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def load(spec):
    result={}
    for k,s in spec["sources"].items():
        b=(ROOT/s["path"]).read_bytes()
        require(hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()==s["git_blob_sha1"],"source identity "+k)
        result[k]=json.loads(b)
    return result
def main():
    spec=json.loads(SPEC.read_text())
    d=load(spec)
    si,ln,sm,s=d["si_geometry"],d["ln_geometry"],d["s_manifest"],d["s_report"]
    require(len(si["components"])==3 and len(ln["components"])==7,"geometry inventory")
    require(all(x["measurement"] is None and x["qualification"] is None for x in si["components"]+ln["components"]+sm["components"]+d["registry"]["components"]),"no exact cell promotion")
    require(ln["revision"]==sm["revision"]==s["revision"]==d["cir"]["pdk_commit"],"TFLN revision linkage")
    require(si["revision"]==d["pcm"]["revision"],"SOI source revision linkage only")
    require(all(x["drc"] is None for x in ln["components"]),"no TFLN DRC promotion")
    mmi,dc=s["components"]
    require(mmi["component"]=="mmi-2x2" and dc["component"]=="directional-coupler","model identities")
    require(mmi["passivity_screen_eligible"] is True and mmi["nonpassive_samples"]==0 and mmi["max_sigma"]<1,"MMI numerical gate")
    require(dc["passivity_screen_eligible"] is False and dc["nonpassive_samples"]==201 and dc["usage"]=="quarantined_nonpassive" and dc["min_sigma"]>1,"DC quarantine")
    require(d["cir"]["source_mmi_sha256"]==mmi["source_sha256"],"CIR MMI source linkage")
    require(all(all(v is True for v in d[k]["checks"].values()) for k in ("mod","ring","cascade")),"TFLN original checks")
    require(sum(len(d[k]["checks"]) for k in ("mod","ring","cascade"))==19,"19 TFLN checks")
    require(all(d[k]["complex_s"] is None and d[k]["geometry_match"] is None and d[k]["qualification"] is None for k in ("mod","ring","cascade")),"TFLN measurement limitations")
    require(d["pcm"]["complex_s"] is None and d["pcm"]["phase"] is None and d["pcm"]["qualification"] is None,"SOI measurement limitations")
    require(d["mod"]["independently_extracted_vpi_v"] is None and d["mod"]["delivered_rf_peak_voltage_v"] is None,"no independent RF voltage")
    require(d["ring"]["isolated_ring_fsr_ghz"] is None and d["ring"]["calibrated_loaded_q"] is None,"no isolated ring promotion")
    eo=next(x for x in d["eo"]["gap_sweep"]["rows"] if x["gap_um"]==4)
    vpi_l=d["cir"]["nominal_push_pull_vpi_v"]*d["cir"]["modulation_length_um"]/10000
    lit=d["mod"]["literature"]
    rf_vpi_l=lit["vpi_rf_v"]*lit["electrode_length_cm"]
    require(math.isclose(vpi_l,d["layout"]["vpi"]["pdk_vpi_L_push_pull_V_cm"],abs_tol=1e-12),"Vpi length conversion")
    require(abs(eo["vpi_L_push_pull_V_cm"]-d["layout"]["vpi"]["opa_eo_002_vpi_L_push_pull_V_cm_at_4um_gap"])<.001,"rounded layout reference")
    gc=next(x for x in d["registry"]["experimental_evidence"] if x["id"]=="siepic-gc-te1550")
    require(gc["exact_pdk_revision_verified"] is False and gc["raw_complex_s_available"] is False and "4.1 dB" in gc["finding"],"GC family scope")
    require(any("generic placeholder (6 dB, 35 nm)" in x for x in d["si_layout"]["limitations"]),"GC placeholder identity")
    require(d["si_layout"]["drc"]["total_violations"]==0,"parent DRC context")
    cut=d["pcm"]["center_raw_fit"]
    rings=d["ring"]["resonance_candidates"]
    require(len(rings)==4 and d["cascade"]["minima_count"]==40,"ring and cascade counts")
    metrics={
      "eo-vpi-length":{"model_generic_v_cm":eo["vpi_L_push_pull_V_cm"],"model_lnoi400_v_cm":vpi_l,"reported_twente_rf_v_cm":rf_vpi_l,"reported_rf_ghz":lit["rf_ghz"],"arithmetic_difference_v_cm":rf_vpi_l-vpi_l,"difference_is_model_error":False},
      "soi-grating":{"placeholder_loss_db":6,"reported_family_loss_db":4.1,"arithmetic_difference_db":1.9,"placeholder_bandwidth_nm":35,"reported_family_1db_bandwidth_nm":30.6,"bandwidth_difference_nm":None},
      "soi-cutback":{"effective_loss_db_per_cm":cut["loss_db_per_cm"],"conditional_ols_95ci":cut["conditional_ols_95ci_loss_db_per_cm"],"wavelength_nm":d["pcm"]["center_wavelength_nm"],"matched_model":None},
      "tfln-ring":{"apparent_spacing_ghz":d["ring"]["median_spacing_ghz"],"literature_fsr_ghz":d["ring"]["literature_fsr_ghz"],"apparent_q_range":[min(r["apparent_q"] for r in rings),max(r["apparent_q"] for r in rings)],"matched_model":None},
      "tfln-mmi":{"max_sigma":mmi["max_sigma"],"nonpassive_samples":mmi["nonpassive_samples"],"center_bar_power":mmi["center"]["bar_power"],"center_cross_power":mmi["center"]["cross_power"]},
      "tfln-dc":{"max_sigma":dc["max_sigma"],"nonpassive_samples":dc["nonpassive_samples"],"center_bar_power":dc["center"]["bar_power"],"center_cross_power":dc["center"]["cross_power"]},
      "soi-bdc":{"matched_model":None,"family_doi":next(x["doi"] for x in d["registry"]["experimental_evidence"] if x["id"]=="siepic-bdc-te1550")},
      "generic-coupler":{"nominal_cross_fraction_1550":d["coupler"]["nominal_cross_fraction_1550"],"matched_measurement":None},
      "tfln-cascade":{"minima_counts":[r["minima_count"] for r in d["cascade"]["scans"]],"matched_model":None},
      "tfln-mzm":{"central_power_range":d["cir"]["central_in1_out1_power_range"],"nominal_vpi_v":d["cir"]["nominal_push_pull_vpi_v"],"matched_measurement":None}}
    rows=[]
    for p in spec["comparisons"]:
        require(p["id"] in metrics and len(p["missing"])>0,"comparison completeness")
        require(p["status"] in {"context_only","measurement_reference_only","conditional_numerical_only","quarantined_nonpassive","published_family_only","numerical_only"},"no calibration status")
        rows.append(dict(**p,metrics=metrics[p["id"]],calibration_eligible=False))
    require(len(rows)==len(metrics)==10 and len({r["id"] for r in rows})==10,"ten unique comparison records")
    require(next(r for r in rows if r["id"]=="tfln-dc")["status"]=="quarantined_nonpassive","quarantine maintained")
    report=dict(experiment=spec["experiment"],source_commit=spec["source_commit"],sources=spec["sources"],comparisons=rows,
                exact_cell_calibration_count=0,comparison_count=10,geometry_count=10,policy=spec["policy"],
                checks=dict(source_identity=True,geometry_inventory=True,revision_linkage=True,no_exact_cell_promotion=True,passivity_and_quarantine=True,original_measurement_scope=True,unit_conversion=True,comparison_completeness=True),
                conclusion="Context and conditional numerical comparisons only. No matched simulation-to-measurement error established; no new hardware results. Prepare process-specific measurement requirements before LIB006 selection.")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (OUT/"comparison-matrix.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["id","status","calibration_eligible","missing","metrics_json"])
        for r in rows:w.writerow([r["id"],r["status"],r["calibration_eligible"],"; ".join(r["missing"]),json.dumps(r["metrics"],sort_keys=True)])
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__": main()
