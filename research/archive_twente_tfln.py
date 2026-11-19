"""Archive the exact CC BY 4.0 Twente dataset; no inferred measurement semantics."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile
import csv
import stat
from pathlib import PurePosixPath

BASE=Path(__file__).resolve().parents[1]/"components/experimentally_validated/Twente-TFLN-Wei-2025"
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def get(url,limit):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Debatt-AI Open Photonic Lab dataset archive"}),timeout=60) as response:
        b=response.read(limit+1)
    require(len(b)<=limit,"download size")
    return b
def audit(raw):
    m=json.loads((BASE/"manifest.json").read_text())
    require(m["license_status"]=="verified_cc_by_4_0" and m["record"]==14065933,"license scope")
    require(len(raw)==m["zip_bytes"] and sha(raw)==m["zip_sha256"] and hashlib.md5(raw).hexdigest()==m["md5"],"pinned ZIP identity")
    pins={e["path"]:e for e in m["inventory"]}
    require(len(pins)==40 and set(pins)==set(m["expected_csv_paths"]),"inventory")
    out={"original.zip":raw}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        require(len(names)==len(set(names)) and len(names)<200 and sum(i.file_size for i in entries)<30_000_000,"ZIP bounds")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in i.filename and not stat.S_ISLNK(i.external_attr>>16),"unsafe ZIP path")
        require(z.testzip() is None,"CRC")
        require({i.filename for i in entries if not i.is_dir()}==set(pins),"exact file set")
        for name,pin in sorted(pins.items()):
            b=z.read(name)
            require(len(b)==pin["bytes"] and sha(b)==pin["sha256"],"member identity "+name)
            rows=csv.reader(io.StringIO(b.decode("utf-8-sig")))
            counts={}
            for row in rows: counts[str(len(row))]=counts.get(str(len(row)),0)+1
            require(counts==pin["row_width_counts"],"CSV schema "+name)
            out["original/"+name]=b
    provenance=dict(record=m["record"],doi=m["doi"],creator=m["creator"],license="CC BY 4.0",license_url=m["license_url"],source_url=m["license_evidence"],preflight_run=m["verified_run"],zip_sha256=m["zip_sha256"],changes="None to original ZIP or CSV bytes; extracted copies and provenance added.",scope="External experimental figure source data; individual semantics pending; no geometry equivalence or complex S claim.",members={n:{"bytes":len(b),"sha256":sha(b)} for n,b in sorted(out.items())})
    out["provenance.json"]=(json.dumps(provenance,indent=2,sort_keys=True)+"\n").encode()
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    if a.source:
        raw=a.source.read_bytes()
    else:
        m=json.loads((BASE/"manifest.json").read_text())
        rec=json.loads(get("https://zenodo.org/api/records/14065933",2_000_000))
        require(rec["id"]==m["record"] and rec["doi"]==m["doi"] and rec["metadata"]["license"]["id"]=="cc-by-4.0" and rec["metadata"]["access_right"]=="open","live dataset identity/license")
        require(len(rec["files"])==1 and rec["files"][0]["key"]==m["filename"] and rec["files"][0]["checksum"]=="md5:"+m["md5"] and rec["files"][0]["size"]==m["zip_bytes"],"publisher file identity")
        raw=get("https://zenodo.org/records/14065933/files/source%20data.zip?download=1",5_000_000)
    files=audit(raw)
    if a.output:
        require(not a.output.exists(),"refuse overwrite")
        a.output.mkdir(parents=True)
        for name,b in files.items():
            dest=a.output/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(b)
    else:
        require({p.relative_to(a.staged).as_posix() for p in a.staged.rglob("*") if p.is_file()}==set(files),"exact staged set")
        for name,b in files.items(): require((a.staged/name).read_bytes()==b,"staged identity "+name)
    print(f"Verified Twente TFLN: 40 CSV files, {len(files)} archive files, {sum(map(len,files.values()))} bytes.")
if __name__=="__main__": main()
