"""OPA-LIB-005-D3: controlled diagnostic of a pinned nonpassive SiEPIC PDK S-model.

Counterfactual variants are diagnostic transformations, not corrected component models.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from audit_lib005_bdc import load, parse, git_blob

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/"components/comparison/lib005-bdc-diagnostic-spec.json"
OUT=ROOT/"results/opa-lib-005-d3"
C=299792458.0

def check(condition, label):
    if not bool(condition):
        raise ValueError(label)

def norm_spectrum(a):
    return np.linalg.svd(a,compute_uv=False)[:,0]

def gate(sigma,tol):
    return int(np.count_nonzero(sigma>1+tol))

def summarize(sigma,tol):
    return {"max_sigma":float(np.max(sigma)),
            "min_sigma":float(np.min(sigma)),
            "violating_frequency_points":gate(sigma,tol)}

def main():
    spec=json.loads(SPEC.read_text())
    check(spec["experiment"]=="OPA-LIB-005-D3" and spec["quarantine_remains"] is True,"study safeguards")
    check(spec["calibration_eligible"] is False and spec["physical_device_quality_inferred"] is False and spec["interpolation_and_rescaling"] is False,"no unearned qualifications")
    ref_files={}
    for kind in ("report","csv"):
        p=ROOT/spec["reference_"+kind+"_path"]
        raw=p.read_bytes()
        check(git_blob(raw)==spec["reference_"+kind+"_git_blob_sha1"],"original archived "+kind+" identity")
        ref_files[kind]=raw
    original=json.loads(ref_files["report"])
    assert original["passivity"]["nonpassive_frequencies"]==50
    pdk_config,manifest,source,txt=load()
    check(source["git_blob_sha1"]==spec["upstream_blob_sha1"] and manifest["upstream_revision"]==spec["upstream_revision"],"exact source pin")
    f,S,mag,phase=parse(txt)
    check(S.shape==(51,4,4) and np.allclose(np.abs(S),mag,rtol=0,atol=1e-12),"unchanged source complex values")
    wavelengths=C/f*1e9
    sigma=norm_spectrum(S)
    original_csv=list(csv.DictReader(ref_files["csv"].decode().splitlines()))
    check(len(original_csv)==len(f)==51,"archived full grid")
    for i,row in enumerate(original_csv):
        check(math.isclose(float(row["frequency_hz"]),f[i],rel_tol=0,abs_tol=1e-3),"archived source frequency")
        check(math.isclose(float(row["sigma_max"]),sigma[i],rel_tol=5e-12,abs_tol=1e-12),"D1 vs D3 singular value")
        check(row["nonpassive_screen"]==str(bool(sigma[i]>1+1e-9)),"D1 passivity classification")
    check(gate(sigma,spec["passivity_tolerance"])==50,"original negative finding unchanged")
    check(math.isclose(float(np.max(sigma)),original["passivity"]["max_sigma_global"],rel_tol=1e-12),"D1 max mismatch")

    # Hermitian Gram = S^H S: off-diagonal entries quantify coherent
    # overlaps between different input-port responses. They can raise
    # maximum coherent gain even where individual input-column powers <= 1.
    gram=S.conj().transpose(0,2,1)@S
    colpowers=np.real(np.diagonal(gram,axis1=1,axis2=2))
    offdiag=gram.copy()
    diag=np.arange(4)
    offdiag[:,diag,diag]=0
    gram_offdiag_fro=np.linalg.norm(offdiag,axis=(1,2))
    cols_weak=np.max(colpowers,axis=1)<=1+1e-9
    violating=sigma>1+spec["passivity_tolerance"]
    counterexample=int(np.count_nonzero(cols_weak & violating))

    # The optimal coherent vector is a singular vector; not a fabricated
    # optical input experiment and phase convention remains unverified.
    u,sv,vh=np.linalg.svd(S)
    worst=vh.conj().transpose(0,2,1)[:,:,0]
    actual=np.sum(np.abs(np.einsum("fij,fj->fi",S,worst))**2,axis=1)
    check(np.allclose(actual,sv[:,0]**2,atol=1e-11),"coherent excitation SVD crosscheck")
    check(np.allclose(sigma,sv[:,0],atol=1e-12),"SVD ordering")

    # Transformations below are not candidate corrected models.
    sym=(S+S.transpose(0,2,1))/2
    no_same_side=S.copy()
    no_same_side[:,:2,:2]=0
    no_same_side[:,2:,2:]=0
    forward=S[:,2:,:2]
    backward=S[:,:2,2:]
    zero_phase=mag.astype(np.complex128)
    input_unitary=np.diag(np.exp(1j*np.array([0.3,-0.4,1.2,-0.6])))
    output_unitary=np.diag(np.exp(1j*np.array([-0.7,0.8,0.1,-1.1])))
    gauge=output_unitary@S@input_unitary
    gauge_delta=float(np.max(np.abs(norm_spectrum(gauge)-sigma)))
    check(gauge_delta<1e-11,"unitary port phase control must preserve SVD spectrum")
    check(np.allclose(np.abs(gauge),mag,atol=1e-11),"unitary phase shift must preserve magnitudes")

    variants={"as_tabulated":S,"reciprocity_symmetrized_counterfactual":sym,
              "same_side_port_blocks_removed_counterfactual":no_same_side,
              "forward_2x2_submatrix_diagnostic":forward,
              "backward_2x2_submatrix_diagnostic":backward,
              "all_phases_zero_counterfactual":zero_phase,
              "unitary_port_phase_control":gauge}
    spectra={k:norm_spectrum(v) for k,v in variants.items()}
    check(all(len(v)==51 and np.all(np.isfinite(v)) for v in spectra.values()),"finite variant spectra")
    recerr=np.max(np.abs(S-S.transpose(0,2,1)),axis=(1,2))
    midpoint=int(np.argmin(np.abs(wavelengths-1550)))
    rows=[]
    for i in range(len(f)):
        row={"frequency_hz":float(f[i]),"wavelength_nm":float(wavelengths[i]),
             "max_input_column_power":float(np.max(colpowers[i])),
             "max_coherent_output_power":float(actual[i]),
             "gram_offdiagonal_fro":float(gram_offdiag_fro[i]),
             "reciprocity_max_field_difference":float(recerr[i]),
             "violates_but_each_column_at_most_one":bool(cols_weak[i] and violating[i])}
        row.update({k+"_sigma_max":float(v[i]) for k,v in spectra.items()})
        rows.append(row)
    result={"experiment":"OPA-LIB-005-D3",
            "source":{"repo":manifest["upstream_repo"],"revision":manifest["upstream_revision"],
                      "git_blob_sha1":source["git_blob_sha1"],"kind":"unqualified_upstream_model"},
            "archived_d1_consistency":{"all_51_frequency_rows_and_singular_values_match":True,"nonpassive_samples":50,
                                       "max_sigma":float(np.max(sigma))},
            "coherent_multiport":{"violating_samples_despite_all_input_columns_at_most_one":counterexample,
                                  "max_single_input_collected_power":float(np.max(colpowers)),
                                  "max_offdiagonal_gram_fro":float(np.max(gram_offdiag_fro)),
                                  "max_optimal_coherent_power_ratio":float(np.max(actual)),
                                  "center_wavelength_nm":float(wavelengths[midpoint]),
                                  "center_optimal_coherent_power_ratio":float(actual[midpoint])},
            "variants":{k:summarize(v,spec["passivity_tolerance"]) for k,v in spectra.items()},
            "controls":{"port_phase_gauge_max_sigma_difference":gauge_delta,"rephasing_invariance":True,
                        "original_svd_replayed":True,"input_vector_reconstruction":True},
            "status":{"component":"siepic-bdc-te1550","decision":"quarantined_nonpassive",
                      "promoted_to_passive_model":False,"original_source_modified":False,
                      "derived_counterfactual_model_qualified":False,"fabricated_device_passivity_inferred":False},
            "interpretation":["Off-diagonal S^H S captures coherent port overlap that single-column power checks miss.",
                              "Reciprocity symmetrization, zero-phase and dropping blocks are interventions not physically validated repairs.",
                              "A submatrix spectral norm is not the same as full 4-port passivity certification.",
                              "All diagnostics assume upstream amplitude/phase encoding and port normalization are meaningful.",
                              "The cause of spectral norm >1 cannot be uniquely established without original model generation and port/reference-plane documentation.",
                              "Do not combine SOI findings with independent TFLN PDK process qualification."],
            "checks":{"pinned_source":True,"archived_rows_match":True,"all_four_ports":True,
                      "svd_and_coherent_excitation":True,"gram_column_consistency":bool(np.allclose(colpowers,np.sum(mag**2,axis=1),atol=1e-12)),
                      "phase_gauge_control":True,"all_variants_finite":True,"negative_model_gate_retained":True}}
    check(all(result["checks"].values()) and not result["status"]["promoted_to_passive_model"],"fail-closed checks")
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    with (OUT/"diagnostics.csv").open("w",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
