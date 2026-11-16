"""Single-request Antigravity infrastructure probe; offline by default."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
PROMPT = """AG-INFRA-001: Execute read-only Linux commands in your remote sandbox.
Report actual command output, exit codes and unknowns, not estimates.
Inspect Python version, OS, CPU count and cgroup CPU quota, RAM and cgroup
memory limit, disk availability, and whether meep, mpb and gdsfactory are
already installed (without importing heavy packages). Do not install packages,
run simulations, browse the web, access credentials or make external requests.
Distinguish host-visible resources from effective sandbox limits. Return a
concise JSON report with commands, outputs and limitations. Do not claim
maximum runtime or billing status unless directly observed."""
PAYLOAD = {
    "agent": "antigravity-preview-09-2026",
    "input": PROMPT,
    "environment": "remote",
    "tools": [{"type": "code_execution"}],
}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-free-project", action="store_true")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps(PAYLOAD, indent=2))
        return 0
    if not args.confirm_free_project:
        parser.error("Live mode requires verified free project with billing disabled")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        parser.error("GEMINI_API_KEY is required")
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(PAYLOAD).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError("Response too large")
        result = json.loads(raw)
    except (OSError, ValueError) as exc:
        print(f"Request failed ({type(exc).__name__}); no retry. Remote work may continue.", file=sys.stderr)
        return 1
    directory = Path(__file__).resolve().parents[2] / "results"
    directory.mkdir(exist_ok=True)
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", dir=directory, prefix="AG-INFRA-001-", suffix=".json", delete=False, encoding="utf-8") as out:
        json.dump(result, out, indent=2)
        print(out.name)
    return 0

if __name__ == "__main__":
    sys.exit(main())
