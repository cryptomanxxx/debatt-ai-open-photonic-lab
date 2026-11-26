# OPA-W-002G — State-resolved memory error analysis

Status: implementation pending CI and review. [W-002F archived audit](../results/ci-originals/opa-w-002f/45906280960-15157888531/result.json) verified 62,208 original W-002E policy rows and 31,104 matched comparisons. It cannot identify individual failing states. This separate diagnostic replay adds state-resolved counts, not a new held-out experiment or historical raw observations.

## Frozen replay protocol

Verify all six [W-002E original files](../results/ci-originals/opa-w-002e/45905192736-15157223437/archive-provenance.json), source run 45905192736 and artifact 15157223437. Pin original adaptive_calibration_v005.py and multilevel_cell_v001.py Git blob identities (94508ac151f19103b70c8a694116327a0f416577 and 26b7ffb6172db8a1d0b4550c7f546fae0180ff7e). Use the existing locked CI environment, preserve its environment records, and record NumPy version. No claim that matching aggregate outputs establishes historical sample identity.

Reuse the 5,184 original held-out trajectory keys, 64 steps, 32 cells per state, 16 states, original fixed baseline and 12 corrected configurations. Freeze the original development gate choices by checking all 18 archived candidate records and their selection rule; no further tuning. For every corrected row require agreement with archived baseline and corrected SER, BER, worst-state SER, decisions, data clipping, enabled steps and mean absolute drift diagnostics. Fail execution on any mismatch. The same seeds are intentionally reused for diagnosis and are not fresh validation data.

## State and temporal outputs

For each of 67,392 trajectory/configuration pairs retain all 16 state error counts and matched baseline counts in a wide CSV (1,078,272 state counts, plus baseline counts). Each state has 2,048 reads; more than two errors fails the existing point criterion. Count all ties for worst state, unique nonzero worst states, new state failures and rescued states relative to fixed. Retain all errors, including edge states and ideal controls.

Aggregate 16x16 confusion matrices by configuration and chronological error counts by state and step over all trajectories. Preserve detailed per-step actual common drift, applied correction, enabled status, scheduled acquisition, reference change mean/spread/clipping and total symbol errors for the first fixed held-out seed 22001 across all 324 scenarios and 13 configurations (269,568 rows). This predetermined subset bounds archive size; it is not selected by outcomes. Other seeds contribute to state totals, per-trajectory state counts and aggregated step/state counts. No full per-trajectory per-step state tensor or raw ADC samples retained. Report all ties rather than arbitrarily naming one worst state.

Outputs: state_counts.csv, diagnostics.csv, state_summary.csv, confusion_summary.csv, step_state_summary.csv, result.json and two environment files. [Implementation](../simulations/memory/state_replay_v007.py), [tests](../simulations/memory/test_state_replay.py). Replay outputs are a new CI artifact with their own provenance; do not overwrite original W-002E files.

## Next gate

Inspect replay agreement and state-level failure distributions before designing a tail-aware policy. Any new threshold or correction policy must be selected on separate development data and evaluated on fresh held-out seeds. Model results remain conditional; measured state distributions, retention, read disturb, energy, addressing and fabrication access are missing. No W-003 release or physical qualification.
