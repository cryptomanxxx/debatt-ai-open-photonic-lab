# OPA-LIB-004 — SiEPIC measured spiral waveguide cutback, D2020_02_UW

Five byte-identical experimental MATLAB scans from [SiEPIC EBeam PDK, pinned revision](https://github.com/SiEPIC/SiEPIC_EBeam_PDK/tree/363fbb52eefa8669100499ab531d3fe7befc4867/PCM/D2020_02_UW). The upstream [spiral cutback analysis](https://github.com/SiEPIC/SiEPIC_EBeam_PDK/blob/363fbb52eefa8669100499ab531d3fe7befc4867/PCM/PCM_analysis/spiral_cutback_analysis.py) explicitly names these five files, nominal lengths (converted to cm), detector 2 and TE cutback. Preserve the original analysis for attribution/reference; do not execute its legacy Python 2 script. MATLAB metadata shows measurements on March 1 2020 and nominal TE 1550 labels. The folder name indicates UW February 2020 run; no exact wafer process certificate established.

## Original evidence and license

The five MAT files (193336 bytes each, 966680 bytes total) and original analysis are in [original/](original/) and [upstream/](upstream/), with [source manifest](manifest.json) and byte-identical [project MIT license](LICENSE.md). Source repository explicitly distributes measurement examples and these PCM files are part of its public project; no separate license or README found at PCM or run-directory checked paths. Interpret the project license as covering these distributed example files; retain attribution to Lukas Chrostowski and contributors and Huixu (Chandler) Deng for analysis. This does not authorize other foundry datasets, third-party restricted materials or fabrication. No private or external Dropbox data imported. MAT files contain detector readings, device and stage coordinates and timestamps.

| Device | Nominal length (µm) | Detector 2 at 1550 nm (dB) |
|---|---:|---:|
| 1698 | 1213 | -25.3761323181 |
| 1695 | 11204 | -32.4392061322 |
| 1711 | 32237 | -36.0350930438 |
| 1712 | 53018 | -41.2909096919 |
| 1699 | 102530 | -51.5441507422 |

Preliminary independent MAT v5 read: five scans, 6001 wavelengths each, identical 1520–1580 nm grid with 0.01 nm spacing, three detector columns (90015 stored readings). Raw detector 2 at 1550 nm yields effective loss 2.40201899741961 dB/cm, R² 0.9670429846738993. These are preregistered independent readback/OLS expectations pending SciPy CI, not certified loss. Device counts, original source Git blobs and metadata are in manifest. The dB scale is used as in the upstream analysis; its absolute reference is not independently established.

## Analysis plan

- Preserve all detector readings and original MAT bytes; no phase inferred.
- Read named `scandata.wavelength` and `scandata.power` fields, verify device metadata and common grid.
- Fit detector 2 level vs nominal length in cm, with intercept; negative slope is effective length-dependent loss. Report residuals, R², conditional OLS 95% interval (3 residual degrees of freedom), leave-one-out sensitivity and local 1540–1560 nm quartic sensitivity. The latter differs explicitly from upstream full-grid quartic.
- At each wavelength, fit only if all five detector 2 levels exceed observed stored -100 dB floor; retain all floor readings in raw export and do not infer calibrated detector sensitivity or interpolate missing values.
- No direct measurement of isolated straight waveguide, bend loss, coupling loss, phase, complex S or exact GDS revision. Intercept absorbs shared offsets but is not a calibrated facet loss. No exact match to LIB001 GDS or LIB002 TFLN. Do not use these silicon spiral estimates to calibrate Luxtelligence TFLN models.

CI exports raw detector CSV, cutback-spectrum CSV, result JSON and environment list. Original measured files are committed by this PR; derived CI files are not yet permanently archived. No additional fabrication or measurement is performed.

## Further acquisition candidates (reference only)

- [SiEPIC openEBL 2025-10](https://github.com/SiEPIC/openEBL-2025-10) and [2025-02](https://github.com/SiEPIC/openEBL-2025-02): linked measurement folders, require individual file access, license, matching design and calibration before import.
- Wei et al., [Nature Communications 16, 2281 (2025)](https://doi.org/10.1038/s41467-025-57441-1), [data DOI 10.5281/zenodo.14065933](https://doi.org/10.5281/zenodo.14065933): measured TFLN MZM and microring circuit, 500 nm film/250 nm etch, not lnoi400; dataset license and contents not independently verified, reference only.
- Dominguez Bucio et al., [10.5258/SOTON/D0392](https://doi.org/10.5258/SOTON/D0392): CC BY 4.0 SiN angled MMI O-band spreadsheet, not 1550 nm TFLN; file content not retrieved, reference only.
- Vitali et al., [10.5258/SOTON/D2550](https://doi.org/10.5258/SOTON/D2550): CC BY-labelled SiN grating-coupler source spreadsheet; not SiEPIC SOI. File content not retrieved, reference only.
- [TFLN directional coupler paper](https://opg.optica.org/ol/abstract.cfm?uri=ol-48-5-1264) and [TFLN polarization-insensitive MMI paper](https://opg.optica.org/ol/abstract.cfm?uri=ol-49-15-4409): data on request, no public raw files verified. Exact Luxtelligence MMI/DC measured complex S remains unavailable in checked sources. Request data from source owner before any claim of model validation.

### Device identity clarification

The filename/device-label suffixes 1698, 1695, 1711, 1712, 1699 differ from the stored `measured_device_number` values 1363, 1360, 1376, 1377, 1364 respectively. These independent fields were read directly from the original MAT bytes and are checked separately. No scientific data or acceptance threshold changed.

## Verified CI results and archive preparation

[Run 44558959047](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44558959047) passed all six checks. At 1550 nm raw OLS effective loss 2.4020189974196104 dB/cm, R² 0.9670429846738993, intercept -27.719318239225444 dB, conditional 95% CI [1.5872622926232898, 3.216775702215931] dB/cm. Local quartic sensitivity loss 2.4728764622493866 dB/cm; leave-one-out range 2.123377623642176–2.796002875918146. 5972/6001 wavelength rows eligible; 29 excluded due to one or more stored detector-2 values <= -100 dB. All 90015 readings preserved, no calibrated sensitivity inferred. [Pinned artifact](archive-source.json): 14548435012, 786855 bytes. After preparation PR merges, run [OPA archive LIB004 evidence](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/workflows/opa-archive-lib004.yml) on main with confirm_archive=true. Read-only preflight and permanent offline audit independently parse exact MAT v5 bytes using stdlib, compare all raw detector readings and replay complete spectral OLS, center interval and leave-one-out. Quartic derived regression is replayed from archived fitted values, not independently refit. Exact derived files follow separate archive PR. No measurement of isolated straight waveguide, TFLN calibration or exact-cell qualification.
