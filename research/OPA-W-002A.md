# OPA-W-002A — Conditional multilevel intensity-cell screen

Status: implementation pending CI and review. [W-001A](OPA-W-001.md) identifies GSSe as a candidate, but no measured state distributions or process-qualified memory model are available. This experiment is intentionally material-agnostic. It does not complete the empirical W-001 or W-002 gates.

## Frozen design

Compare natural binary labels for 2 and 16 uniformly spaced normalized intensity states on [0.2,0.8] (spacing 0.6 and 0.04 respectively). Draw independent Gaussian programming errors per write, clip stored transmission to [0,1], hold fixed for eight reads. Add independent Gaussian receiver noise and a single Gaussian offset shared by every validation read in a panel. Clip receiver values to [0,1], round to nearest ADC code (ties to even), scale back. Calibration has zero drift; estimate state means from independent calibration writes and reads and freeze midpoint thresholds. Non-increasing calibration means block that panel; ties in decoding go to the higher state. No adaptive test-set thresholds.

Eight fixed seeds; 512 independent writes per state in each calibration and validation split, eight reads per write. Programming and receiver standard deviations independently sweep 0, 0.002, 0.005, 0.01, 0.02 in normalized full-scale units; shared drift sigma 0, 0.005, 0.02; ADC 6, 8, 12 bits. Use common random numbers within a bit-depth/seed across parameter settings. Binary and 16-state comparisons have equal per-state sample size, not equal total reads. 3,600 panels total (1,800 per bit depth); no pooling as independent trials across settings.

Report natural binary BER (Hamming errors / bits read), SER, worst state SER, all confusion counts, calibration centers and thresholds, held-out state means/std, clipping counts and actual drift draws. Pre-register worst-state observed SER <= 0.001 as a **conditional point screen only**. A negative scientific outcome is valid; execution success is not a reliability pass. A per-panel one-sided Hoeffding upper bound on average SER uses independent write-cluster fractions conditional on calibration and drift, not independent repeated reads; no simultaneous or across-drift guarantee. With zero bad write clusters, also report exact conservative zero-event bound on the mean probability of any erroneous read per write (equal state weights; heterogeneous independent trials). No physical BER claim. Eight shared-drift draws are sensitivity examples, not a population reliability characterization.

## Reproduction and outputs

Run the registered experiment in the existing locked CI environment. [Implementation](../simulations/memory/multilevel_cell_v001.py) and [tests](../simulations/memory/test_multilevel_cell.py) cover ideal control, zero margin, clipping, Hamming accounting, repeated-read counts and reproducibility. Export panels.csv, confusion.csv, calibration.json and result.json with environment records. Preserve positive and negative outcomes and failed calibration panels; archive original CI bytes via the public profile. No actual results claimed before CI.

## Limits and next gate

No time axis or calibrated retention law, read disturb, thermal crosstalk, device-to-device distributions, optical complex phase, write energy or endurance. Normalized intensity values and noise are assumptions, not measured GSSe properties. No direct mapping from ADC nominal bits to usable memory bits. Before W-003, obtain state-specific experimental distributions and addressing constraints; use W-002A to identify sensitivity regions, then preregister a separately validated model or a negative conclusion. The [OPA-M comparison contract](OPA-W-001.md) remains unchanged.
