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

## Observed results — 2026-11-17

[CI run 44106677587](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44106677587) passed all eight checks. The downloaded original ZIP (218777 bytes) was independently checked against GitHub SHA-256 and ZIP CRC. Its six files are pinned by the archive script; permanent Git archive is pending manual workflow.

| Architecture | Original feasible | Corrected feasible | Best original TOPS/W | Best corrected TOPS/W |
|---|---:|---:|---:|---:|
| MZI | 49 | 83 | 1.5329 | 1.5329 |
| MRR | 64 | 119 | 0.6471 | 0.6471 |
| Hybrid | 86 | 144 | 1.6279 | 1.6279 |
| SingleWave_MZI | 5 | 5 | 1.9145 | 1.9145 |
| IndepLaser_MZI | 121 | 121 | 2.0842 | 2.0842 |
| Total | 325 | 472 | 2.0842 | 2.0842 |

All 147 newly feasible configurations are 4-bit comb candidates (34 MZI, 55 MRR, 58 Hybrid). None of the 325 previously feasible candidates becomes rejected. Of the previously feasible candidates, 98 records change. Of the optical-link-budget rejections, 631 change classification: 147 feasible, 382 below minimum throughput, 102 endurance-limited. Counts of 6-bit candidates remain 30 (all independent laser); no 8- or 12-bit candidates are analytically feasible in either model.

The best new candidate is Hybrid, distributed, 2 pumps / 8 combs, 8 wavelengths, 8x8 mesh, 8 tiles, Pockels TFLN, 4 bits: 1.6216 TOPS/W, 75.305 W system proxy, 122.117 TOPS, 194.62 mW modeled optical pump power per pump, amplifier used. The best overall comb candidate remains the unchanged 8-pump/8-comb Hybrid at 1.6279 TOPS/W. Neither approaches the assumed 3.5 TOPS/W electronic reference. Best overall independent laser candidate remains 2.0842 TOPS/W at 4 bits; best >=6-bit candidate remains 1.5405 TOPS/W at 6 bits.

The paired CSV contains 46,514 changed records, including 45,785 with unchanged optical rejection category, 631 changed feasibility/rejection classifications and 98 changed feasible records. It is not a complete list of all rejected configurations. Independent inspection of both feasible JSON lists found unique configuration keys, matching counts, 147 new keys and zero removed keys.

These are analytical feasibility results, not training convergence or measured hardware. Original toy training reached only 79.72% at 4 bits, below its 90% target; the new 4-bit candidates have not been independently tested for convergence. The correction increases feasible counts but does not change the best efficiencies or establish a competitive comb training architecture.

## Next correction

Prioritize receiver SNR and source/amp accounting at fixed configuration, including balanced detection and local-oscillator optical/electrical costs, explicit signal versus ASE power and bandwidth, per-laser versus aggregate limits, and pump-threshold floor handling. Verify against independent algebraic tests before further full sweeps. Preserve this stage as an immutable comparison baseline; do not combine unrelated changes without attribution.
