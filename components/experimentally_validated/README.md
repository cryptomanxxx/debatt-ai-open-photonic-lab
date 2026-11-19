# Experimentally Validated Components — evidence index

Published physical demonstrations linked to external component IDs. Neither entry establishes exact geometry/revision equivalence to the pinned PDK cell. No raw complex S data or process qualification is asserted. Do not treat these entries as Debatt-AI fabrication results.

| Component ID | Physical evidence | Scope |
|---|---|---|
| siepic-bdc-te1550 | [10.1364/OE.23.003795](https://pubmed.ncbi.nlm.nih.gov/25836231/): SOI broadband directional couplers including 50:50 demonstrated; reported bandwidths exceed 75 nm across studied devices. | Published design family; exact revision unverified |
| siepic-gc-te1550 | [10.1364/OE.22.020652](https://pubmed.ncbi.nlm.nih.gov/25321270/): Published TE grating coupler measured insertion loss 4.1 dB and 1 dB bandwidth 30.6 nm; not the local placeholder model. | Published design family; exact revision unverified |

For exact-cell promotion require documented revision/geometry, process, measurement conditions, traceable data and license; for calibrated circuit use also require model-to-measurement agreement. No exact-cell entries yet.

## Imported external measurement evidence

[OPA-LIB-004 SiEPIC PCM spiral cutback](SiEPIC-PCM-2020-02-UW/README.md): five original TE MAT scans from D2020_02_UW, 6001 wavelength points each, three detectors. Measured external test structures only; no exact pinned-cell geometry or phase, no complex S or qualification. Independent cutback CI passed; the permanent archive preserves the verified [raw detector CSV](SiEPIC-PCM-2020-02-UW/archive/datasets/raw-detectors.csv), [spectral fits](SiEPIC-PCM-2020-02-UW/archive/datasets/cutback-spectrum.csv) and [report](SiEPIC-PCM-2020-02-UW/archive/evidence/result.json).

[OPA-LIB-004 Twente TFLN — Wei et al.](Twente-TFLN-Wei-2025/README.md): 40 exact external figure-source CSVs and [original ZIP](Twente-TFLN-Wei-2025/archive/original.zip), CC BY 4.0, [provenance](Twente-TFLN-Wei-2025/archive/provenance.json). All paths and bytes verified; selected figure schemas and metrics analyzed; remaining figures pending review. Different TFLN process from lnoi400; no exact-cell calibration or measured complex optical S.

Twente analysis evidence: [modulator](Twente-TFLN-Wei-2025/analysis-archive/modulator/result.json), [ring](Twente-TFLN-Wei-2025/analysis-archive/ring/result.json), [cascade](Twente-TFLN-Wei-2025/analysis-archive/cascade/result.json), [provenance](Twente-TFLN-Wei-2025/analysis-archive/provenance.json). Three original CI artifacts, 19 checks, 51006 measured spectrum rows without double-counting and 400 separate theoretical rows. Apparent resonance metrics and sideband-derived modulation depth are external experimental references, not isolated-ring or exact-cell calibration. Replayed with original reviewed algorithms, not independent estimators.
