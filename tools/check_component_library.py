"""Conservative v1 component registry validation, no network or simulation."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def local(path):
    require(isinstance(path,str) and path and not Path(path).is_absolute()
            and ".." not in Path(path).parts, "invalid local path")
    p=ROOT/path
    require(p.is_file() and p.resolve().is_relative_to(ROOT), "missing local evidence: "+path)

def https(url):
    require(isinstance(url,str) and url.startswith("https://") and len(url)>8, "invalid URL")

def main():
    data=json.loads((ROOT/"components/registry.json").read_text())
    require(data["schema_version"]==1,"schema")
    entries={}
    for e in data["components"]:
        ident=e["id"]
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",ident) and ident not in entries,"ID")
        entries[ident]=e
        require(e["cell"] and e["kind"] and e["notes"] and e["local_evidence"],"metadata")
        for p in e["local_evidence"]:
            local(p)
        require(e["measurement"] is None and e["qualification"] is None,"v1 does not certify exact cells")
        require(e["model"]["complex_s_parameters"]=="not_imported","v1 does not import S data")
        require(e["model"]["type"] in {"upstream_compact_model_candidate","placeholder","not_audited","pdk_sax_model_evaluated","mpb_fdtd_coupled_mode","nonlinear_state_and_receiver","ideal_behavioral_matrix"},"model type")
        if e["origin"]=="external":
            p=e["pdk"]
            require(all(p[k] for k in ("name","version","platform","license")),"PDK metadata")
            https(p["source"])
            local(p["lock"])
            require(e["redistribution"]=="reference_only" and e["evidence_scope"]=="layout_use","external scope")
        else:
            require(e["origin"]=="debatt_ai" and e["pdk"] is None and e["evidence_scope"]=="numerical_research" and e["redistribution"]=="repository_reference","original scope")
    require(entries and {e["origin"] for e in entries.values()}=={"external","debatt_ai"},"origin coverage")
    seen=set()
    for m in data["experimental_evidence"]:
        require(m["id"] in entries and entries[m["id"]]["origin"]=="external","measurement component")
        key=(m["id"],m["doi"])
        require(key not in seen and m["doi"].startswith("10.") and m["finding"],"measurement identity")
        seen.add(key)
        https(m["url"])
        local(m["local_link"])
        require(m["local_link"] in entries[m["id"]]["local_evidence"],"evidence link")
        require(m["scope"]=="published_design_family" and m["exact_pdk_revision_verified"] is False and m["raw_complex_s_available"] is False,"measurement scope")
    for lead in data["discovery_queue"]:
        require(lead["name"] and lead["status"]=="not_audited","lead")
        https(lead["url"])
    print(f"Validated {len(entries)} reference components, {len(seen)} published evidence links; no exact-cell qualification or imported S data.")

if __name__=="__main__":
    main()
