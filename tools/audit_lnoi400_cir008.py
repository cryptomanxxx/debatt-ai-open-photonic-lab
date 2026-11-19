"""OPA-CIR-008: conditional system accounting on frozen CIR007 accuracy evidence."""
import hashlib
import io
import itertools
import json
import math
import os
from pathlib import Path
import runpy
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/opa-cir-008"
PARAMS=ROOT/"antigravity/reproduction/AG-PHOTONIC-003/original/params.py"
SHA="abc07f6aa4bc74b2dbb708a3cbeb29a23ee557bfd724259baa5eb45d0202e26c"
RUN=44523102737
ARTIFACT=14528427171
RATE=10e9 # conditional one vector per symbol, not demonstrated timing
N=4
COUNTS=dict(complex_macs_per_vector=16,dac_lanes=8,adc_lanes=8,
            input_driver_lanes=8,balanced_tia_pairs=8,photodiodes=16,
            optical_hybrids=4,mzi=12,mmi=24,phase_control_parameters=32,
            ideal_attenuators=4,carriers=1)
EXPECTED={(8,1.,1.),(8,1.,3.),(10,1.,1.),(10,1.,3.)}

def key(r):
    return (r["bits"],r["launch_max_mw"],r["lo_per_output_mw"])

def close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-15)

def main():
    raw=Path(os.environ["CIR007_ZIP"]).read_bytes()
    assert len(raw)==10718 and hashlib.sha256(raw).hexdigest()==SHA
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert sorted(z.namelist())==["installed-packages.json","result.json"]
        assert z.testzip() is None
        ref=json.loads(z.read("result.json"))
    assert ref["experiment"]=="OPA-CIR-007" and ref["channels"]==1 and ref["carrier_nm"]==1550
    assert ref["source_run"]==44517897095 and ref["source_artifact"]==14527555003
    assert ref["source_sha256"]=="0f35693c16434e42d16038aac5bd33fb8d832ba1c9d69b5d85d998a28bae8b05"
    assert not ref["failures"] and len(ref["checks"])==7 and all(ref["checks"].values())
    assert len(ref["cases"])==180 and len(ref["summaries"])==36
    groups={}
    for r in ref["cases"]:
        groups.setdefault(key(r),[]).append(r)
    assert len(groups)==36
    admitted=[]
    for r in ref["summaries"]:
        g=groups[key(r)]
        assert len(g)==5 and len({x["target"] for x in g})==5
        worst=max(x["total_relative_error"] for x in g)
        clip=max(x["adc_clip_fraction"] for x in g)
        assert close(worst,r["worst_error"]) and close(clip,r["worst_clip_fraction"])
        assert close(max(x["max_diode_mw"] for x in g),r["max_diode_mw"])
        passed=worst<=.05 and clip==0
        assert passed==r["provisional_screen_passed"]
        if passed: admitted.append(r)
    assert {key(r) for r in admitted}==EXPECTED and ref["passing_configurations"]==4
    src=runpy.run_path(str(PARAMS))
    op=src["OPTICAL_PARAMS"]; sy=src["SYSTEM_PARAMS"]
    # Historical AG003 proxy assumptions, NOT specifications for chosen parts.
    inputs={}
    names={"optical":("laser_wpe","coupler_il_db","mod_il_db","splitter_excess_db"),
           "electronic":("dac_pj_per_conv_8b","adc_pj_per_conv_8b","tia_mw_per_ch",
                         "mod_driver_pj_per_sym","sram_pj_per_byte","hbm_pj_per_byte",
                         "calib_mw_per_ring_or_mzi","pue_cooling_factor")}
    for domain,keys in names.items():
        table=op if domain=="optical" else sy
        for k in keys:
            p=table[k];inputs[k]=dict(nominal=p.val,low=p.low,high=p.high,unit=p.unit,provenance=p.provenance)
    def value(k,scenario):
        p=inputs[k]
        if scenario=="nominal":return p["nominal"]
        if k=="laser_wpe":return p["high" if scenario=="low" else "low"]
        return p[scenario]
    rows=[]
    for cfg,scenario,split,frontends,memory in itertools.product(admitted,("low","nominal","high"),
            ("adaptive_lower_bound","fixed_equal"),(8,16),("sram","hbm")):
        bits,launch,lo=key(cfg)
        v=lambda k:value(k,scenario)
        # Signal plane is already after encoder at the modeled core input.
        # Fixed 1:4 split must provision each branch for a full-scale vector
        # component (4x aggregate peak). Adaptive allocation is an optimistic
        # lower bound with no claimed implementation.
        allocation=1 if split=="adaptive_lower_bound" else N
        coupling=10**(v("coupler_il_db")/10)
        splitter=10**(2*v("splitter_excess_db")/10)
        mod=10**(v("mod_il_db")/10)
        signal_source_mw=launch*allocation*coupling*splitter*mod
        lo_source_mw=N*lo*coupling*splitter
        laser_w=(signal_source_mw+lo_source_mw)*1e-3/v("laser_wpe")
        # Explicit 2^(bits-8) scenario assumption for both converters;
        # no claim of available 10-bit/10-GS/s converter performance.
        bscale=2**(bits-8)
        p=dict(laser=laser_w,
               dac=COUNTS["dac_lanes"]*RATE*v("dac_pj_per_conv_8b")*bscale*1e-12,
               adc=COUNTS["adc_lanes"]*RATE*v("adc_pj_per_conv_8b")*bscale*1e-12,
               input_drivers=COUNTS["input_driver_lanes"]*RATE*v("mod_driver_pj_per_sym")*1e-12,
               tia=frontends*v("tia_mw_per_ch")*1e-3,
               calibration_proxy=COUNTS["mzi"]*v("calib_mw_per_ring_or_mzi")*1e-3,
               vector_memory=16*bits/8*RATE*v(memory+"_pj_per_byte")*1e-12)
        subtotal=sum(p.values())
        cooling=v("pue_cooling_factor")
        proxy=subtotal*cooling
        macrate=COUNTS["complex_macs_per_vector"]*RATE
        rows.append(dict(bits=bits,launch_max_mw=launch,lo_per_output_mw=lo,
            worst_relative_error=cfg["worst_error"],max_diode_mw=cfg["max_diode_mw"],
            scenario=scenario,signal_distribution=split,tia_frontends=frontends,memory=memory,
            signal_source_mw=signal_source_mw,lo_source_mw=lo_source_mw,
            optical_source_total_mw=signal_source_mw+lo_source_mw,
            optical_core_input_max_mw=launch,lo_at_hybrids_mw=N*lo,
            mean_detected_signal_mw_by_target={r["target"]:r["mean_detected_signal_mw"] for r in groups[key(cfg)]},
            vector_payload_bytes=16*bits/8,power_terms_w=p,partial_subtotal_w=subtotal,
            cooling_multiplier=cooling,partial_cooled_proxy_w=proxy,
            conditional_vectors_per_s=RATE,conditional_complex_macs_per_s=macrate,
            partial_energy_pj_per_vector=proxy/RATE*1e12,
            partial_energy_pj_per_complex_mac=proxy/macrate*1e12))
    nominal=[r for r in rows if r["scenario"]=="nominal" and r["signal_distribution"]=="fixed_equal"
             and r["tia_frontends"]==8 and r["memory"]=="sram"]
    baseline=next(r for r in nominal if key(r)==(8,1.,1.))
    # Counterfactual pair checks: same accuracy evidence, accounting changes only.
    index={(key(r),r["scenario"],r["signal_distribution"],r["tia_frontends"],r["memory"]):r for r in rows}
    checks=dict(frozen_accuracy_screen=len(admitted)==4,complete_grid=len(rows)==96 and len(index)==96,
        source_power_conservation=all(r["signal_source_mw"]>=r["optical_core_input_max_mw"] and
             r["lo_source_mw"]>=r["lo_at_hybrids_mw"] for r in rows),
        no_double_count_core_loss=all(close(r["optical_source_total_mw"],r["signal_source_mw"]+r["lo_source_mw"]) for r in rows),
        sum_and_units=all(close(r["partial_cooled_proxy_w"],sum(r["power_terms_w"].values())*r["cooling_multiplier"]) and
             close(r["partial_energy_pj_per_complex_mac"]*16,r["partial_energy_pj_per_vector"]) for r in rows),
        fixed_split_factor=all(close(r["signal_source_mw"],4*index[(key(r),r["scenario"],"adaptive_lower_bound",r["tia_frontends"],r["memory"])]["signal_source_mw"]) for r in rows if r["signal_distribution"]=="fixed_equal"),
        tia_pair_accounting=all(close(r["power_terms_w"]["tia"],2*index[(key(r),r["scenario"],r["signal_distribution"],8,r["memory"])]["power_terms_w"]["tia"]) for r in rows if r["tia_frontends"]==16),
        ordered_scenarios=all(index[(key(r),"low",r["signal_distribution"],r["tia_frontends"],r["memory"])]["partial_cooled_proxy_w"]<=r["partial_cooled_proxy_w"]<=index[(key(r),"high",r["signal_distribution"],r["tia_frontends"],r["memory"])]["partial_cooled_proxy_w"] for r in rows if r["scenario"]=="nominal"),
        single_carrier_only=COUNTS["carriers"]==1,
        finite_positive=all(math.isfinite(r["partial_cooled_proxy_w"]) and r["partial_cooled_proxy_w"]>0 for r in rows))
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-008",source_run=RUN,source_artifact=ARTIFACT,source_zip_sha256=SHA,
        parameter_file=str(PARAMS.relative_to(ROOT)),parameter_sha256=hashlib.sha256(PARAMS.read_bytes()).hexdigest(),
        architecture=COUNTS,carrier_nm=1550,conditional_symbol_rate_hz=RATE,
        checks=checks,failures=failures,scenario_count=len(rows),accuracy_eligible=len(admitted),
        assumed_parameters=inputs,nominal_baseline=baseline,nominal_alternatives=nominal,
        unknown_or_excluded=["Actual 32 phase-control bias/driver hold power and four attenuator controls",
          "Physical IQ encoder transfer, detector saturation, phase tracking, RIN and LO coherence/distribution details",
          "Unmodeled routing, output coupling and hybrid excess losses; additional loss invalidates frozen accuracy unless compensated",
          "Digital normalization, complex output gain, activation, weight programming, calibration probes, metadata, clocks and idle power",
          "Host, packaging, actual thermal solution and measured timing"],
        limitations=["Partial budget, not a full accelerator/card/host total or a rigorous lower bound on actual hardware.",
          "All electrical powers and external optical losses are historical conditional proxies, not device measurements.",
          "10 Gvector/s is a throughput assumption only; no measured bandwidth or latency.",
          "Complex MAC convention is 16 per vector; no real TOPS comparison or claim of matched AI accuracy.",
          "No WDM speedup, no optical gain, no new accuracy simulation; inherited screen applies only at frozen optical reference planes.",
          "Memory counts packed I/Q vector payload only; weight updates, metadata and activation omitted.",
          "Low/nominal/high are deterministic joint sensitivity scenarios, not confidence intervals."],cases=rows)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    (OUT/"cir007-source.zip").write_bytes(raw)
    print(json.dumps({k:v for k,v in report.items() if k not in ("cases","assumed_parameters","nominal_alternatives")},indent=2,allow_nan=False))
    if failures:raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
