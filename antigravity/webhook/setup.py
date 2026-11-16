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

def request(url, headers, method="GET", body=None):
    req = urllib.request.Request(url, headers={**headers, "Content-Type": "application/json"},
                                 method=method, data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return json.loads(response.read(1048577))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Remote HTTP status {exc.code}") from None
    except Exception:
        raise RuntimeError("Remote request or JSON decoding failed") from None

def setup(call, google_headers, cf_headers, account, mode):
    if not re.fullmatch(r"[a-f0-9]{32}", account):
        raise ValueError("Invalid Cloudflare account ID")
    cf = f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/{NAME}/secrets"
    existing = call(GOOGLE, google_headers)
    if not isinstance(existing, dict) or not isinstance(existing.get("webhooks", []), list):
        raise RuntimeError("Unexpected Google list response")
    if existing.get("next_page_token") or existing.get("nextPageToken"):
        raise RuntimeError("Paginated list: inspect manually before creating")
    matches = [w for w in existing.get("webhooks", []) if w.get("uri") == URI or w.get("name") == NAME]
    print(f"Matching Google registrations: {len(matches)}")
    if mode == "inspect":
        return
    if matches:
        raise RuntimeError("Registration already exists; do not create duplicates. Recover via secret rotation manually.")
    current = call(cf, cf_headers)
    if current.get("success") is not True or not isinstance(current.get("result"), list):
        raise RuntimeError("Cloudflare secret preflight failed")
    names = {s.get("name") for s in current["result"]}
    if "GITHUB_TOKEN" not in names or "WEBHOOK_SIGNING_SECRET" in names:
        raise RuntimeError("Expected GitHub token and no existing signing secret")
    created = call(GOOGLE, google_headers, "POST", {"name": NAME, "uri": URI, "subscribed_events": EVENTS})
    secret = created.get("new_signing_secret", "")
    try:
        if not isinstance(secret, str) or not secret.startswith("whsec_") or len(base64.b64decode(secret[6:], validate=True)) < 16:
            raise ValueError()
    except Exception:
        raise RuntimeError("Google registration may exist; unexpected signing secret format. Recover manually.") from None
    print("::add-mask::" + secret, flush=True)
    result = call(cf, cf_headers, "PUT", {"name": "WEBHOOK_SIGNING_SECRET", "text": secret, "type": "secret_text"})
    if result.get("success") is not True:
        raise RuntimeError("Cloudflare secret write failed; Google registration may exist. Recover manually.")
    print("Signing secret transferred to Cloudflare. Retrieval remains disabled.")

def main():
    mode = os.environ.get("SETUP_MODE")
    if mode not in ("inspect", "create") or os.environ.get("CONFIRM_FREE_PROJECT") != "true":
        raise RuntimeError("Explicit free project confirmation required")
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("Only first attempt on main is allowed")
    google = os.environ["GEMINI_API_KEY"]
    cf = os.environ.get("CF_WEBHOOK_SETUP_TOKEN", "")
    if not google or (mode == "create" and not cf):
        raise RuntimeError("Required credentials missing")
    setup(request, {"x-goog-api-key": google}, {"Authorization": "Bearer " + cf},
          os.environ["CF_ACCOUNT_ID"], mode)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No tracebacks or arbitrary remote values in public logs.
        print("Setup failed. Inspect registration state before any new create attempt.")
        raise SystemExit(1)
