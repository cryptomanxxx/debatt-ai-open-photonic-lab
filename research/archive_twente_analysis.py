"""Preserve exact three successful CI artifacts; replay all derived outputs from pinned sources.

Replay uses the original analysis implementations, not a new independent estimator.
Original ZIP bytes are retained, and all JSON fields and CSV cells checked.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"components/experimentally_validated/Twente-TFLN-Wei-2025"
MANIFEST=BASE/"analysis-archive-source.json"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def equivalent(a,b,path=""):
    if isinstance(a,bool) or isinstance(b,bool) or a is None or b is None:
        require(type(a)==type(b) and a==b,"value "+path)
    elif isinstance(a,(int,float)) and isinstance(b,(int,float)):
        require(math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9),"numeric "+path)
    elif isinstance(a,dict) and isinstance(b,dict):
        require(set(a)==set(b),"keys "+path)
        for k in a: equivalent(a[k],b[k],path+"/"+k)
    elif isinstance(a,list) and isinstance(b,list):
        require(len(a)==len(b),"length "+path)
        for i,(x,y) in enumerate(zip(a,b)): equivalent(x,y,path+"/"+str(i))
    else: require(type(a)==type(b) and a==b,"value "+path)
def compare_csv(a,b):
    aa=list(csv.reader(io.StringIO(a.decode())))
    bb=list(csv.reader(io.StringIO(b.decode())))
    require(len(aa)==len(bb) and aa[0]==bb[0],"CSV header/count")
    for x,y in zip(aa[1:],bb[1:]):
        require(len(x)==len(y)==len(aa[0]),"CSV width")
        for u,v in zip(x,y):
            if u==v: continue
            equivalent(float(u),float(v),"CSV cell")
def audit(source):
    m=json.loads(MANIFEST.read_text())
    require([p["key"] for p in m]==["modulator","ring","cascade"],"manifest set")
    require({p.name for p in source.iterdir()}=={p["key"]+".zip" for p in m},"exact source ZIP set")
    out={}
    total=0
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)
        # Run the reviewed implementations in an isolated temporary repo-shaped tree.
        dest=work/BASE.relative_to(ROOT)
        dest.mkdir(parents=True)
        shutil.copytree(BASE/"archive/original",dest/"archive/original")
        (work/"tools").mkdir()
        for pin in m:
            key=pin["key"]
            raw=(source/(key+".zip")).read_bytes()
            require(len(raw)==pin["size"] and sha(raw)==pin["sha256"],"ZIP identity "+key)
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                entries=z.infolist()
                names=[i.filename for i in entries]
                require(len(names)==2 and set(names)=={"result.json",pin["csv"]},"exact ZIP members "+key)
                require(sum(i.file_size for i in entries)<2_000_000,"ZIP size")
                for i in entries:
                    p=PurePosixPath(i.filename)
                    require(len(p.parts)==1 and p.name==i.filename and not p.is_absolute() and "\\" not in i.filename and not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16),"unsafe ZIP member")
                require(z.testzip() is None,"CRC "+key)
                files={n:z.read(n) for n in names}
            result=json.loads(files["result.json"])
            equivalent(result,pin["expected_result"],key+"/original CI log")
            require(result["experiment"]==pin["experiment"] and all(v is True for v in result["checks"].values()),"checks "+key)
            require(all(result[k] is None for k in ("complex_s","geometry_match","qualification")),"no promotion")
            total+=len(result["checks"])
            code=ROOT/"tools"/f"audit_twente_tfln_{key}.py"
            code_bytes=code.read_bytes()
            require(hashlib.sha1(f"blob {len(code_bytes)}\0".encode()+code_bytes).hexdigest()==pin["analysis_git_blob_sha1"],"pinned analysis implementation")
            copy=work/"tools"/code.name
            shutil.copyfile(code,copy)
            subprocess.run([sys.executable,str(copy)],cwd=work,check=True,stdout=subprocess.DEVNULL)
            replay=work/"results"/pin["name"]
            equivalent(json.loads((replay/"result.json").read_bytes()),result,key+"/replay")
            compare_csv(files[pin["csv"]],(replay/pin["csv"]).read_bytes())
            out[key+"/original.zip"]=raw
            out[key+"/result.json"]=files["result.json"]
            out[key+"/"+pin["csv"]]=files[pin["csv"]]
    require(total==19,"19 original checks")
    provenance=dict(source_doi="10.5281/zenodo.14065933",dataset_license="CC BY 4.0",creator="Chuangchuang Wei",
                    article_doi="10.1038/s41467-025-57441-1",original_checks=total,
                    sources=[{k:v for k,v in p.items() if k!="expected_result"} for p in m],
                    verification="Pinned original ZIP/CRC/member set, all JSON fields against original CI log, full replay with pinned reviewed implementation, all CSV cells compared with numeric tolerance; exact staged bytes. Replay is not an independent estimator.",
                    limitations="No new measurements, exact geometry match, measured complex S, calibration or qualification. Original dataset attribution retained; derived outputs unchanged.",
                    members={n:dict(bytes=len(b),sha256=sha(b)) for n,b in sorted(out.items())})
    out["provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    if a.staged:
        require(a.source is None,"staged ZIPs only")
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)
            for key in ("modulator","ring","cascade"):
                shutil.copyfile(a.staged/key/"original.zip",source/(key+".zip"))
            files=audit(source)
        require({p.relative_to(a.staged).as_posix() for p in a.staged.rglob("*") if p.is_file()}==set(files),"exact staged file set")
        for n,b in files.items(): require((a.staged/n).read_bytes()==b,"staged bytes "+n)
    else:
        require(a.source is not None,"source required")
        files=audit(a.source)
        require(not a.output.exists(),"refuse overwrite")
        a.output.mkdir(parents=True)
        for n,b in files.items():
            dest=a.output/n
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(b)
    print(f"Verified 3 original Twente analysis artifacts, 19 checks, {len(files)} archive files, {sum(map(len,files.values()))} bytes.")
if __name__=="__main__": main()
