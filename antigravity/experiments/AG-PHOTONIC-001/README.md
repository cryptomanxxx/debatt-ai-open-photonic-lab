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
Each resume dispatch sends one request with a configurable requested budget of 20,000–200,000 tokens (default 200,000). The HTTP timeout is 30 minutes and the job timeout is 40 minutes; neither guarantees remote cancellation. The project dashboard on 2026-11-16 showed 60 RPM, 100,000 input TPM and 100 RPD on Free Tier. These are rate limits, not an allocation or a guarantee that a 200,000-token interaction succeeds. No automatic retry or paid fallback.
If incomplete again, update both secrets from the newest response before
another manually approved continuation. Never automatically restart a missing
sandbox. Free-tier interaction retention is documented as one day; sandbox
availability is not guaranteed. Raw response artifacts may contain identifiers.
See https://ai.google.dev/gemini-api/docs/antigravity-agent.

## Background execution (preferred for long tasks)

Use AG-PHOTONIC-001 background on main. Default mode retrieve sends GET only;
set AG_RETRIEVE_INTERACTION_ID to a known interaction ID in Actions secrets.
Resume mode explicitly submits one new continuation with background=true and
store=true. Do not resume while an earlier request may still be running.
The timed-out synchronous request on 2026-11-16 did not return its new ID;
retrieving the original ID does not necessarily recover that continuation.
Poll once per minute up to 30 times, saving the latest response after each GET.
If still active or a GET fails, download the artifact, set the retrieval secret
from its top-level id, and dispatch retrieve. No automatic POST retry.
Artifacts may be public and contain identifiers or agent output; do not include
credentials or sensitive data in prompts. A hard runner cancellation may prevent
artifact upload. A POST timeout before receipt of an ID remains ambiguous.
See https://ai.google.dev/gemini-api/docs/background-execution.
