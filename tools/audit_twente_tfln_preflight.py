"""Read-only acquisition audit. Never publish source data or execute downloaded code."""
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parents[1] / "components/experimentally_validated/Twente-TFLN-Wei-2025"
OUT = Path("results/opa-lib004-tfln-preflight")
def require(ok, message):
    if not ok:
        raise ValueError(message)
def get(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent":"Debatt-AI Open Photonic Lab research metadata audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit+1)
    require(len(data)<=limit, "download size bound")
    return data
def main():
    m=json.loads((BASE/"manifest.json").read_text())
    record=json.loads(get("https://zenodo.org/api/records/14065933",2_000_000))
    require(str(record["id"])=="14065933" and record["doi"]==m["doi"],"record identity")
    require(record["metadata"]["access_right"]=="open","record not public")
    files=record["files"]
    require(len(files)==1 and files[0]["key"]==m["filename"],"file inventory")
    f=files[0]
    require(f["checksum"]=="md5:"+m["md5"],"publisher checksum")
    raw=get("https://zenodo.org/records/14065933/files/source%20data.zip?download=1",5_000_000)
    require(len(raw)==f["size"] and hashlib.md5(raw).hexdigest()==m["md5"],"original zip identity")
    inventory=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist()
        require(len(entries)<200 and sum(i.file_size for i in entries)<30_000_000,"archive bounds")
        names=[i.filename for i in entries]
        require(len(set(names))==len(names),"duplicate names")
        for i in entries:
            p=PurePosixPath(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in i.filename and not stat.S_ISLNK(i.external_attr>>16),"unsafe ZIP path")
        require(z.testzip() is None,"ZIP CRC")
        actual={i.filename for i in entries if not i.is_dir()}
        expected=set(m["expected_csv_paths"])
        # A preview is not an authoritative manifest: record differences explicitly,
        # never silently admit unexpected files or assume figure-to-column mapping.
        for i in entries:
            if i.is_dir(): continue
            b=z.read(i)
            info={"path":i.filename,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
            if i.filename.lower().endswith(".csv"):
                try:
                    decoded=b.decode("utf-8-sig")
                    reader=csv.reader(io.StringIO(decoded))
                    counts={}
                    for row in reader:
                        counts[str(len(row))]=counts.get(str(len(row)),0)+1
                    info["row_width_counts"]=counts
                except (UnicodeError,csv.Error):
                    info["csv_parse_status"]="manual_review_required"
            inventory.append(info)
    report={"experiment":m["experiment"],"record":record["id"],"doi":record["doi"],
            "metadata_license":record["metadata"].get("license"),
            "metadata_rights":record["metadata"].get("rights"),
            "zip_bytes":len(raw),"zip_sha256":hashlib.sha256(raw).hexdigest(),
            "zip_md5":hashlib.md5(raw).hexdigest(),"inventory":inventory,
            "missing_preview_paths":sorted(expected-actual),"unexpected_paths":sorted(actual-expected),
            "redistribution":"blocked_pending_manual_rights_and_schema_review",
            "measurement_values_published":False,"complex_s":None,"geometry_match":None}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"inventory.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
