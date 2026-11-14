# OPA-MOD-005 — Conditional energy efficiency

**Evidence:** successful [CI run](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43550202206), original ZIP SHA-256 verified. All nine report checks pass. 288 parameter scenarios × four workloads × two receiver RMS targets × five sizes = 11,520 rows (2,304 groups). All input coefficients are hypothetical. Results do not establish real hardware efficiency or equal end-to-end accuracy.

The original 8,716,060-byte result.json is archived in 22 consecutive byte parts, verified individually against the downloaded ZIP. Run `python results/opa-mod-005/restore_report.py` to verify and print the summary, or add `--output /tmp/opa-mod-005-result.json` to reconstruct the exact original report. Do not normalize part line endings.

| Tile | Feasible / 2304 | Both feasible vs monolithic | Lower energy | Higher energy | Ratio range |
|---|---:|---:|---:|---:|---|
| 128 | 512 | 512 | 0 | 0 | 1 |
| 64 | 592 | 464 | 19 | 445 | 0.720455–3.549243 |
| 32 | 656 | 440 | 0 | 440 | 1.013612–4.810174 |
| 16 | 680 | 432 | 0 | 432 | 1.031763–8.624046 |
| 8 | 656 | 416 | 0 | 416 | 1.068066–16.472555 |

Ratios only exist when both architectures meet the receiver noise target. Of 2,304 groups, 1,544 have no feasible architecture; 248 have an infeasible monolithic baseline but at least one feasible modular alternative. Among 760 groups with at least one feasible design, lowest modeled energy is at size 128 in 493, 64 in 147, 32 in 88, and 16 in 32. This is not a win rate over a probabilistic hardware distribution.

All 19 direct modular energy wins occur at size 64, 3% target, 16-bit ADC and the lower electronic overhead setting (0.1 pJ base; ADC 25.6 pJ). Fifteen are orthogonal workloads with 0.175 dB/column; four are ill-conditioned with 0.095 dB/column. No direct wins at 1% or for random_signed or rank_one. At the tested link losses 0/2/6/12 dB the wins are 6/6/4/3, respectively; the experiment does not establish a universal communication break-even.

Best case: scenario 209, orthogonal, 3% receiver RMS; 0.175 dB/column, 0 dB extra modular link, 16-bit ADC, 0.1 pJ base overhead, 1 nW/control and 1,000,000 weight reuses. 128 vs 64: 47.3 vs 25.1 dB scalar loss; 9.377577 vs 6.756125 nJ/MVM; 572.362 vs 412.361 fJ/MAC (one MAC counted per weight); 27.95% reduction. Laser term 6.009415 vs 0.059835 nJ; receiver/ADC term 3.2768 vs 6.5536 nJ. The energy reduction comes from lower modeled laser cost outweighing extra conversion and communication. The monolithic ADC noise floor is 2.31%, close to the target, versus 0.359% modular. At otherwise identical settings, the energy ratios with 2/6/12 dB extra link loss are approximately 0.7243/0.7406/0.8429; no crossover in that slice.

**H5:** conditional support only; no general energy advantage. Many configurations cannot satisfy the idealized receiver precision target. No hardware calibration, DAC precision, static error or correlated noise, host/memory or cooling cost is validated here. Further work should combine MOD-003/004 residual error with receiver noise and calibrated energy coefficients before any physical efficiency claim. MOD-006 can test training numerically, but not hardware energy savings.
