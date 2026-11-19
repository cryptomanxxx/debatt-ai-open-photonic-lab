# Experimentally Validated Components — evidence index

Published physical demonstrations linked to external component IDs. Neither entry establishes exact geometry/revision equivalence to the pinned PDK cell. No raw complex S data or process qualification is asserted. Do not treat these entries as Debatt-AI fabrication results.

| Component ID | Physical evidence | Scope |
|---|---|---|
| siepic-bdc-te1550 | [10.1364/OE.23.003795](https://pubmed.ncbi.nlm.nih.gov/25836231/): SOI broadband directional couplers including 50:50 demonstrated; reported bandwidths exceed 75 nm across studied devices. | Published design family; exact revision unverified |
| siepic-gc-te1550 | [10.1364/OE.22.020652](https://pubmed.ncbi.nlm.nih.gov/25321270/): Published TE grating coupler measured insertion loss 4.1 dB and 1 dB bandwidth 30.6 nm; not the local placeholder model. | Published design family; exact revision unverified |

For exact-cell promotion require documented revision/geometry, process, measurement conditions, traceable data and license; for calibrated circuit use also require model-to-measurement agreement. No exact-cell entries yet.

## Imported external measurement evidence

[OPA-LIB-004 SiEPIC PCM spiral cutback](SiEPIC-PCM-2020-02-UW/README.md): five original TE MAT scans from D2020_02_UW, 6001 wavelength points each, three detectors. Measured external test structures only; no exact pinned-cell geometry or phase, no complex S or qualification. Independent cutback CI passed; the archive review PR preserves the verified [raw detector CSV](SiEPIC-PCM-2020-02-UW/archive/datasets/raw-detectors.csv), [spectral fits](SiEPIC-PCM-2020-02-UW/archive/datasets/cutback-spectrum.csv) and [report](SiEPIC-PCM-2020-02-UW/archive/evidence/result.json).
