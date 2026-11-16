"""Submit once or retrieve an existing interaction; never retry POST."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
import urllib.error
import resume

ENDPOINT = resume.photonic.probe.ENDPOINT
ACTIVE = {"in_progress", "queued", "pending"}
def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", value):
        raise ValueError("Invalid interaction ID")
    return value

def request(key, interaction_id=None, payload=None):
    url = ENDPOINT if interaction_id is None else ENDPOINT + "/" + valid_id(interaction_id)
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key,
                 "Api-Revision": "2026-05-20"}, method="GET" if payload is None else "POST")
    with urllib.request.build_opener(resume.photonic.probe.NoRedirect()).open(req, timeout=60) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError("Response too large")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Invalid response")
    return result

def save(directory, result):
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / "latest.tmp"
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    tmp.replace(directory / "latest.json")

def execute(key, directory, *, payload=None, interaction_id=None, polls=30):
    if (payload is None) == (interaction_id is None):
        raise ValueError("Choose exactly one operation")
    result = request(key, interaction_id, payload)
    save(directory, result)
    actual_id = valid_id(result.get("id"))
    if interaction_id is not None and actual_id != interaction_id:
        raise ValueError("Interaction ID mismatch")
    for i in range(polls + 1):
        status = result.get("status")
        if status == "completed":
            print("Interaction completed; scientific validation still required.")
            return 0
        if status not in ACTIVE:
            print("Interaction stopped or returned unknown status; inspect artifact.")
            return 1
        if i == polls:
            print("Still active; retrieve using saved interaction ID. Do not resubmit.")
            return 0
        print("Interaction active; waiting 60 seconds.", flush=True)
        time.sleep(60)
        result = request(key, actual_id)
        if result.get("id") != actual_id:
            raise ValueError("Interaction ID mismatch")
        save(directory, result)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["resume", "retrieve"], required=True)
    parser.add_argument("--token-budget", type=int, default=200000)
    parser.add_argument("--confirm-free-project", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = None
        interaction_id = None
        if args.mode == "resume":
            payload = dict(resume.build_payload(os.getenv("AG_PREVIOUS_INTERACTION_ID"),
                os.getenv("AG_ENVIRONMENT_ID"), args.token_budget), background=True, store=True)
        else:
            interaction_id = valid_id(os.getenv("AG_RETRIEVE_INTERACTION_ID"))
        if not args.live:
            print("Offline validation only.")
            return 0
        if not args.confirm_free_project or not os.getenv("GEMINI_API_KEY"):
            parser.error("Verified billing-disabled project and API key required")
        return execute(os.environ["GEMINI_API_KEY"], Path(__file__).resolve().parents[2] / "results" / "background",
                       payload=payload, interaction_id=interaction_id)
    except (OSError, ValueError) as exc:
        print(f"Request stopped ({type(exc).__name__}); inspect saved artifact. No POST retry.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
