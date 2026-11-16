"""Resume one incomplete interaction using operator-supplied identifiers."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import sys

spec = importlib.util.spec_from_file_location("photonic", Path(__file__).with_name("run.py"))
photonic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photonic)

def build_payload(interaction_id, environment_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", interaction_id or ""):
        raise ValueError("Invalid interaction ID")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", environment_id or "") or environment_id in ("remote", "local"):
        raise ValueError("Invalid existing environment ID")
    return dict(photonic.PAYLOAD, previous_interaction_id=interaction_id,
                environment=environment_id,
                input="Continue the original coupler task in the existing environment. "
                      "Check the existing MPB installation and /tmp/test_mpb.ctl, "
                      "then execute and validate your model. Avoid reinstalling packages "
                      "or printing verbose logs. Preserve the original constraints. "
                      "Return actual numerical results, complete source and limitations. "
                      "If the environment is missing, stop and report it.")

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--confirm-free-project", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = build_payload(os.getenv("AG_PREVIOUS_INTERACTION_ID"), os.getenv("AG_ENVIRONMENT_ID"))
    except ValueError as exc:
        parser.error(str(exc))
    flags = []
    if args.live:
        flags.append("--live")
    if args.confirm_free_project:
        flags.append("--confirm-free-project")
    # Do not print session identifiers during offline validation.
    if not args.live:
        print("Continuation payload validated; no request sent.")
        return 0
    return photonic.probe.main(flags, payload=payload, result_prefix="AG-PHOTONIC-001")

if __name__ == "__main__":
    sys.exit(main())
