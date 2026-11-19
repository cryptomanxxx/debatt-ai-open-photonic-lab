"""Offline CIR final report evidence audit; no scientific reruns."""
import hashlib
import json
import math
from pathlib import Path
import tempfile
from archive_cir import audit, require, ROOT, SPEC

ARCHIVE=ROOT/"research/evidence/opa-cir"
def close(a,b):
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-14)

def main():
    manifest=json.loads(SPEC.read_text())
    require(len(manifest)==8 and [m["experiment"] for m in manifest]==[f"OPA-CIR-{i:03d}" for i in range(1,9)],"manifest sequence")
    with tempfile.TemporaryDirectory() as d:
        source=Path(d)
        for m in manifest:
            n=m["name"]
            (source/(n+".zip")).write_bytes((ARCHIVE/n/"original.zip").read_bytes())
        expected=audit(source)
    actual={p.relative_to(ARCHIVE).as_posix() for p in ARCHIVE.rglob("*") if p.is_file()}
    require(actual==set(expected),"archive members")
    require(len(expected)==41 and sum(map(len,expected.values()))==3222234,"archive counts")
    for name,b in expected.items():
        require((ARCHIVE/name).read_bytes()==b,"archive bytes "+name)
    r=[json.loads(expected[m["name"]+"/files/result.json"]) for m in manifest]
    require(sum(len(x["checks"]) for x in r)==63 and all(all(x["checks"].values()) for x in r),"63 checks")
    a,b,c,d,e,f,g,h=r
    require(close(a["errors"]["programmed_targets"],1.2123818431320796e-15),"CIR001 headline")
    require(b["samples"]==63 and close(b["metrics"]["sax_network_error"],3.4989384658674724e-14),"CIR002 headline")
    require(c["cases"]==330 and close(c["metrics"]["sax_error"],1.608206982491765e-11),"CIR003 headline")
    for obj,k,v in [(d,"median_naive_shape_error",.8755775537326204),(d,"median_calibrated_shape_error",.02405753448557389),(d,"median_transmission",.7340495495954931),(e,"median_naive_shape_error",.7787228642179679),(e,"median_calibrated_shape_error",.027171304983280103),(e,"max_calibrated_shape_error",.03991538251055307),(e,"median_heldout_mvm_error",.028806195471855384),(e,"median_nonzero_transmission",.1940492784992479)]:
        require(close(obj[k],v),k)
    # Rebuild every WDM worst-case window from full raw rows.
    require(len(f["rows"])==255 and len(f["windows"])==15,"WDM rows")
    for w in f["windows"]:
        group=[x for x in f["rows"] if x["spacing_ghz"]==w["spacing_ghz"] and abs(x["offset"])<=(w["channels"]-1)//2]
        require(len(group)==5*w["channels"],"WDM group")
        for metric,prefix in [("fixed_gain_matrix_error","fixed_gain"),("channel_gain_matrix_error","channel_gain")]:
            error=max(x[metric] for x in group)
            require(close(error,w["worst_"+prefix+"_error"]),"WDM aggregate")
            require((error<=.05)==w[prefix+"_screen_passed"]==(w["channels"]==1),"WDM gate")
    # Rebuild the four interface admissions from the raw group results.
    key=lambda x:(x["bits"],x["launch_max_mw"],x["lo_per_output_mw"])
    admitted={}
    require(len(g["cases"])==180 and len(g["summaries"])==36,"interface grid")
    for s in g["summaries"]:
        rows=[x for x in g["cases"] if key(x)==key(s)]
        require(len(rows)==5 and len({x["target"] for x in rows})==5,"interface group")
        error=max(x["total_relative_error"] for x in rows)
        clip=max(x["adc_clip_fraction"] for x in rows)
        require(close(error,s["worst_error"]) and close(clip,s["worst_clip_fraction"]),"interface aggregate")
        passed=error<=.05 and clip==0
        require(passed==s["provisional_screen_passed"],"interface gate")
        if passed:admitted[key(s)]=error
    expected_errors={(8,1,1):.04812054379807613,(8,1,3):.047604616578430785,(10,1,1):.0429788433785091,(10,1,3):.0419308059452297}
    require(set(admitted)==set(expected_errors) and all(close(admitted[k],v) for k,v in expected_errors.items()),"four settings")
    require(len(h["cases"])==96 and h["architecture"]["carriers"]==1,"system cases")
    require(hashlib.sha256((ROOT/h["parameter_file"]).read_bytes()).hexdigest()==h["parameter_sha256"],"parameter provenance")
    for row in h["cases"]:
        require(key(row) in admitted and close(row["worst_relative_error"],admitted[key(row)]),"inherited accuracy")
        p=sum(row["power_terms_w"].values())
        require(close(p,row["partial_subtotal_w"]) and close(p*row["cooling_multiplier"],row["partial_cooled_proxy_w"]),"power sum")
        require(close(row["partial_energy_pj_per_vector"],row["partial_cooled_proxy_w"]/row["conditional_vectors_per_s"]*1e12),"energy vector")
        require(close(row["partial_energy_pj_per_complex_mac"]*16,row["partial_energy_pj_per_vector"]),"energy MAC")
    base=h["nominal_baseline"]
    require(key(base)==(8,1,1) and base["scenario"]=="nominal" and base["memory"]=="sram" and base["tia_frontends"]==8 and base["signal_distribution"]=="fixed_equal","baseline identity")
    require(base in h["cases"],"baseline row")
    require(close(base["partial_cooled_proxy_w"],.7023243568111672) and close(base["partial_energy_pj_per_complex_mac"],4.389527230069795),"baseline values")
    require(close(min(x["partial_cooled_proxy_w"] for x in h["cases"]),.24065993180597614) and close(max(x["partial_cooled_proxy_w"] for x in h["cases"]),7.432175333083025),"scenario extrema")
    nom={(x["bits"],x["lo_per_output_mw"]):x["partial_cooled_proxy_w"] for x in h["nominal_alternatives"]}
    require(set(nom)=={(8,1),(8,3),(10,1),(10,3)} and all(close(nom[k],v) for k,v in {(8,1):.7023243568111672,(8,3):.7769276212896781,(10,1):1.8293243568111672,(10,3):1.9039276212896779}.items()),"nominal alternatives")
    print(json.dumps(dict(archive_verified=True,experiments=8,numerical_checks=63,wdm_multi_channel_passed=False,interface_passing=4,system_cases=96,baseline_partial_w=base["partial_cooled_proxy_w"],baseline_pj_per_complex_mac=base["partial_energy_pj_per_complex_mac"],scope="archived numerical evidence; no hardware claims"),indent=2))
if __name__=="__main__":
    main()
