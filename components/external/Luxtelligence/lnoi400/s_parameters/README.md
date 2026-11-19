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

CI produces full complex JSON datasets (201×4×4×2 real/imag), metric CSVs and report; exact exported files are not yet in main and will be archived after verification. Original coefficient files are already committed in this PR. Historic LIB002 sidecars remain unchanged and describe their original evidence state. Current model status lives here, not in the historical v1 reference registry. No fabricated measurements or DRC.
