# Repository instructions for AI coding agents

## Antigravity: retrieve existing files directly

Before working on Antigravity, read [antigravity/README.md](antigravity/README.md).

For existing workspace files, **use Google Environments Files API first**. Do not start or continue an AI interaction just to copy existing files. Use the existing authenticated environment ID from an encrypted checkpoint and the documented GET endpoint:

`GET /v1beta/environments/{env_id}/files/workspace?alt=media&recursive=true`

See [the verified AG003 implementation](antigravity/reproduction/AG-PHOTONIC-003/download_snapshot.py) and [recovery evidence](antigravity/reproduction/AG-PHOTONIC-003/README.md). The directory download succeeded in run [44074735184](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44074735184): seven expected files, 164850 bytes, verified SHA-256, no new AI model execution. Prior agent-mediated export attempts ended incomplete or cancelled. Preserve this lesson for all future Antigravity experiments.

Use interaction GETs for status/response retrieval, not workspace file export. Use model calls only for actual research or explicitly justified tasks requiring reasoning. If direct file retrieval fails, diagnose access, paths, API errors or environment availability before considering a model fallback. Do not automatically submit, continue, retry POSTs, or raise token budgets.

Retain the billing-disabled/free-project policy and explicit authorization for live requests. Never expose credentials or environment identifiers. Encrypt full snapshots and review files before public export. Preserve original bytes; conduct corrected research separately. Current snapshots are not proof of historical immutability.

## OPA research planning

Before proposing a new OPA research experiment, review the [prioritized research backlog](PHOTONIC_RESEARCH_ROADMAP.md), the current README, experiment registry and archived results. Reuse existing experiments rather than duplicating them. The backlog contains hypotheses, not validated results; keep the existing roadmap active and preserve the distinction between simulations, fabrication and measured hardware. Follow repository experiment and CI conventions.

## Reuse-first OPA component selection

Check [components/registry.json](components/registry.json) and [library policy](components/README.md) before proposing new component designs. Record the system requirement or missing model that justifies custom research; do not duplicate existing PDK cells, copy restricted data, or imply measurement/qualification from a layout DRC pass. Keep origin and experimental evidence separate.
