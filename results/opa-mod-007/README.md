# OPA-MOD-007 — Multilayer hybrid training

Source: [successful CI run 43586842825](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43586842825), job 132423117107, artifact 14113131505. Original ZIP digest verified. All 11 checks passed. Optical experiment loop took 4457.5 seconds; 150 configurations, 72 paired comparisons, 2496 training-loss records and 360 layer-error records. Maximum digital directional-gradient error 1.21e-11; maximum ideal multilayer absolute forward error 1.96e-13.

## Results

Hybrid training lowered held-out cross-entropy in 36/36 uncalibrated comparisons and 22/36 calibrated comparisons. Accuracy improved in 35/72 comparisons, tied in 18 and declined in 19. Lower loss is not equivalent to higher accuracy.

Mean test accuracy over three seeds, three layers, high component errors and no calibration:

| Tile | Digital training then optical deployment | Hybrid training |
|---|---:|---:|
| 16 | 63.02% | 63.67% |
| 64 | 63.41% | 66.15% |
| 128 | 61.85% | 64.06% |

The 64-wide configuration has the best mean accuracy in this specific scenario, not a globally established optimum.

Mean cumulative relative activation error for hybrid training, three layers, 128-wide tile, high errors:

| Layer | Uncalibrated | Calibrated |
|---|---:|---:|
| 1 | 38.19% | 14.51% |
| 2 | 59.19% | 20.16% |
| 3 | 77.82% | 23.65% |

Calibration reduces cumulative activation error in this scenario by about 70% at layer three. Each error is relative to the ideal digital forward of that policy's own trained weights; these are not isolated per-layer device errors. The policies have separate learned weights, so this comparison includes training effects.

## Limitations

Synthetic four-class classification, 128 channels per layer, electronic tanh and digital straight-through backward. Three seeds are not sufficient to establish statistical significance or generalization. The local phase oracle and modeled losses/noise are assumptions; calibration uses extra probes. Receiver noise draws are paired across calibration policies, unlike MOD-006's cross-calibration comparison. No fabricated hardware, energy or speed advantage is demonstrated.

## Restore exact outputs

From the repository root:

```sh
python results/opa-mod-007/restore_report.py
python results/opa-mod-007/restore_report.py --output-dir /tmp/opa-mod-007
```

The first command verifies without writing; the second restores the original 690,118-byte JSON and four CSV files without overwriting existing files. All five SHA-256 hashes are checked. The two environment files are documented by hash only, not copied here. The complete original ZIP contains all seven files and is available until artifact expiry. Seven archived chunks were verified by Git blob SHA against the original ZIP's report bytes; all four CSVs were independently reconstructed byte-for-byte locally.
