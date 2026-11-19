# OPA-LIB-003 — external complex scattering models

Two exact original upstream JSON coefficient files from the [pinned Luxtelligence lnoi400 PDK](https://github.com/Luxtelligence/lxt_pdk_gf/tree/d16db6a4882657feb1ce696c16c604ff6cb7ccfa) are preserved under [original/](original/). The PDK README explicitly covers geometry and compact circuit models; the root [MIT license](../LICENSE) applies to this public library, and no separate data-directory license was located. No restricted foundry material or fabrication rights inferred. Git blob identities match the upstream files exactly. These are simulated polynomial fits (upstream directional-coupler doc has the typo “FTDT”), not raw FDTD samples or measured complex scattering.

| Model | Linked GDS | Source |
|---|---|---|
| MMI 2×2 | [GDS](../archive/gds/mmi-2x2.gds) | [Original coefficients](original/mmi_2x2_optimized_1550.json) |
| Directional coupler | [GDS](../archive/gds/directional-coupler.gds) | [Original coefficients](original/directional_coupler_balanced.json) |

The nominal default PCell and model use the same named factory and pinned revision. This is not proof of identical FDTD geometry, modal planes, polarization or calibration. See [manifest](manifest.json) for explicit conventions and unknowns. Native model uses phase in radians, complex coefficient = polynomial amplitude times exp(+i phase); preserve signed fitted amplitudes and all reflections. Matrix rows are outgoing, columns incoming, in order o1,o2,o3,o4. Native dimensionless field coefficients are assumed power-normalized for numerical passivity tests. No independent verification of normalization or time convention.

## Preregistered numerical audit

Evaluate 201 wavelengths, 1540–1560 nm inclusive, 0.1 nm step; compare all 16 complex coefficients to independent polynomial evaluation and check reciprocity and largest singular value. Passivity screen sigma_max <= 1 + 1e-10 assumes compatible power-normalized ports. The source provides no certified interval or uncertainty. Also evaluate 200 midpoints and report complex-linear interpolation error; use native polynomial instead of extrapolation. Sampled passivity is not continuous-band certification.

Preliminary independent coefficient evaluation found MMI maximum sigma about 0.99294 (0/201 nonpassive), directional coupler about 1.12758 (201/201 nonpassive), center 1.08738. These are preregistered expected findings, pending independent NumPy/SAX CI. Preserve the directional coupler unchanged but quarantine for passive network use; do not clip, normalize or interpret as optical gain. MMI is a candidate for conditional numerical use only, not measured or fabrication-qualified. This phase does not replace CIR meshes or solve WDM.

CI produces full complex JSON datasets (201×4×4×2 real/imag), metric CSVs and report; the exact exported files are preserved in the archive review branch below. Original coefficient files were committed in PR227. Historic LIB002 sidecars remain unchanged and describe their original evidence state. Current model status lives here, not in the historical v1 reference registry. No fabricated measurements or DRC.

## Verified CI results and archive preparation

[Run 44549140764](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44549140764) passed six checks. MMI max sigma 0.9929422282945128; directional coupler max sigma 1.1275809745127237, nonpassive 201/201. Native polynomial and reciprocity discrepancy zero for both; max midpoint complex-linear errors 0.0005772152585584936 and 0.0006252299617571072 respectively. Preserve both original datasets, including quarantined directional coupler. [Pinned artifact](archive-source.json): 14541764334, 75129 bytes. After PR228 merged, the manual workflow was run; for the procedure see [OPA archive LIB003 evidence](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/workflows/opa-archive-lib003.yml) on main with confirm_archive=true. Read-only preflight and permanent offline audit independently replay coefficients, sampled singular values, power and midpoint diagnostics from the exact archived bytes (stdlib only). Archive branch research/opa-lib003-evidence requires separate review. No measured data or continuous-band certification.

## Completed archive

[Archive run 44551216595](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44551216595) verified the original ZIP and staged Git bytes: 9 files, 709737 bytes, 6432 complex values. Archive commit `f696a17` has a LIB002 typo in its message; its contents and audit are LIB003. [Original ZIP](archive/original.zip) | [Datasets](archive/datasets/) | [Metrics](archive/metrics/) | [Report](archive/evidence/result.json) | [Provenance](archive/provenance.json). MMI remains conditional numerical only; directional coupler remains quarantined. No measured or continuous-band validity implied.
