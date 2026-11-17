"""Explicit source-only follow-up in the existing completed AG003 environment.

Run only after confirming free-tier eligibility and billing disabled. No retries,
no new environment, no execution of returned code. Encrypted output only.
"""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import manager

EXPERIMENT = "AG-PHOTONIC-003"
PROMPT = """Recover the existing final AG-PHOTONIC-003 files from /workspace.
Do not modify, regenerate, or rerun the experiment. Do not create substitute
files. Read exactly params.py, physics_model.py, sweep.py, circuit_sim.py,
train_sim.py, run_all.py, and report.json. For each, emit the exact original
bytes in base64, byte length, SHA-256, and basename. Use a read-only Python
code execution to print one complete JSON manifest directly as its tool result.
Compute the bytes and hashes from the files, not from memory. Do not repeat
base64 in the final answer; a short completion statement is sufficient.
Use exactly one JSON object in the tool result, no Markdown or surrounding text,
with a files array; each file object must contain name, base64, size_bytes,
and sha256. If a file is missing, omit it from files and list it in missing.
Include any required input filenames and dependency versions separately. If available,
also report the exact previous and final energy-validation assertion and
the source diff, clearly distinguishing evidence from recollection.
Do not disclose secrets, environment identifiers or unrelated files.
This is an export only, not further research."""

def recover(key, prior, output, budget, confirm, recovery=None):
    if not confirm or not key or not 20_000 <= budget <= 1_000_000:
        raise ValueError("Explicit free-project confirmation and bounded budget required")
    if output.exists() or prior.resolve() == output.resolve():
        raise ValueError("Output must be new")
    parent = manager.load(key, EXPERIMENT, prior)
    if parent.get("status") != "completed":
        raise ValueError("Completed original required")
    environment = manager.background.valid_id(parent.get("environment_id"))
    if environment == "remote":
        raise ValueError("Existing environment required")
    previous = parent
    if recovery is not None:
        previous = manager.load(key, EXPERIMENT, recovery)
        if previous.get("status") != "incomplete" or previous["id"] == parent["id"]:
            raise ValueError("Continuation requires an incomplete recovery")
        if previous.get("environment_id") != environment:
            raise ValueError("Recovery environment mismatch")
        if output.resolve() == recovery.resolve():
            raise ValueError("Output must be new")
    payload = dict(manager.EXPERIMENTS[EXPERIMENT], background=True, store=True,
                   previous_interaction_id=previous["id"], environment=environment,
                   input=PROMPT)
    payload["agent_config"] = dict(payload["agent_config"], max_total_tokens=budget)
    result = manager.background.request(key, payload=payload)
    manager.seal(key, EXPERIMENT, result, output)
    if result.get("id") in (parent["id"], previous["id"]):
        raise ValueError("Expected distinct follow-up")
    if result.get("status") not in manager.background.ACTIVE and result.get("status") != "completed":
        raise ValueError("Recovery stopped; encrypted response preserved")

def retrieve(key, prior, recovery, output, confirm):
    if not confirm or not key or output.exists():
        raise ValueError("Explicit confirmation and new output required")
    parent = manager.load(key, EXPERIMENT, prior)
    current = manager.load(key, EXPERIMENT, recovery)
    if parent.get("status") != "completed" or current["id"] == parent["id"]:
        raise ValueError("Invalid recovery checkpoint")
    if current.get("environment_id") != parent.get("environment_id"):
        raise ValueError("Recovery environment mismatch")
    # Preserve the authenticated checkpoint before any potentially failing GET.
    manager.seal(key, EXPERIMENT, current, output)
    if current.get("status") == "completed":
        return
    if current.get("status") not in manager.background.ACTIVE:
        raise ValueError("Recovery is not active")
    result = manager.background.request(key, interaction_id=current["id"])
    if result.get("id") != current["id"]:
        raise ValueError("Interaction mismatch")
    manager.seal(key, EXPERIMENT, result, output)
    if result.get("status") not in manager.background.ACTIVE and result.get("status") != "completed":
        raise ValueError("Recovery stopped; encrypted response preserved")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("submit", "retrieve", "continue"), default="submit")
    p.add_argument("--recovery", type=Path)
    p.add_argument("--prior", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--budget", type=int, default=1_000_000)
    p.add_argument("--confirm-free-project", action="store_true")
    a = p.parse_args()
    key = os.environ["GEMINI_API_KEY"]
    if a.mode == "retrieve":
        if a.recovery is None:
            p.error("Recovery checkpoint required")
        retrieve(key, a.prior, a.recovery, a.output, a.confirm_free_project)
    elif a.mode == "continue":
        if a.recovery is None:
            p.error("Incomplete recovery checkpoint required")
        recover(key, a.prior, a.output, a.budget, a.confirm_free_project, a.recovery)
    else:
        if a.recovery is not None:
            p.error("Recovery checkpoint only valid in retrieve or continue mode")
        recover(key, a.prior, a.output, a.budget, a.confirm_free_project)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Source recovery stopped: {type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
