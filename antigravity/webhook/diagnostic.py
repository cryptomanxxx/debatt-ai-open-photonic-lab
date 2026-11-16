"""Read-only registration checks and optional Google-originated ping."""
import json
import os
import re
import urllib.request
import urllib.error
from setup import NAME, URI, GOOGLE, EVENTS, NoRedirect, SafeError, request

def inspect(call, headers):
    listing = call(GOOGLE, headers)
    if not isinstance(listing, dict) or not isinstance(listing.get("webhooks"), list):
        raise SafeError("Unexpected webhook list")
    if listing.get("next_page_token") or listing.get("nextPageToken"):
        raise SafeError("Paginated list; stop")
    matches = [w for w in listing["webhooks"] if isinstance(w, dict)
               and (w.get("name") == NAME or w.get("uri") == URI)]
    print("Matching registrations:", len(matches))
    if len(matches) != 1:
        raise SafeError("Expected exactly one registration")
    ident = matches[0].get("id")
    if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", ident):
        raise SafeError("Unexpected webhook ID format")
    url = GOOGLE + "/" + ident
    detail = call(url, headers)
    if not isinstance(detail, dict):
        raise SafeError("Unexpected webhook detail")
    state = detail.get("state")
    print("State:", state if state in ("enabled", "disabled", "disabled_due_to_failed_deliveries") else "unknown")
    print("Name matches:", detail.get("name") == NAME)
    print("URI matches:", detail.get("uri") == URI)
    print("Completion subscription matches:", detail.get("subscribed_events") == EVENTS)
    if detail.get("id") != ident or detail.get("name") != NAME or detail.get("uri") != URI or detail.get("subscribed_events") != EVENTS or state != "enabled":
        raise SafeError("Registration does not match enabled pilot")
    return url

def ping(url, headers):
    req = urllib.request.Request(url + ":ping", headers={**headers, "Content-Type":"application/json"}, method="POST", data=b"{}")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            print("Google ping HTTP status:", response.status)
            if not 200 <= response.status < 300:
                raise SafeError("Ping not accepted")
    except urllib.error.HTTPError as exc:
        raise SafeError("Google ping HTTP status: " + str(exc.code)) from None
    print("Ping accepted; verify Cloudflare invocation logs separately.")

def main():
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_RUN_ATTEMPT") != "1" or os.environ.get("CONFIRM_FREE_PROJECT") != "true":
        raise SafeError("First attempt on main and free project confirmation required")
    mode = os.environ.get("DIAGNOSTIC_MODE")
    if mode not in ("inspect", "ping"):
        raise SafeError("Invalid mode")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SafeError("Missing API key")
    headers = {"x-goog-api-key": key}
    url = inspect(request, headers)
    if mode == "ping":
        ping(url, headers)

if __name__ == "__main__":
    try:
        main()
    except SafeError as exc:
        print(str(exc))
        raise SystemExit(1)
    except Exception:
        print("Diagnostic failed; no automatic retry.")
        raise SystemExit(1)
