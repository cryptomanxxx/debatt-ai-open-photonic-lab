# Antigravity research lab

AG-INFRA-001 is a feasibility probe, not a photonic simulation. AG-PHOTONIC-001 will independently reproduce a directional coupler benchmark before comparing against the lab's existing FDTD/MPB results.

## Zero-cost policy
Use only a dedicated Gemini API project with billing disabled, after checking the current [pricing](https://ai.google.dev/gemini-api/docs/pricing) and confirming agent free-tier eligibility. Never use a paid project or enable billing to bypass quota errors. The runner cannot verify billing status; its explicit confirmation is an operator assertion, not a spending cap. No live calls in CI. No credentials in the repository. Free-tier data may be subject to Google's terms; send only public/non-sensitive material.

## Run
From the repository root:
```sh
python antigravity/experiments/AG-INFRA-001/probe.py
python -m unittest discover -s antigravity/tests
# Only after verifying the dedicated project is free and billing disabled:
# Set GEMINI_API_KEY securely in your environment.
python antigravity/experiments/AG-INFRA-001/probe.py --live --confirm-free-project
```
Dry run is the default. Live mode makes one POST, no automatic retries or polling. A timeout does not imply remote cancellation. The response is saved locally under antigravity/results/; inspect before sharing. Agent-reported hardware and command output are unverified observations. No installation or heavy simulation in this first probe.

API reference: https://ai.google.dev/gemini-api/docs/antigravity-agent

## Initial token budget
The initial probe requests a 20,000 total-token limit via `agent_config.max_total_tokens`. This is a conservative experimental choice, not a monetary cap or a guarantee of free eligibility. If the service rejects the limit or returns an incomplete interaction, stop and inspect the response; do not automatically increase the budget or retry. See the [agent budget controls](https://ai.google.dev/gemini-api/docs/antigravity-agent). Confirm free-tier status at https://aistudio.google.com/api-keys before any live call. Never paste the API key into chat or commit it.

## Experiment manager (encrypted checkpoints)
Use the manual Antigravity experiment manager workflow on main. Confirm the
billing-disabled project for every operation. The only long-term secret is
GEMINI_API_KEY. For the existing coupler, select import once using the existing
AG_RETRIEVE_INTERACTION_ID secret. For a new experiment select start and explicitly
confirm new submission. Each operation sends exactly one request; start uses
background=true and store=true. No automatic POST retries; reruns are blocked.
If submission times out without a checkpoint, inspect AI Studio before submitting again.

For retrieval select the experiment and leave prior_run_id blank. The manager
finds the newest completed main-branch manager run with a non-expired,
experiment-specific checkpoint (including failed jobs that saved a response).
An explicit prior_run_id overrides discovery for historical retrieval. Legacy
coupler run 43855012421 is a verified migration fallback; other legacy artifacts
require explicit selection. The encrypted experiment identity is checked before
any Google request. No matching checkpoint means stop, never start a new job.
No Google interaction ID is needed.
The checkpoint contains the entire response including environment ID and is
authenticated-encrypted with Fernet using a domain-separated SHA-256 derivation
from the API key. Public artifacts contain ciphertext only. Keep the original
API key securely: rotation or loss prevents decryption. Artifacts expire after
90 days (or earlier per repository policy); download encrypted backups as needed.
Do not publish decrypted raw responses or credentials. For local inspection,
install python3-cryptography, download and extract the checkpoint, set the API
key securely in your shell, then from the repository root:
```sh
python3 -c 'from antigravity.manager import load; from pathlib import Path; import os,json; print(json.dumps(load(os.environ["GEMINI_API_KEY"],"AG-PHOTONIC-001",Path("checkpoint.enc")),indent=2))'
```
This first manager version does not schedule polling or maintain a permanent
registry. A green job can mean active, not completed; inspect its status log.
Distinct manually dispatched start runs can still create distinct interactions.
Legacy workflows remain available; do not use their raw public artifacts for
sensitive material. Scientific validation remains separate from API completion.
