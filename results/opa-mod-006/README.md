# OPA-MOD-006 — Hybrid AI training

**Evidence:** [CI run 43552625166](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43552625166), job 132318355385, artifact 14096993702. Original artifact ZIP SHA-256 verified. All eight checks passed; maximum ideal forward absolute error 9.66e-15. The report contains 75 configurations, 624 learning-curve records and 36 paired comparisons.

## Held-out test MSE

Mean over three seeds; lower is better. Both policies are evaluated on the same modeled optical hardware, with matching calibration policy and held-out noise seed.

| Tile | Impairments | Calibration | Digital training then optical deployment | Hybrid training | Hybrid wins / 3 |
|---|---|---|---:|---:|---:|
| 16 | low | off | 0.132662 | 0.131792 | 3 |
| 16 | low | on | 0.129997 | 0.129985 | 3 |
| 16 | high | off | 0.148924 | 0.142249 | 3 |
| 16 | high | on | 0.130624 | 0.130566 | 1 |
| 64 | low | off | 0.142856 | 0.138378 | 3 |
| 64 | low | on | 0.130061 | 0.130083 | 0 |
| 64 | high | off | 0.237996 | 0.188956 | 3 |
| 64 | high | on | 0.132837 | 0.132850 | 1 |
| 128 | low | off | 0.159729 | 0.147242 | 3 |
| 128 | low | on | 0.130064 | 0.130109 | 0 |
| 128 | high | off | 0.386344 | 0.271500 | 3 |
| 128 | high | on | 0.149178 | 0.153310 | 0 |

Hybrid wins 18/18 uncalibrated and 5/18 calibrated comparisons (23/36 overall). In the high-error uncalibrated cases, mean MSE reductions versus digital training followed by optical deployment are 4.48%, 20.61%, and 29.73% for tiles 16, 64, and 128, respectively. The purely digital test MSE averages 0.129983. Under high impairments the 16-wide tiles have the lowest mean MSE among the tested sizes for both policies. This does not establish an energy-optimal tile size.

Calibration improves the mean MSE of both training policies in every tested size/impairment group. The local phase oracle and per-program gain probes are modeled assumptions; hybrid calibration uses 544 calibration vectors versus 32 at deployment for digital training. Calibration is therefore not free. This is a synthetic linear regression pilot with a digital straight-through weight update, not physical optical training, a deep-network demonstration, or an energy benchmark. Three seeds do not establish generalization or statistical significance.

## Reconstruct the exact report

Run from any directory:

```sh
python results/opa-mod-006/restore_report.py
python results/opa-mod-006/restore_report.py --output-dir /tmp/opa-mod-006
```

The first command verifies the archive without writing files. The second restores the original 153,652-byte result.json and all three CSVs, checking the original SHA-256 of each. Existing output files are never overwritten. The two environment files in the original ZIP are not archived here; their hashes are recorded in provenance.json and the experiment uses the repository's locked environment. The complete original ZIP remains available from the Actions run until artifact expiry.
