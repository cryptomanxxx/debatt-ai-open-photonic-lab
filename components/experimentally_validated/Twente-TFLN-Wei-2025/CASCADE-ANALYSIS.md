# OPA-LIB-004-TFLN-CASCADE — recurring optical minima

Source [Wei et al. dataset, CC BY 4.0](https://doi.org/10.5281/zenodo.14065933), [article](https://doi.org/10.1038/s41467-025-57441-1). Supplementary 4a–d each contain 10001 absolute optical power samples on the same nominal wavelength grid. 4a already analyzed in RING-ANALYSIS.md; 30003 additional rows, 40004 total. The final supplementary PDF was not available during prior analysis; no physical ring or heater-setting assignment is made here.

Exploratory method: local minimum below -72 dBm within ±100 samples, four wavelength windows [1549.30,1549.60], [1549.66,1549.96], [1550.02,1550.32], [1550.38,1550.68] nm selected after inspecting data. Freeze independent minima for CI. Record threshold (-71,-72,-73,-74 dBm) and radius (75,100,125 samples) sensitivity without requiring every setting to give the same count. Exact reciprocal wavelength difference, no constant nm-to-GHz conversion. Recurrence matches ordinal minima across neighboring windows only, not proven mode identities.

| Scan | Minima per window | Total | Within-window span GHz |
|---|---:|---:|---:|
|4a|1|4|0|
|4b|2|8|11.59991–11.63982|
|4c|3|12|12.20058–12.31952|
|4d|4|16|12.35951–12.54077|

4d consecutive within-window gaps are approximately 4.02–4.30 GHz (independent exploratory readback). The observed pattern is consistent with increasing complexity of a multi-resonance optical response, not a measurement of the number of physical rings. No exact heater settings, isolated-ring Q or FSR, coherent transfer function, coupling topology or RF filter bandwidth inferred. No calibration of lnoi400. CI emits result.json and minima.csv; permanent analysis archive pending. Original CSVs unchanged. Next step archive MOD, RING and CASCADE derived evidence before comparative component studies.
