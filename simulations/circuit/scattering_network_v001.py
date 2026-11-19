"""OPA-CIR-001: validate reusable scattering-network assembly against MZI references."""
import json
from pathlib import Path
import numpy as np
from mzi import coupler, phase, phase_screen, programmed_matrix, programmed_matrix_hw, program_unitary, haar_unitary
from scattering_network import assemble, reciprocal_transmission

OUT=Path("results/opa-cir-001")
TOL=1e-12
SEED=20261119
PORTS=("l0","l1","r0","r1")

def network(theta,phi,a,b,split1=.5,split2=.5,loss_top_db=0.,loss_bottom_db=0.):
    # Reuse existing analytic component functions, not new physical models.
    arm=np.diag([np.exp(1j*theta)*10**(-loss_top_db/20),10**(-loss_bottom_db/20)])
    stages=[phase(phi),coupler(split1),arm,coupler(split2),phase_screen(a,b)]
    blocks={str(i):(PORTS,reciprocal_transmission(t)) for i,t in enumerate(stages)}
    links=[((str(i),"r"+str(j)),(str(i+1),"l"+str(j))) for i in range(4) for j in range(2)]
    external=[("0","l0"),("0","l1"),("4","r0"),("4","r1")]
    return assemble(blocks,links,external)

def error(a,b):
    return float(np.max(np.abs(a-b)))

def rejected(fn):
    try:
        fn()
    except ValueError:
        return True
    return False

def main():
    rng=np.random.default_rng(SEED)
    ref=json.loads(Path("results/opa-mzi-001/result.json").read_text())
    assert ref["experiment"]=="OPA-MZI-001" and not ref["failures"]
    errors={k:0. for k in ("ideal_complex_field","unitarity","reciprocity","reflectionless","reverse_transpose","programmed_targets","lossy_reference","passivity_excess","archived_sweep","archived_rotation")}
    def record(k,v):
        errors[k]=max(errors[k],float(v))
    for _ in range(128):
        angles=rng.uniform(0,2*np.pi,4)
        s=network(*angles)
        t=programmed_matrix(*angles)
        record("ideal_complex_field",error(s[2:,:2],t))
        record("unitarity",error(s.conj().T@s,np.eye(4)))
        record("reciprocity",error(s,s.T))
        record("reflectionless",max(error(s[:2,:2],0),error(s[2:,2:],0)))
        record("reverse_transpose",error(s[:2,2:],t.T))
        u=haar_unitary(2,rng)
        record("programmed_targets",error(network(*program_unitary(u))[2:,:2],u))
        hw=dict(split1=.47,split2=.53,loss_top_db=.8,loss_bottom_db=.2)
        lossy=network(*angles,**hw)
        record("lossy_reference",error(lossy[2:,:2],programmed_matrix_hw(angles,hw)))
        record("passivity_excess",max(0,np.linalg.svd(lossy,compute_uv=False)[0]-1))
    for row in ref["splitting_sweep"]:
        s=network(row["theta_rad"],0,0,0)
        record("archived_sweep",error(abs(s[2:,0])**2,[row["power_top"],row["power_bottom"]]))
    for settings in ref["degenerate_case_settings"].values():
        angles=[settings[k] for k in ("theta","phi","a","b")]
        record("ideal_complex_field",error(network(*angles)[2:,:2],programmed_matrix(*angles)))
    rotation=ref["rotation_30deg"]
    s=network(*(rotation["settings"][k] for k in ("theta","phi","a","b")))
    for row in rotation["samples"]:
        target=np.array([complex(*z) for z in row["output_field"]])
        record("archived_rotation",error(s[2:,:2]@row["input"],target))
    # Independent analytic Fabry-Perot-like reflection test: two identical
    # lossless reciprocal mirrors (real reflection, imaginary transmission).
    r=.4
    t=1j*np.sqrt(1-r*r)
    mirror=np.array([[r,t],[t,r]])
    blocks={"a":(("l","r"),mirror),"b":(("l","r"),mirror)}
    links=[(("a","r"),("b","l"))]
    boundary=[("a","l"),("b","r")]
    result=assemble(blocks,links,boundary)
    expected=np.array([[r+t*t*r/(1-r*r),t*t/(1-r*r)],[t*t/(1-r*r),r+t*t*r/(1-r*r)]])
    errors["reflective_network"]=error(result,expected)
    errors["reflective_unitarity"]=error(result.conj().T@result,np.eye(2))
    # Nonresonant lossy asymmetric mirrors test nonzero reflection as well.
    other=np.array([[.2,.6j],[.6j,.2]])
    result=assemble({"a":blocks["a"],"b":(("l","r"),other)},links,boundary)
    den=1-r*.2
    expected=np.array([[r+t*t*.2/den,t*.6j/den],[t*.6j/den,.2+(.6j)**2*r/den]])
    errors["asymmetric_reflection"]=error(result,expected)
    errors["boundary_reordering"]=error(assemble(blocks,links,boundary[::-1]),assemble(blocks,links,boundary)[::-1,::-1])
    checks={k:bool(np.isfinite(v) and v<=TOL) for k,v in errors.items()}
    checks["duplicate_port_rejected"]=rejected(lambda:assemble(blocks,links,[boundary[0],boundary[0]]))
    checks["unconnected_port_rejected"]=rejected(lambda:assemble(blocks,[],boundary))
    checks["unknown_port_rejected"]=rejected(lambda:assemble(blocks,links,[boundary[0],("b","x")]))
    checks["singular_loop_rejected"]=rejected(lambda:assemble({"a":(("l","r"),np.eye(2)),"b":(("l","r"),np.eye(2))},links,boundary))
    checks["nonfinite_rejected"]=rejected(lambda:reciprocal_transmission([[np.nan]]))
    checks["wrong_phase_detected"]=error(network(.7,.2,.3,.4)[2:,:2],programmed_matrix(.7,.2,.3,.5))>1e-3
    failures=[k for k,v in checks.items() if not v]
    report=dict(experiment="OPA-CIR-001",seed=SEED,random_trials=128,tolerance=TOL,checks=checks,errors=errors,failures=failures,
                reference="OPA-MZI-001 archived sweep and rotation; existing MZI-002 hardware transfer formula",
                model_scope="ideal/assumed linear single-frequency power-normalized scattering blocks",
                port_order=["input_top","input_bottom","output_top","output_bottom"],
                limitations=["No PDK model imported, no measured or FDTD complex S data.","Assumed lossy reference is not physical device evidence.","No wavelength interpolation, active/nonlinear state, noise, electrical or thermal model.","Linear steady-state solve; no transient or physical throughput claim."])
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2,allow_nan=False))
    if failures:
        raise SystemExit("failed: "+", ".join(failures))

if __name__=="__main__":
    main()
