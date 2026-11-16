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
