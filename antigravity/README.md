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

## Permanent research archive
Create a repository Actions secret AG_ARCHIVE_KEY with a separately generated
high-entropy random value (for example openssl rand -hex 32). Keep an offline
backup; do not publish it. Run Antigravity research archive manually once with
run ID 43857964113 to migrate the verified coupler checkpoint. Subsequent
manager completions trigger the archive workflow automatically. It makes no
Google requests. The archive lives on the dedicated antigravity-archive branch
in antigravity/archive/, with an index mapping run IDs to ciphertext and SHA-256.
Identical responses share a ciphertext via a keyed fingerprint. Only encrypted
originals and non-sensitive index metadata are committed; public scientific
results require separate review. No automatic key rotation or pruning.
If no matching temporary artifact exists, manager restores the latest permanent
checkpoint for the experiment. Explicit historical IDs still require temporary
artifacts. A new Gemini key can decrypt restored checkpoints after re-encryption,
but Google may reject retrieval if the key belongs to another project.
Archive workflow requires contents write permission and a writable archive
branch. Check its status; GitHub concurrency may cancel pending archive jobs,
so manually backfill missed runs before expiration. Git history is not an
independent backup; retain the archive key and encrypted backups separately.

## Scientific export (public artifact)
Manually dispatch Antigravity scientific export on main with an experiment and
its archived manager run ID (AG-PHOTONIC-002: 43893127914). Confirm public export
only for research intended for public release. No Google request or Gemini API
key is needed. The archive key authenticates the selected completed checkpoint.
The export selects model text, execution code/results and file-write evidence;
thoughts, signatures and structured interaction metadata are omitted. Known
identifiers, the archive key and common credential patterns in selected text
cause export to fail. This is not a guarantee against arbitrary secrets in
free text; never use this workflow for confidential inputs or research. The
artifact is public, expires after seven days, and is not independently validated.
No agent code is executed and no plaintext is committed. Review before reuse.
