# AG-PHOTONIC-001 — autonomous coupler pilot

The agent receives a physical problem, not our implementation or reference results.
This is a bounded single-agent pilot, not a multi-agent teamwork experiment.

The geometry and indices are fixed benchmark assumptions, not a foundry PDK.
A 50/50 splitter is the target. The agent may choose gap and length.
After the response is archived, independently reproduce its code in an isolated
GitHub environment without secrets. Review generated code before executing.
Compare identical geometries, material assumptions, modes and definitions of
coupling length; do not compare unmatched reference values. Require numerical
convergence and power conservation checks before claiming full-wave agreement.
An approximate or unexecuted result is not a successful full-wave validation.
Record model ID, usage, wall time, solver, dependencies, raw data and limitations.
API completion is transport success only, not scientific success.

Run offline: `python antigravity/experiments/AG-PHOTONIC-001/run.py`.
Live execution is manual only, on main, with a verified billing-disabled project.
The requested 20,000 token budget is not a guaranteed usage or monetary cap.
No automatic retry. Raw response is retained for seven days; it may be public.

## Resume an incomplete run

From the saved response JSON, copy the top-level `id` and `environment_id`
into repository Actions secrets `AG_PREVIOUS_INTERACTION_ID` and
`AG_ENVIRONMENT_ID`. Do not commit identifiers. Use the same Google project.
Dispatch AG-PHOTONIC-001 resume on main after verifying billing is disabled.
Each dispatch sends one new request with its own requested 20,000-token budget.
If incomplete again, update both secrets from the newest response before
another manually approved continuation. Never automatically restart a missing
sandbox. Free-tier interaction retention is documented as one day; sandbox
availability is not guaranteed. Raw response artifacts may contain identifiers.
See https://ai.google.dev/gemini-api/docs/antigravity-agent.
