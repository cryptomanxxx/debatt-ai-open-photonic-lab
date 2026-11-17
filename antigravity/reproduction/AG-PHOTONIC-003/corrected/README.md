# Corrected AG003 model — stage 1 (pump fanout)

OPA-SYS-002 is a controlled counterfactual of the original architecture sweep.
The archived original and replay remain immutable. The corrected physics_model.py
differs from original in exactly two expressions; shared parameters are imported
unchanged from original/params.py.

For N equal comb branches per pump, ideal splitting contributes 10 log10(N)
dB. Additional splitter excess and coupling loss are included once. The
required optical power per pump is the required optical power at each ring
multiplied by the inverse branch transmission. The old formula also
multiplied by N, counting the ideal division twice. Remove that extra factor
in both the line-power calculation (used also by the amplified branch) and the
1.5× threshold floor. Nothing else is corrected at this stage.

## Paired experiment

The registered OPA-SYS-002 script enumerates the same 330,960 unique
configuration tuples, uses the same structural rejection ordering, evaluates
both models and checks original feasibility and rejection counts against the
archived report. All independent-laser/single-wave controls and N=1 cases
must remain unchanged. It verifies original hashes before and after and
requires the corrected file to equal the exact two-expression transformation.

Outputs: result.json (counts, transitions, checks, best analytical candidates),
paired_changes.csv (changed records by configuration key), and all analytically
feasible records for each model in original_feasible.json and
corrected_feasible.json. Candidate rank labels are intentionally not reused.

No convergence gate is applied. Do not treat new analytical feasibility as
validated training or physical performance. Other known issues, including
receiver and amplifier modeling, independent laser limits, path-loss
conventions, scheduling and convergence, are deferred. The six other
roadmap tracks remain deferred until AG003 is completed.
