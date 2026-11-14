# OPA-ID-001 — Adjoint solver verification

[Successful CI job](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/43596583595/job/132452389643) · [PR #51](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/pull/51)

All seven acceptance checks passed. Meep 1.35.1 with Autograd 1.9.1, 143 material weights in a 1.2 × 1.0 µm 2D design region, 1550 nm, resolutions 30 and 60 pixels/µm. Runtime 264.47 s. The objective is unnormalized mean squared Fourier Ez, not power transmission.

## Normalization-window finding

The single-frequency adjoint Gaussian in Meep's [objective.py](https://github.com/NanoComp/meep/blob/v1.35.1/python/adjoint/objective.py) uses a forward-time-limited discrete Fourier normalization. Its duration is 155 Meep time units for this frequency. Extending the minimum simulation time from 20 to 200 resolved the observed mismatch in this configuration. The short-window control reproduces the discrepancy with the same geometry and objective, supporting the causal hypothesis. No gradient rescaling or tolerance change was used.

| Minimum time | Max scaled directional error, resolution 60, step 0.005 |
|---|---:|
| 20 (control) | 0.5700682677 |
| 200 | 3.638833758e-7 |

Improvement factor approximately 1.57 million. Error is normalized by the full adjoint gradient norm, not individual directional derivative magnitude. Across both steps and resolutions the largest error for the accepted mean objective is 1.354978157e-6.

| Direction | Adjoint | Central finite difference (resolution 60, step 0.005) |
|---|---:|---:|
| 0 | 0.481653714720 | 0.481654195088 |
| 1 | 0.136727258926 | 0.136727194525 |
| 2 | -0.118806542668 | -0.118806688591 |

At resolution 60, the independently evaluated ascent step improves the objective from 11.1380970878 to 11.1644297148. The official upstream DFT test passes its single- and multifrequency cases; its log also contains a RuntimeWarning in filter_source.py during the multifrequency case. No hardware or general multi-frequency optimization validity is claimed.

## Files

- [result.json](result.json): original report, all checks, 12 directional measurements, six diagnostic measurements, weights and gradients.
- [gradient_checks.csv](gradient_checks.csv): original primary gradient table.
- [upstream_reference.log](upstream_reference.log): original unmodified test execution log.
- [environment-lock.txt](environment-lock.txt): exact environment lock.
- [provenance.json](provenance.json): SHA-256 and source identifiers.

The installed package inventory is recorded by checksum only and remains in the original CI ZIP until expiry (2027-02-12). The other four files are byte-identical to the artifact.

## Guidance for OPA-ID-002

Retain the verified minimum-time setting for the same single-frequency source or derive a conservative window for changed source settings; verify gradients independently again in the splitter geometry. Use normalized guided-mode power rather than this field-intensity objective to evaluate splitter performance. Distinguish continuous 2D optimization from binary layout, 3D verification and fabricated hardware.
