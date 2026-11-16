"""One request per invocation; encrypted checkpoints for a public repository."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent / "experiments/AG-PHOTONIC-001"))
import background
from cryptography.fernet import Fernet

DYNAMIC_URI = "https://debatt-ai-open-photonic-lab-antigravity-webhook.xx8031126.workers.dev/gemini-dynamic"

EXPERIMENTS = {
    "AG-INFRA-001": background.resume.photonic.probe.PAYLOAD,
    "AG-PHOTONIC-001": background.resume.photonic.PAYLOAD,
    "AG-PHOTONIC-002": dict(background.resume.photonic.PAYLOAD, input=(Path(__file__).resolve().parent / "experiments/AG-PHOTONIC-002/prompt.txt").read_text()),
    "AG-PHOTONIC-003": dict(background.resume.photonic.PAYLOAD, input=(Path(__file__).resolve().parent / "experiments/AG-PHOTONIC-003/prompt.txt").read_text()),
}

def cipher(key):
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(
        b"debatt-ai-antigravity-checkpoint-v1\0" + key.encode()).digest()))

def seal(key, experiment, result, path):
    background.valid_id(result.get("id"))
    data = json.dumps({"experiment": experiment, "response": result}).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(cipher(key).encrypt(data))
    tmp.replace(path)

def load(key, experiment, path):
    if path.stat().st_size > 8_000_000:
        raise ValueError("Checkpoint too large")
    data = json.loads(cipher(key).decrypt(path.read_bytes()))
    if data["experiment"] != experiment:
        raise ValueError("Experiment mismatch")
    background.valid_id(data["response"].get("id"))
    return data["response"]

def execute(key, experiment, mode, output, prior=None, legacy_id=None,
            budget=20_000, allow_submit=False, dynamic_webhook=False):
    if dynamic_webhook and (mode != "start" or experiment != "AG-INFRA-001" or budget != 20_000):
        raise ValueError("Dynamic webhook restricted to 20k infrastructure start")
    if experiment not in EXPERIMENTS or not 20_000 <= budget <= 200_000:
        raise ValueError("Invalid experiment or budget")
    if output.exists():
        raise ValueError("Output already exists")
    if mode == "start":
        if not allow_submit or prior is not None or legacy_id:
            raise ValueError("Explicit new submission required")
        payload = dict(EXPERIMENTS[experiment], background=True, store=True)
        payload["agent_config"] = dict(payload["agent_config"], max_total_tokens=budget)
        if dynamic_webhook:
            payload["webhook_config"] = {"uris": [DYNAMIC_URI]}
            print("Dynamic webhook diagnostic enabled.")
        result = background.request(key, payload=payload)
    elif mode in ("retrieve", "import"):
        if mode == "retrieve":
            if prior is None:
                raise ValueError("Prior checkpoint required")
            ident = load(key, experiment, prior)["id"]
        else:
            if experiment != "AG-PHOTONIC-001" or prior is not None:
                raise ValueError("Legacy import is restricted to the coupler")
            ident = background.valid_id(legacy_id)
        result = background.request(key, interaction_id=ident)
        if result.get("id") != ident:
            raise ValueError("Interaction mismatch")
    else:
        raise ValueError("Unknown operation")
    seal(key, experiment, result, output)
    if mode == "start":
        print("Interaction SHA256: " + hashlib.sha256(result["id"].encode()).hexdigest())
    status = result.get("status")
    if status == "completed":
        print("Completed; scientific validation still required.")
        return 0
    if status in background.ACTIVE:
        print("Active; retrieve from this run's encrypted checkpoint.")
        return 0
    print("Stopped or unknown status; encrypted response preserved.")
    return 1

# Only fixed enum values and bounded integer HTTP codes may reach public logs.
GOOGLE_ERROR_STATUSES = frozenset({
    "CANCELLED", "UNKNOWN", "INVALID_ARGUMENT", "DEADLINE_EXCEEDED",
    "NOT_FOUND", "ALREADY_EXISTS", "PERMISSION_DENIED", "RESOURCE_EXHAUSTED",
    "FAILED_PRECONDITION", "ABORTED", "OUT_OF_RANGE", "UNIMPLEMENTED",
    "INTERNAL", "UNAVAILABLE", "DATA_LOSS", "UNAUTHENTICATED",
})

def safe_http_error(exc):
    code = exc.code
    http = str(code) if type(code) is int and 100 <= code <= 599 else "unknown"
    status = "unknown"
    try:
        raw = exc.read(65537)
        if len(raw) <= 65536:
            error = json.loads(raw).get("error", {})
            candidate = error.get("status")
            if isinstance(candidate, str) and candidate in GOOGLE_ERROR_STATUSES:
                status = candidate
    except Exception:
        pass
    finally:
        try:
            exc.close()
        except Exception:
            pass
    return f"Google API HTTP status: {http}; canonical status: {status}"

def poll_existing(key, experiment, output, *, sleep=time.sleep):
    """At most 12 GETs, five minutes apart; never submit or change interaction."""
    result = load(key, experiment, output)
    ident = result["id"]
    for _ in range(12):
        if result.get("status") not in background.ACTIVE:
            break
        sleep(300)
        candidate = background.request(key, interaction_id=ident)
        if candidate.get("id") != ident:
            raise ValueError("Interaction mismatch")
        seal(key, experiment, candidate, output)
        result = candidate
    if result.get("status") == "completed":
        print("Polling completed; scientific validation still required.")
        return 0
    if result.get("status") in background.ACTIVE:
        print("Polling limit reached; checkpoint preserved. Retrieve later.")
        return 0
    print("Polling stopped; encrypted response preserved.")
    return 1

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--experiment", choices=EXPERIMENTS, required=True)
    p.add_argument("--mode", choices=["start", "retrieve", "import"], required=True)
    p.add_argument("--budget", type=int, default=20_000)
    p.add_argument("--prior", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--confirm-free-project", action="store_true")
    p.add_argument("--allow-submit", action="store_true")
    p.add_argument("--dynamic-webhook", action="store_true")
    p.add_argument("--poll", action="store_true")
    a = p.parse_args()
    key = os.getenv("GEMINI_API_KEY")
    if not key or not a.confirm_free_project:
        p.error("Verified billing-disabled project and API key required")
    try:
        if a.poll and (a.mode not in ("start", "retrieve") or a.dynamic_webhook):
            raise ValueError("Polling requires start or retrieve without dynamic webhook")
        code = execute(key, a.experiment, a.mode, a.output, a.prior,
                       os.getenv("AG_RETRIEVE_INTERACTION_ID") if a.mode == "import" else None,
                       a.budget, a.allow_submit, a.dynamic_webhook)
        if a.poll and code == 0:
            return poll_existing(key, a.experiment, a.output)
        return code
    except urllib.error.HTTPError as exc:
        print(safe_http_error(exc), file=sys.stderr)
        print("Request failed; submission outcome not confirmed. No automatic retry.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Stopped ({type(exc).__name__}); no automatic retry.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
