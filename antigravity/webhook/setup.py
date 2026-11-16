"""Manual static webhook setup. Never log remote response bodies."""
import base64
import json
import os
import re
import urllib.request
import urllib.error

NAME = "debatt-ai-open-photonic-lab-antigravity-webhook"
URI = "https://" + NAME + ".xx8031126.workers.dev/gemini"
GOOGLE = "https://generativelanguage.googleapis.com/v1beta/webhooks"
EVENTS = ["interaction.completed"]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

class SafeError(RuntimeError):
    pass

def request(url, headers, method="GET", body=None):
    req = urllib.request.Request(url, headers={**headers, "Content-Type": "application/json"},
                                 method=method, data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return json.loads(response.read(1048577))
    except urllib.error.HTTPError as exc:
        raise SafeError(f"Remote HTTP status {exc.code}") from None
    except Exception:
        raise SafeError("Remote request or JSON decoding failed") from None

def stage(call, label, *args):
    print("Stage: " + label, flush=True)
    try:
        result = call(*args)
    except SafeError as exc:
        # Only request() constructs SafeError from fixed text and numeric status.
        print(str(exc), flush=True)
        raise
    print("Response received: " + label, flush=True)
    return result

def setup(call, google_headers, cf_headers, account, mode):
    if not re.fullmatch(r"[a-f0-9]{32}", account):
        raise ValueError("Invalid Cloudflare account ID")
    cf = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{NAME}/secrets"
    existing = stage(call, "Google list", GOOGLE, google_headers)
    if not isinstance(existing, dict) or not isinstance(existing.get("webhooks", []), list):
        raise SafeError("Unexpected Google list response")
    if existing.get("next_page_token") or existing.get("nextPageToken"):
        raise SafeError("Paginated list: inspect manually before creating")
    matches = [w for w in existing.get("webhooks", []) if w.get("uri") == URI or w.get("name") == NAME]
    print(f"Matching Google registrations: {len(matches)}")
    if mode == "inspect":
        return
    if mode == "create" and matches:
        raise SafeError("Registration already exists; do not create duplicates. Recover via secret rotation manually.")
    current = stage(call, "Cloudflare list secrets", cf, cf_headers)
    if current.get("success") is not True or not isinstance(current.get("result"), list):
        raise SafeError("Cloudflare secret preflight failed")
    names = {s.get("name") for s in current["result"]}
    print("GitHub token present: " + str("GITHUB_TOKEN" in names))
    print("Signing secret present: " + str("WEBHOOK_SIGNING_SECRET" in names))
    if mode == "diagnose":
        return
    if "GITHUB_TOKEN" not in names or "WEBHOOK_SIGNING_SECRET" in names:
        raise SafeError("Expected GitHub token and no existing signing secret")
    created = stage(call, "Google create", GOOGLE, google_headers, "POST", {"name": NAME, "uri": URI, "subscribed_events": EVENTS})
    secret = created.get("new_signing_secret", "")
    try:
        if not isinstance(secret, str) or not secret.startswith("whsec_") or len(base64.b64decode(secret[6:], validate=True)) < 16:
            raise ValueError()
    except Exception:
        raise SafeError("Google registration may exist; unexpected signing secret format. Recover manually.") from None
    print("::add-mask::" + secret, flush=True)
    result = stage(call, "Cloudflare write secret", cf, cf_headers, "PUT", {"name": "WEBHOOK_SIGNING_SECRET", "text": secret, "type": "secret_text"})
    if result.get("success") is not True:
        raise SafeError("Cloudflare secret write failed; Google registration may exist. Recover manually.")
    print("Signing secret transferred to Cloudflare. Retrieval remains disabled.")

def main():
    mode = os.environ.get("SETUP_MODE")
    if mode not in ("inspect", "diagnose", "create") or os.environ.get("CONFIRM_FREE_PROJECT") != "true":
        raise SafeError("Explicit free project confirmation required")
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise SafeError("Only first attempt on main is allowed")
    google = os.environ["GEMINI_API_KEY"]
    cf = os.environ.get("CF_WEBHOOK_SETUP_TOKEN", "")
    if not google or (mode != "inspect" and not cf):
        raise SafeError("Required credentials missing")
    setup(request, {"x-goog-api-key": google}, {"Authorization": "Bearer " + cf},
          os.environ["CF_ACCOUNT_ID"], mode)

if __name__ == "__main__":
    try:
        main()
    except SafeError as exc:
        print(str(exc), flush=True)
        print("Setup failed. Inspect registration state before any new create attempt.")
        raise SystemExit(1)
    except Exception:
        # No tracebacks or arbitrary remote values in public logs.
        print("Setup failed. Inspect registration state before any new create attempt.")
        raise SystemExit(1)
