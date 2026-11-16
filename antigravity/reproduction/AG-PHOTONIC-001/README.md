# AG-PHOTONIC-001 independent reproduction

Source: user-exported Google AI Studio interaction (ai_studio_code.txt), executed write_to_file and bash results, not the final narrative alone. The original executed coupler.ctl is preserved; reproduce.py is our new portable runner, not agent-authored code. reference.json records rounded stdout values: sweep rows [gap nm, even index, odd index, L50 um]; convergence rows [resolution, sx, sy, even index, odd index, L50 um]. Original full trace remains encrypted in the research archive; the original Python orchestration is not copied in this PR.

Model: 450 x 220 nm silicon strips, constant indices 3.48 and 1.44, 1550 nm, periodic transverse supercell, propagation along z. MPB 1.11.1 was reported by the agent; CI records the installed version. Lc = lambda/(2 delta n), L50 = Lc/2. Tolerances chosen before execution: absolute index difference 0.0002 and relative L50 difference 1%. Point-field polarization/parity diagnostics are not full field symmetry proofs. The six convergence cases and five sweep cases are independently rerun, including the repeated 200 nm case. No Google calls.

## Comparison to existing laboratory experiments

OPA-COUPLER-001 uses 500 x 220 nm strips and wavelength-dependent indices. OPA-COUPLER-002 uses a full 3D layout with 500 nm width and 236 nm gap; OPA-COUPLER-003 uses that layout and sensitivity sweeps. Their published coupling lengths are not directly comparable to the 450 nm ideal straight pair. A matched geometry parity-resolved MPB run and then a matched 3D FDTD model are follow-up work, not completed validation.

The original mesh convergence is nonmonotonic; the 64-to-96 resolution change is about 1.4%, not a proof of convergence across all gaps. Power conservation is an ideal-model assumption. No fabrication, measured insertion loss, or hardware performance is established. CI reproduces the same numerical method on another runner, not independent physical validation.

## Parity-resolved cross-validation

cross_validate.py adapts the laboratory OPA-COUPLER-001 Python solver to the exact agent geometry and constant indices. It solves each TE symmetry sector separately, rotates the propagation axis, and compares all five gaps at 96 pixels/um against the agent's rounded references. The same 1% length and 0.0002 absolute index tolerances apply. A separate 200 nm gap refinement at 100, 200 and 400 pixels/um requires the last two lengths to agree within 1%; a 5x3 to 6x4 um cell check at 200 pixels/um requires 0.5% agreement. These thresholds are prospective, not observed results. Refinement at one gap does not establish convergence at all gaps. Both implementations use MPB, so this is an implementation cross-check, not a different physical solver. Matched 3D FDTD remains a separate follow-up. No external API calls or credentials are used.
