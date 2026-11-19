"""Preserve exact LIB004 measured scan analysis; independently replay MAT/CSV/OLS.

Only the pinned uncompressed little-endian MATLAB v5 subset is accepted.
No new measurement, no replacement analysis artifact.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/experimentally_validated/SiEPIC-PCM-2020-02-UW"
MANIFEST=BASE/"archive-source.json"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b):
    return hashlib.sha256(b).hexdigest()
def blob(b):
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def close(a,b,tol=1e-9):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol

def elements(b):
    pos=0
    while pos<len(b):
        require(pos+8<=len(b),"MAT tag truncated")
        tag,n=struct.unpack_from("<II",b,pos)
        if tag>>16:
            typ,size=tag&65535,tag>>16
            require(0<size<=4,"MAT small tag")
            yield typ,b[pos+4:pos+4+size]
            pos+=8
        else:
            require(pos+8+n<=len(b),"MAT element truncated")
            yield tag,b[pos+8:pos+8+n]
            pos+=8+((n+7)//8)*8
    require(pos==len(b),"MAT padding")

def matrix(payload):
    it=iter(elements(payload))
    typ,flags=next(it); require(typ==6 and len(flags)==8,"MAT flags")
    cls=struct.unpack("<II",flags)[0]&255
    typ,dim=next(it); require(typ==5 and len(dim)%4==0,"MAT dims")
    shape=struct.unpack("<"+"i"*(len(dim)//4),dim)
    typ,name=next(it); require(typ==1,"MAT name")
    name=name.decode("ascii")
    if cls==2:
        require(shape==(1,1),"MAT scalar struct")
        typ,n=next(it); require(typ==5 and len(n)==4,"MAT field width")
        width=struct.unpack("<i",n)[0]
        typ,fields=next(it); require(typ==1 and width>0 and len(fields)%width==0,"MAT field names")
        keys=[fields[i:i+width].split(b"\0",1)[0].decode("ascii") for i in range(0,len(fields),width)]
        require(len(set(keys))==len(keys),"MAT duplicate fields")
        result={}
        for k in keys:
            typ,v=next(it); require(typ==14,"MAT field matrix")
            result[k]=matrix(v)
    elif cls==6:
        typ,v=next(it); require(typ==9 and len(v)==8*math.prod(shape),"MAT doubles")
        result=struct.unpack("<"+"d"*math.prod(shape),v)
        require(all(map(math.isfinite,result)),"MAT finite")
    elif cls==12:
        typ,v=next(it); require(typ==5 and len(v)==4 and math.prod(shape)==1,"MAT integer scalar")
        result=struct.unpack("<i",v)[0]
    elif cls==4:
        typ,v=next(it); require(typ==16 and len(v)==math.prod(shape),"MAT UTF8 chars")
        result=v.decode("utf-8")
    else:
        raise ValueError("unsupported MAT class "+str(cls))
    require(next(it,None) is None,"extra matrix data")
    return name,shape,result

def mat_read(raw):
    require(len(raw)==193336 and raw.startswith(b"MATLAB 5.0 MAT-file") and raw[126:128]==b"IM","MAT header")
    top={}
    for typ,payload in elements(raw[128:]):
        require(typ==14,"MAT uncompressed matrix")
        name,shape,result=matrix(payload)
        require(name not in top,"MAT duplicate matrix")
        top[name]=(shape,result)
    require(set(top)=={"scandata","metadata"},"MAT top-level keys")
    scan=top["scandata"][1]; meta=top["metadata"][1]
    _,wshape,w=scan["wavelength"]
    _,pshape,p=scan["power"]
    require(wshape==(1,6001) and pshape==(6001,3),"MAT measurement dimensions")
    return w,[p[i*6001:(i+1)*6001] for i in range(3)],meta

def fit(x,y):
    mx=math.fsum(x)/len(x); my=math.fsum(y)/len(y)
    xx=[v-mx for v in x]
    ssx=math.fsum(v*v for v in xx)
    slope=math.fsum(v*(b-my) for v,b in zip(xx,y))/ssx
    intercept=my-slope*mx
    residual=[b-intercept-slope*a for a,b in zip(x,y)]
    sse=math.fsum(v*v for v in residual)
    sst=math.fsum((v-my)**2 for v in y)
    se=math.sqrt(sse/(len(x)-2)/ssx)
    return -slope,intercept,1-sse/sst if sst else None,se

def audit(raw):
    m=json.loads(MANIFEST.read_text())
    require(len(raw)==m["size"] and sha(raw)==m["sha256"],"pinned ZIP identity")
    expected={"raw-detectors.csv","cutback-spectrum.csv","result.json","installed-packages.json"}
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
    spec=json.loads((BASE/"manifest.json").read_text())
    r=json.loads(files["result.json"])
    require(r["experiment"]==spec["experiment"]==m["experiment"]=="OPA-LIB-004" and r["revision"]==spec["revision"]==m["revision"],"experiment revision")
    require(set(r["checks"])=={"original_identity","shape_and_finite","common_grid","device_metadata","independent_center_readback","ols_crosscheck"} and all(v is True for v in r["checks"].values()),"six verified checks")
    require(r["source_run"]==spec["source_run"] and r["evidence_scope"]==spec["evidence_scope"] and r["geometry_match"]==spec["geometry_match"],"measurement scope")
    require(all(r[k] is None and spec[k] is None for k in ("phase","complex_s","qualification","measurement_uncertainty")),"no promotion")
    require(r["detector_number"]==spec["detector_number"]==2 and r["detector_readings"]==m["detector_readings"]==90015 and r["wavelength_points_per_scan"]==6001,"sample count")
    require(blob((BASE/"LICENSE.md").read_bytes())==spec["license_git_blob_sha1"] and blob((BASE/"upstream/spiral_cutback_analysis.py").read_bytes())==spec["analysis_git_blob_sha1"],"license and original analysis")
    require(len(spec["files"])==len(r["measurement_files"])==len(m["source_sha256"])==5,"original file count")
    scan_rows=csv.DictReader(io.StringIO(files["raw-detectors.csv"].decode()))
    require(scan_rows.fieldnames==["device_number","nominal_length_um","wavelength_nm","detector1_db","detector2_db","detector3_db"],"raw CSV schema")
    x=[]; y=[]; wref=None
    for e,record,pin in zip(spec["files"],r["measurement_files"],m["source_sha256"],strict=True):
        b=(BASE/"original"/e["name"]).read_bytes()
        require(len(b)==e["bytes"]==193336 and blob(b)==e["git_blob_sha1"]==record["git_blob_sha1"] and sha(b)==record["sha256"]==pin,"original MAT identity")
        w,p,meta=mat_read(b)
        require(meta["device"][2]==e["name"][:-4] and meta["measured_device_number"][2]==e["measured_device_number"]==record["measured_device_number"],"independent device IDs")
        require(record["device_number"]==e["device_number"] and record["nominal_length_um"]==e["nominal_length_um"] and record["name"]==e["name"],"record metadata")
        require(meta["time_str"][2]==record["measured_time_as_stored"] and [meta[k][2][0] for k in ("gds_x_coord","gds_y_coord")]==record["gds_coord_as_stored"],"time/coordinate identity")
        if wref is None: wref=w
        require(w==wref,"common grid")
        x.append(e["nominal_length_um"]*1e-4);y.append(p[1])
        require(sum(v<=-100 for v in p[1])==record["detector2_floor_count"] and p[1][3000]==record["detector2_center_db"],"source detector statistics")
        for i,a in enumerate(w):
            c=next(scan_rows)
            require(int(c["device_number"])==e["device_number"] and int(c["nominal_length_um"])==e["nominal_length_um"],"raw row identity")
            require(close(float(c["wavelength_nm"]),a*1e9) and close(a*1e9,1520+i*.01),"raw grid")
            require(all(float(c[f"detector{k+1}_db"])==p[k][i] for k in range(3)),"all raw readings exact")
    require(next(scan_rows,None) is None,"extra raw rows")
    require([sum(v<=-100 for v in p) for p in y]==r["floor_or_below_counts"]==m["floor_counts"],"floor counts")
    spectra=list(csv.DictReader(io.StringIO(files["cutback-spectrum.csv"].decode())))
    require(len(spectra)==6001,"spectrum length")
    complete=0
    for i,c in enumerate(spectra):
        require(close(float(c["wavelength_nm"]),wref[i]*1e9),"spectrum grid")
        values=[p[i] for p in y]
        n=sum(v<=-100 for v in values)
        require(int(c["floor_or_below_count"])==n and c["eligible_complete_five_point_fit"]==str(n==0),"eligibility")
        if n:
            require(all(c[k]=="" for k in ("loss_db_per_cm","intercept_db","r2")),"excluded values remain absent")
        else:
            complete+=1
            loss,intercept,r2,se=fit(x,values)
            require(close(float(c["loss_db_per_cm"]),loss) and close(float(c["intercept_db"]),intercept) and close(float(c["r2"]),r2),"spectrum OLS replay")
    require(complete==r["complete_spectral_fits"]==m["complete_spectral_fits"]==5972,"complete fits")
    values=[p[3000] for p in y]
    loss,intercept,r2,se=fit(x,values)
    center=r["center_raw_fit"]
    require(close(loss,center["loss_db_per_cm"]) and close(loss,m["center_loss"]) and close(intercept,center["intercept_db"]) and close(r2,center["r2"]) and close(r2,m["center_r2"]) and close(se,center["slope_standard_error_db_per_cm"]),"center regression")
    # Exact fixed df=3 t critical value, not instrument uncertainty.
    half=3.182446305284263*se
    require(all(close(a,b) and close(a,c) for a,b,c in zip([loss-half,loss+half],center["conditional_ols_95ci_loss_db_per_cm"],m["center_ci"])),"conditional CI")
    qloss,qintercept,qr2,qse=fit(x,r["center_local_quartic_detector_values_db"])
    q=r["center_local_quartic_fit"]
    require(close(qloss,q["loss_db_per_cm"]) and close(qloss,m["quartic_loss"]) and close(qintercept,q["intercept_db"]) and close(qr2,q["r2"]) and close(qse,q["slope_standard_error_db_per_cm"]),"quartic derived regression")
    for i,record in enumerate(r["leave_one_out_center"]):
        loss=fit(x[:i]+x[i+1:],values[:i]+values[i+1:])[0]
        require(record["omitted_device"]==spec["files"][i]["device_number"] and close(loss,record["loss_db_per_cm"]) and close(loss,m["loo"][i]),"leave-one-out replay")
    out={"original.zip":raw}
    for name,b in files.items():
        folder="datasets" if name.endswith(".csv") else "evidence"
        out[folder+"/"+name]=b
    provenance=dict(**m,verification="Exact ZIP/CRC/member set, independent uncompressed MAT v5 read, all 90015 raw detector values, all eligible spectrum OLS fits, center CI and leave-one-out replay, quartic derived regression from frozen fitted values, staged byte identity. No rerun or claim of independent quartic refit.",
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
    print(f"Verified LIB004 (90015 measured detector values; 5972 complete spectral fits), {len(files)} archive files, {sum(map(len,files.values()))} bytes.")
if __name__=="__main__":
    main()
