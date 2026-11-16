"""Webhook control test: one minimal plain-model interaction, no agent.

Answers one question: does this project receive interaction.completed
webhooks for an ordinary background model interaction? If it does while
Antigravity interactions stay silent, the gap is agent-specific.

One POST, never retried. Then at most POLLS GETs of the same interaction.
The interaction ID is sealed right after create in an encrypted checkpoint
(Fernet, key derived from the API key with a separate domain), so a later
retrieve run can check the status with GETs only, never a new submission.
Public logs get only fixed text, enum statuses, HTTP codes, UTC times,
the interaction SHA-256 (as the manager prints) and yes/no keyword flags.
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
API_REVISION = "2026-05-20"  # same header as the Antigravity manager
DYNAMIC_URI = "https://debatt-ai-open-photonic-lab-antigravity-webhook.xx8031126.workers.dev/gemini-dynamic"
INPUT = "Reply with the single word OK."
DEFAULT_MODEL = "gemini-3.8-flash"
POLLS, INTERVAL = 20, 15
ACTIVE = {"in_progress", "queued", "pending"}
KNOWN = ACTIVE | {"completed", "failed", "cancelled", "incomplete", "requires_action"}
CANONICAL = frozenset({
    "CANCELLED", "UNKNOWN", "INVALID_ARGUMENT", "DEADLINE_EXCEEDED", "NOT_FOUND",
    "ALREADY_EXISTS", "PERMISSION_DENIED", "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION",
    "ABORTED", "OUT_OF_RANGE", "UNIMPLEMENTED", "INTERNAL", "UNAVAILABLE",
    "DATA_LOSS", "UNAUTHENTICATED",
})
# Only whether the error text mentions these words is reported, never the text.
KEYWORDS = ("webhook", "uris", "background", "store", "model", "agent", "revision", "free tier", "billing")


class SafeError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def cipher(key):
    from cryptography.fernet import Fernet
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(
        b"debatt-ai-webhook-control-v1\0" + key.encode()).digest()))


def valid_id(ident):
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", ident):
        raise SafeError("Unexpected interaction ID format")
    return ident


def seal(key, record, path):
    valid_id(record.get("id"))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(cipher(key).encrypt(json.dumps(record).encode()))
    tmp.replace(path)


def unseal(key, path):
    if path.stat().st_size > 65536:
        raise SafeError("Checkpoint too large")
    try:
        record = json.loads(cipher(key).decrypt(path.read_bytes()))
    except Exception:
        raise SafeError("Checkpoint could not be decrypted with this API key") from None
    if not isinstance(record, dict) or record.get("kind") != "webhook-control":
        raise SafeError("Not a webhook control checkpoint")
    valid_id(record.get("id"))
    return record


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_model(model):
    if not re.fullmatch(r"gemini-[a-z0-9.-]{1,48}", model or "") or re.search(r"agent|antigravity|research", model):
        raise SafeError("Model must be a plain Gemini model ID, not an agent")
    return model


def build_payload(model, variant):
    payload = {"model": valid_model(model), "input": INPUT, "background": True, "store": True}
    if variant == "dynamic":
        payload["webhook_config"] = {"uris": [DYNAMIC_URI]}
    elif variant != "static":
        raise SafeError("Variant must be static or dynamic")
    return payload


def status_of(result):
    status = result.get("status") if isinstance(result, dict) else None
    return status if status in KNOWN else "other"


def error_summary(code, raw):
    """HTTP code, canonical status, error field names and keyword flags only."""
    http = str(code) if type(code) is int and 100 <= code <= 599 else "unknown"
    status, fields, flags = "unknown", [], {}
    try:
        if len(raw) <= 65536:
            body = json.loads(raw)
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict):
                if error.get("status") in CANONICAL:
                    status = error["status"]
                fields = sorted(k for k in error if isinstance(k, str) and re.fullmatch(r"[a-z_]{1,32}", k))[:10]
                text = json.dumps(error).lower()
            else:
                fields = sorted(k for k in body if isinstance(k, str) and re.fullmatch(r"[a-z_]{1,32}", k))[:10] if isinstance(body, dict) else []
                text = json.dumps(body).lower()
            flags = {word: word in text for word in KEYWORDS}
    except Exception:
        pass
    mentioned = sorted(w for w, hit in flags.items() if hit)
    return (f"Google API HTTP status: {http}; canonical status: {status}; "
            f"error fields: {fields}; error text mentions: {mentioned}")


def request(key, interaction_id=None, payload=None):
    url = ENDPOINT if interaction_id is None else ENDPOINT + "/" + interaction_id
    req = urllib.request.Request(
        url, data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key, "Api-Revision": API_REVISION},
        method="GET" if payload is None else "POST")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as response:
            raw = response.read(1_000_001)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(65537)
        except Exception:
            body = b""
        raise SafeError(error_summary(exc.code, body)) from None
    except Exception:
        raise SafeError("Request failed before an HTTP response") from None
    if len(raw) > 1_000_000:
        raise SafeError("Response too large")
    try:
        result = json.loads(raw)
    except Exception:
        raise SafeError("Response was not JSON") from None
    if not isinstance(result, dict):
        raise SafeError("Unexpected response")
    return result


def follow(key, ident, status, variant, call, sleep, clock):
    """At most POLLS GETs of the same interaction; never submits."""
    for _ in range(POLLS):
        if status not in ACTIVE:
            break
        sleep(INTERVAL)
        try:
            result = call(key, interaction_id=ident)
        except SafeError as exc:
            print(str(exc), flush=True)
            print("Polling stopped on first error; no retry.")
            return 1
        if result.get("id") != ident:
            print("Interaction mismatch; stopping.")
            return 1
        status = status_of(result)
    print(f"Final status: {status} at {clock()}")
    if status == "completed":
        expected = "dynamic_google_signature_observed on /gemini-dynamic" if variant == "dynamic" else \
                   "antigravity_verified_completion with the SHA256 above on /gemini"
        print("Now check Cloudflare Workers Logs for a POST from Google and " + expected + ".")
        return 0
    if status in ACTIVE:
        print("Still active after the polling limit; run retrieve with this run ID later.")
        return 0
    print("Interaction did not complete; only interaction.completed is subscribed, so no webhook is expected.")
    return 1


def run(key, model, variant, output, call=request, sleep=time.sleep, clock=utc):
    payload = build_payload(model, variant)
    if output.exists():
        raise SafeError("Output already exists")
    submitted = clock()
    print(f"Variant: {variant}; model: {payload['model']}; submitted at {submitted}", flush=True)
    try:
        result = call(key, payload=payload)
    except SafeError as exc:
        print(str(exc), flush=True)
        print("Create rejected; nothing to poll. Submission outcome not confirmed, no retry.")
        return 1
    try:
        ident = valid_id(result.get("id"))
    except SafeError:
        print("Unexpected interaction ID format; stopping.")
        return 1
    print("Interaction SHA256: " + hashlib.sha256(ident.encode()).hexdigest(), flush=True)
    seal(key, {"kind": "webhook-control", "id": ident, "variant": variant,
               "model": payload["model"], "submitted": submitted}, output)
    print("Encrypted checkpoint saved; retrieve later with this run ID.", flush=True)
    print("Webhook config echoed: " + str(isinstance(result.get("webhook_config"), dict)))
    status = status_of(result)
    print(f"Status at create: {status}", flush=True)
    return follow(key, ident, status, variant, call, sleep, clock)


def retrieve(key, prior, call=request, sleep=time.sleep, clock=utc):
    record = unseal(key, prior)
    ident = record["id"]
    print("Interaction SHA256: " + hashlib.sha256(ident.encode()).hexdigest())
    print(f"Variant: {record.get('variant') if record.get('variant') in ('static', 'dynamic') else 'unknown'}; "
          f"submitted at {record.get('submitted') if re.fullmatch(r'[0-9TZ:-]{20}', str(record.get('submitted'))) else 'unknown'}")
    try:
        result = call(key, interaction_id=ident)
    except SafeError as exc:
        print(str(exc), flush=True)
        print("Retrieve failed; no retry.")
        return 1
    if result.get("id") != ident:
        print("Interaction mismatch; stopping.")
        return 1
    status = status_of(result)
    print(f"Status at retrieve: {status} at {clock()}", flush=True)
    return follow(key, ident, status, record.get("variant"), call, sleep, clock)


def main():
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SafeError("First attempt on main required")
    if os.environ.get("CONFIRM_FREE_PROJECT") != "true":
        raise SafeError("Free project confirmation required")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SafeError("Missing API key")
    variant = os.environ.get("CONTROL_VARIANT")
    if variant == "retrieve":
        return retrieve(key, Path(os.environ["CONTROL_PRIOR"]))
    if os.environ.get("CONFIRM_CONTROL_CALL") != "true":
        raise SafeError("Control call confirmation required for a new submission")
    return run(key, os.environ.get("CONTROL_MODEL") or DEFAULT_MODEL, variant, Path(os.environ["CONTROL_OUTPUT"]))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SafeError as exc:
        print(str(exc))
        sys.exit(1)
    except Exception:
        print("Control test failed; no automatic retry.")
        sys.exit(1)
