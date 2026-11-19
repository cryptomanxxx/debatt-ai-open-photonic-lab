"""Preserve exact LIB003 complex S exports, including quarantined model; no reruns."""
import argparse
import cmath
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/external/Luxtelligence/lnoi400/s_parameters"
MANIFEST=BASE/"archive-source.json"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b):
    return hashlib.sha256(b).hexdigest()
def close(a,b,tol=1e-10):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol
def polyval(coef,x):
    v=0.
    for c in coef: v=v*x+c
    return v
def polynomial(d,wl):
    x=wl-d["center_wavelength"]
    def value(k):
        return polyval(d["pol_"+k+"_abs"],x)*cmath.exp(1j*polyval(d["pol_"+k+"_phase"],x))
    b,c,r,s=map(value,("trans_bar","trans_cross","refl_bar","refl_cross"))
    return [[r,s,c,b],[s,r,b,c],[c,b,r,s],[b,c,s,r]]
def audit(raw):
    m=json.loads(MANIFEST.read_text())
    require(len(raw)==m["size"] and sha(raw)==m["sha256"],"pinned ZIP identity")
    ids={"mmi-2x2","directional-coupler"}
    require(set(m["components"])==ids,"pinned component selection")
    expected={i+s for i in ids for s in (".s.json",".metrics.csv")} | {"result.json","environment-lock.txt","installed-packages.json"}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        require(len(names)==len(set(names)) and set(names)==expected,"exact ZIP member set")
        require(sum(i.file_size for i in entries)<10_000_000,"archive size limit")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(len(p.parts)==1 and p.name==i.filename and not p.is_absolute() and "\\" not in i.filename and not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16),"unsafe member")
        require(z.testzip() is None,"ZIP CRC")
        files={n:z.read(n) for n in names}
    require(files["environment-lock.txt"]==(ROOT/"layout/requirements-lock-lnoi400.txt").read_bytes(),"environment identity")
    spec=json.loads((BASE/"manifest.json").read_text())
    report=json.loads(files["result.json"])
    require(report["experiment"]==spec["experiment"]==m["experiment"]=="OPA-LIB-003" and report["revision"]==spec["revision"]==m["revision"],"experiment revision")
    require(set(report["checks"])=={"source_identity","geometry_link","full_complex_grid","native_polynomial_agreement","reciprocity","passivity_classification"} and all(v is True for v in report["checks"].values()),"six audit checks")
    require(len(report["components"])==len(spec["components"])==2,"component count")
    rows={x["component"]:x for x in report["components"]}
    specs={x["id"]:x for x in spec["components"]}
    require(set(rows)==set(specs)==ids,"component identity")
    for ident in sorted(ids):
        r=rows[ident]; s=specs[ident]; pin=m["components"][ident]
        raw_data=files[ident+".s.json"]
        d=json.loads(raw_data)
        require(sha(raw_data)==r["dataset_sha256"]==pin["dataset_sha256"],"dataset hash "+ident)
        source=(BASE/s["local_source"]).read_bytes()
        require(sha(source)==d["source_sha256"]==r["source_sha256"]==pin["source_sha256"],"original coefficient hash")
        require(d["source_git_blob_sha1"]==s["source_git_blob_sha1"],"source blob")
        gds=(BASE.parent/"archive/gds"/(ident+".gds")).read_bytes()
        require(sha(gds)==d["gds_sha256"]==r["gds_sha256"]==s["gds_sha256"],"GDS identity")
        require(d["component"]==ident and d["revision"]==m["revision"] and d["port_order"]==spec["port_order"]==["o1","o2","o3","o4"],"dataset metadata")
        for key in ("matrix_convention","complex_encoding","normalization","reference_planes","phase","validity","polarization","bias_temperature"):
            require(d[key]==spec[key],"convention "+key)
        require(d["measurement"] is None and d["qualification"] is None and d["source_type"]==s["source_type"],"evidence scope")
        wl=d["wavelength_nm"]; mats=d["scattering"]
        csvrows=list(csv.DictReader(io.StringIO(files[ident+".metrics.csv"].decode())))
        require(len(wl)==len(mats)==len(csvrows)==r["samples"]==201 and r["midpoint_samples"]==200,"grid length")
        data=json.loads(source)
        sigma=[]; matrices=[]
        for i,(w,mat,c) in enumerate(zip(wl,mats,csvrows)):
            require(close(w,1540+i*.1) and close(float(c["wavelength_nm"]),w),"grid value")
            require(len(mat)==4 and all(len(row)==4 and all(len(v)==2 and all(math.isfinite(x) for x in v) for v in row) for row in mat),"matrix shape/finite")
            a=[[complex(*v) for v in row] for row in mat]
            matrices.append(a)
            expected=polynomial(data,w/1000)
            require(max(abs(a[j][k]-expected[j][k]) for j in range(4) for k in range(4))<=1e-10,"coefficient agreement")
            require(max(abs(a[j][k]-a[k][j]) for j in range(4) for k in range(4))<=1e-10,"reciprocity")
            # These symmetric four-port matrices are diagonalized by a real
            # orthogonal Hadamard basis. Singular values are abs(eigenvalues).
            rr,ss,cc,bb=a[0]
            sv=max(abs(rr+u*ss+v*cc+u*v*bb) for u in (-1,1) for v in (-1,1))
            sigma.append(sv)
            power=[sum(abs(a[j][k])**2 for j in range(4)) for k in range(4)]
            require(close(float(c["sigma_max"]),sv) and close(float(c["max_input_power"]),max(power)) and close(float(c["reciprocity_error"]),0),"metric consistency")
            require(close(float(c["bar_power"]),abs(a[3][0])**2) and close(float(c["cross_power"]),abs(a[2][0])**2) and close(float(c["reflection_power"]),sum(abs(a[j][0])**2 for j in (0,1))),"power consistency")
        fail=sum(x>1+1e-10 for x in sigma)
        require(fail==r["nonpassive_samples"]==pin["nonpassive_samples"],"preserve negative result")
        require(d["passivity_screen_eligible"] is (fail==0) and r["passivity_screen_eligible"] is (fail==0) and d["usage"]==r["usage"]==pin["usage"],"quarantine classification")
        require(close(max(sigma),r["max_sigma"]) and close(max(sigma),pin["max_sigma"]) and close(min(sigma),r["min_sigma"]),"singular values")
        require(all(close(float(v),float(csvrows[100][k])) for k,v in r["center"].items()),"center metrics")
        midpoint=max(abs(polynomial(data,(wl[i]+wl[i+1])/2000)[j][k]-(matrices[i][j][k]+matrices[i+1][j][k])/2) for i in range(200) for j in range(4) for k in range(4))
        require(close(midpoint,r["max_complex_linear_midpoint_error"]) and close(midpoint,pin["midpoint_error"]),"midpoint error")
    out={"original.zip":raw}
    for name,b in files.items():
        folder="datasets" if name.endswith(".s.json") else "metrics" if name.endswith(".metrics.csv") else "evidence"
        out[folder+"/"+name]=b
    provenance=dict(**m,verification="Exact ZIP, CRC, member set, dataset hashes, source/GDS linkage, independent polynomial and sampled passivity replay, midpoint diagnostics and staged byte identity; no reruns.",
                    members={name:{"bytes":len(b),"sha256":sha(b)} for name,b in sorted(out.items())})
    out["provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    files=audit(a.source.read_bytes())
    if a.output:
        require(not a.output.exists(),"refuse overwrite")
        a.output.mkdir(parents=True)
        for n,b in files.items():
            f=a.output/n
            f.parent.mkdir(parents=True,exist_ok=True)
            f.write_bytes(b)
    else:
        require({p.relative_to(a.staged).as_posix() for p in a.staged.rglob("*") if p.is_file()}==set(files),"archived member set")
        for n,b in files.items():
            require((a.staged/n).read_bytes()==b,"archived bytes "+n)
    print(f"Verified two LIB003 S datasets (6432 complex values; quarantine preserved), {len(files)} archive files, {sum(map(len,files.values()))} bytes.")
if __name__=="__main__":
    main()
