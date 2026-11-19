"""Verify exact NL021 ZIP and CI-emitted science hashes; archive without execution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

RUN=44504831351
ARTIFACT=14519955758
ZIP_SHA="b728cc934b003e44dd6ccfa3543e0ca16aa3f382b8bd370ad2a91b427df80a69"
ZIP_SIZE=326958
EXPECTED={
    "coefficient_summary.csv":(2065,"3b1c43afad927114332afa85dc3d0ed213def2f69a22c690c2ec5944ad0eccd8"),
    "coefficients.json":(81475,"979a67c10517f4939d39b1dd282bbdd8993b3610d42fb4109d2fc19e25fa18e1"),
    "common_drive_pairs.csv":(3511,"cd405a8875191cf5cba731e9d04aa8b780eabd29cb633532445fbe6227a57afc"),
    "convergence.csv":(867,"8bf5a6f0a80a468727f66f165f60c3ca7c69cc1eb0279cb90f3d63c44d347c51"),
    "environment-lock.txt":(9532,"a413f375d4a3097d7cb7c9922da7288e15ad77026afdcb11d8f6945375ee8c4c"),
    "installed-packages.json":(68543,"f8bf20346f3dcd14fac94e7b91949ca983197c352d906a00e6b8152b0acf60f6"),
    "metrics.csv":(256567,"d1b4b064d315b351c858058b9d1ca0595b549c32fb2d2636911e87140829d614"),
    "nl020_seed_analysis.json":(341004,"70687e637bb5dc6e0a6a2322b7ad4d945dc435a3c423fa97b18d9df723a6e2fc"),
    "optical_audit.csv":(951,"49f3fcc86a8a12e76cee59bd5134979a07a4e583ba19114bee78a69327ff56b2"),
    "paired_readouts.csv":(1073233,"a8e892f0ed534120759a81100f4070f30f14d6b91cf0651fbc06c6376adb4dcf"),
    "paired_summary.csv":(22846,"db273cb1e5a28385a4c0e7eda47c4075312c6b72eb07ea2bbbaf2cf37f80db63"),
    "resolution_groups.csv":(30948,"3540621d74db2c561725bec9418c05ced4e6565a4c52b423a87a683acc4457be"),
    "resolution_metrics.csv":(766755,"5e1c76624c93583adc89d355141a755daade521642093da4bc06a65043b0ec69"),
    "result.json":(41009,"a5c4354a9f7186340575f9325558e74ed007f89d6a4282b04a04931877b70c4e"),
    "summary.csv":(13402,"6acde04f4352f38b7ddd37998303088f9514a1bb9fc6c5eefcc25dca3d04b1ab"),
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
    fields=("lo_mw","readout","combined_worst_A_low","combined_worst_A_high","combined_worst_B_low","combined_worst_B_high")
    expected=[
        (2,"end",0.890625,0.990234375,0.89599609375,0.98974609375,"FAIL"),
        (2,"eighth_mean",0.92236328125,0.97021484375,0.92138671875,0.97021484375,"FAIL"),
        (2,"quarter_mean",0.9208984375,0.89501953125,0.91259765625,0.89453125,"FAIL"),
        (2,"half_mean",0.83154296875,0.71044921875,0.8203125,0.6982421875,"FAIL"),
        (2,"frozen_fresh_ridge16",0.95703125,0.99462890625,0.9521484375,0.99560546875,"FAIL"),
        (2,"frozen_margin16_low",0.9599609375,0.99951171875,0.96630859375,0.99951171875,"FAIL"),
        (2,"frozen_nl020_margin16_low",0.95947265625,0.9990234375,0.96533203125,0.99853515625,"FAIL"),
        (2,"frozen_nl020_robust16_softmax",0.96044921875,0.9990234375,0.96484375,0.9990234375,"PASS"),
        (2,"frozen_nl020_robust16_repeat",0.9599609375,0.9990234375,0.96484375,0.9990234375,"FAIL"),
        (3,"end",0.8935546875,0.990234375,0.8984375,0.990234375,"FAIL"),
        (3,"eighth_mean",0.9228515625,0.970703125,0.92236328125,0.97119140625,"FAIL"),
        (3,"quarter_mean",0.92138671875,0.89501953125,0.91357421875,0.89404296875,"FAIL"),
        (3,"half_mean",0.8310546875,0.71044921875,0.8212890625,0.697265625,"FAIL"),
        (3,"frozen_fresh_ridge16",0.9580078125,0.9951171875,0.953125,0.99609375,"FAIL"),
        (3,"frozen_margin16_low",0.9619140625,0.99951171875,0.96630859375,0.99951171875,"PASS"),
        (3,"frozen_nl020_margin16_low",0.96044921875,0.9990234375,0.96630859375,0.99853515625,"PASS"),
        (3,"frozen_nl020_robust16_softmax",0.96044921875,0.9990234375,0.96533203125,0.9990234375,"PASS"),
        (3,"frozen_nl020_robust16_repeat",0.96044921875,0.9990234375,0.9658203125,0.9990234375,"PASS"),
    ]
    pairs=report["all_common_drive_pairs"]
    if (report["experiment"]!="OPA-NL-021" or len(report["checks"])!=27
        or not all(v is True for v in report["checks"].values()) or report["failures"]
        or report["rows"]!=360 or report["groups"]!=72 or report["resolution_groups"]!=216
        or report["combined_passing_groups"]!=48 or report["ambiguous_groups"]!=0
        or report["robustness_ambiguous_groups"]!=0
        or [tuple(p[k] for k in fields)+("PASS" if p["robustness_target_met"] else "FAIL",) for p in pairs]!=expected
        or report["primary_endpoint"]!=next(p for p in pairs if p["lo_mw"]==3 and p["readout"]=="frozen_margin16_low")
        or report["secondary_endpoint"]!=next(p for p in pairs if p["lo_mw"]==2 and p["readout"]=="frozen_margin16_low")
        or report["primary_passed"] is not True or report["secondary_passed"] is not False
        or report["independent_confirmation_passed"] is not True
        or report["confirmed_cadence_gsymbol_s"]!=1000/42
        or report["calibration_domains"]!=[]
        or report["test_domains"]!={"A":list(range(10904,10909)),"B":list(range(10914,10919))}
        or len(report["convergence"])!=4
        or any(p["changed_group_gates"] or p["changed_seed_gates"] for p in report["convergence"])):
        raise ValueError("unexpected report")
    if json.loads(files["nl020_seed_analysis.json"])["verified"] is not True:
        raise ValueError("prior audit failed")


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
    return (json.dumps(dict(experiment="OPA-NL-021",workflow_run_id=RUN,
        job_id=135493790044,artifact_id=ARTIFACT,artifact_sha256=ZIP_SHA,
        artifact_bytes=ZIP_SIZE,head_sha="ad5ccd6e849715de19a74d9338bf44d506f51cc3",
        merge_sha="651b180df79959428df3f1e92254f9b182f0e523",pull_request=207,
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
    print("Verified exact NL021 evidence and provenance.")

if __name__=="__main__":
    main()
