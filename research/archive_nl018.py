"""Verify exact NL018 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44387159815
ARTIFACT=14467183137
ZIP_SHA="5056ec8c3e7ffb398184c320b653ca4c4c200510fac76c58d9eb8f2f2ec9276d"
ZIP_SIZE=344108
EXPECTED={
    "coefficient_summary.csv":(2696,"7c9979feb3abb99af470914d721850f1eeec21ba81f8d76b1e3f6f67d62e9901"),
    "coefficients.json":(22153,"1674b429446175292546456eb83236673af2307809746580f654d32aabf2d84c"),
    "common_drive_pairs.csv":(3649,"dc2b77b64b329beab2b3a1d8e2968b65102d28fcea8b4b931c7f7b84b4856aeb"),
    "convergence.csv":(1626,"177556e7f22991879d34e099e167088dc4dae73a543824d47cdf883005f9b601"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(318377,"3507b736c3f534409edf9b4757fff974ca981dfb09cddfe0ef1108e64cb93f5a"),
    "nl017_seed_analysis.json":(225277,"ed069debdcae76cf591fd832abe0986e445213650ba4b6df3c5ce84ccd63fc29"),
    "optical_audit.csv":(1842,"7deb43df5c16eee3eb1ed5a773190a0d9c6b1ec73f938f85b8fbb8aaa4375ad8"),
    "paired_readouts.csv":(912822,"cb58f72b8bceeaa2a61fa2b789abf7bcc5036ccdc02f751f777f48e128f61cff"),
    "paired_summary.csv":(17818,"6082c55edeab1715a970758a77f9bf526752b34b34cd5643887dba18a3cf99fa"),
    "resolution_groups.csv":(41767,"2a1d03c7bdf350c14a90f927992c541d415eff1447e98131e3ed5f0e8732aef4"),
    "resolution_metrics.csv":(952291,"258ba5fbd87b9128f71913bf3b58c98b16073bb1ac0ef60fe67c29e27551d483"),
    "result.json":(43017,"1dbc768e80d155d284f92b895d4bb6ef2afc25b94a5094cef1ca284dbda5a1d7"),
    "summary.csv":(17489,"fcd81d69a14426f456f844461d2a144260fa8d1889e9d2bbd1d1c29a9033c4ba"),
}
NAMES=set(EXPECTED)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_science(files):
    if set(files)!=NAMES:
        raise ValueError("unexpected evidence names")
    for name,(size,digest) in EXPECTED.items():
        if (len(files[name]),sha(files[name]))!=(size,digest):
            raise ValueError("CI science hash mismatch: "+name)
    report=json.loads(files["result.json"])
    primary=report["primary_endpoint"]
    controls=report["positive_controls"]
    if (report["experiment"]!="OPA-NL-018" or len(report["checks"])!=27
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=480 or report["groups"]!=96
        or report["resolution_groups"]!=288
        or report["combined_passing_groups"]!=36 or report["ambiguous_groups"]!=0
        or report["common_two_panel_passes"]!=[]
        or len(report["all_common_drive_pairs"])!=24
        or any(p["passes_both_drives_both_panels"] for p in report["all_common_drive_pairs"])
        or report["primary_passed"] is not False or report["control_passed"] is not False
        or report["independent_confirmation_passed"] is not False
        or report["confirmed_cadence_gsymbol_s"]!=1000/42
        or (primary["on_ps"],primary["lo_mw"],primary["fc_ghz"],primary["readout"])!=(41,3.,80,"frozen_ridge16_midlow")
        or tuple(primary["combined_worst_"+k] for k in ("A_low","A_high","B_low","B_high"))!=(.94677734375,.9921875,.94189453125,.99560546875)
        or tuple(primary["passed_"+k] for k in ("A_low","A_high","B_low","B_high"))!=(False,True,False,True)
        or len(controls)!=2
        or [(p["on_ps"],p["lo_mw"],p["fc_ghz"],p["readout"],p["combined_worst_B_low"]) for p in controls]!=[(42,2.,120,"ridge16",.947265625),(42,3.,120,"ridge16",.9482421875)]
        or any(tuple(p["passed_"+k] for k in ("A_low","A_high","B_low","B_high"))!=(True,True,False,True) for p in controls)
        or len(report["supporting_endpoints"])!=5
        or any(p["passes_both_drives_both_panels"] for p in report["supporting_endpoints"])
        or len(report["matched_history_comparisons"])!=12 or len(report["matched_recalibration_comparisons"])!=8
        or len(report["matched_regularization_comparisons"])!=4
        or len(report["convergence"])!=8
        or any(p["changed_group_gates"] or p["changed_seed_gates"] for p in report["convergence"])):
        raise ValueError("unexpected report")

def read_zip(path):
    raw=path.read_bytes()
    if len(raw)!=ZIP_SIZE or sha(raw)!=ZIP_SHA:
        raise ValueError("ZIP identity mismatch")
    with zipfile.ZipFile(path) as z:
        info=z.infolist()
        if len(info)!=len(NAMES) or {i.filename for i in info}!=NAMES:
            raise ValueError("unexpected ZIP entries")
        if any(i.is_dir() or stat.S_ISLNK(i.external_attr>>16) or i.file_size!=EXPECTED[i.filename][0] for i in info):
            raise ValueError("invalid ZIP entry")
        if z.testzip() is not None:
            raise ValueError("CRC failure")
        files={i.filename:z.read(i) for i in info}
    verify_science(files)
    return files

def manifest(files):
    return (json.dumps(dict(experiment="OPA-NL-018",workflow_run_id=RUN,
        job_id=135094871000,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="3695dcc663f08fe6a7d04def6735b383fe2aab06",
        merge_sha="4ca87bc2fef0e2f0fe600513d8bf8ce11186fd80",pull_request=195,
        verification="Raw ZIP pinned to GitHub metadata; CRC and all fifteen file hashes pinned to CI stdout; staged bytes compared to verified ZIP.",
        files={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()}),
        indent=2,sort_keys=True)+"\n").encode()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",required=True,type=Path)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--output",type=Path)
    g.add_argument("--staged",type=Path)
    a=p.parse_args()
    files=read_zip(a.zip)
    files["provenance.json"]=manifest(files)
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        for name,b in files.items():
            (a.output/name).write_bytes(b)
    else:
        if {p.name for p in a.staged.iterdir()}!=set(files):
            raise ValueError("staged names mismatch")
        for name,b in files.items():
            if (a.staged/name).read_bytes()!=b:
                raise ValueError("staged bytes mismatch: "+name)
    for name,b in sorted(files.items()):
        print(name,len(b),sha(b))
    print("Verified exact NL018 evidence and provenance.")

if __name__=="__main__":
    main()
