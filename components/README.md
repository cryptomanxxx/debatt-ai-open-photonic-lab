# OPA Photonic Component Library

System-first, reuse-first registry for OPA-CIR. This initial release is a **reference catalog**, not an imported model package or a fabricated component library. It links existing evidence instead of copying the [GDS release archive](../gds/README.md) or the generated [chip design catalog](../catalog/README.md).

## Three views

- [External Components](external/README.md): third-party building blocks with pinned PDK provenance.
- [Experimentally Validated Components](experimentally_validated/README.md): published physical evidence, with explicit design/revision scope; currently no exact pinned-cell measurement certification.
- [Debatt-AI Components](debatt_ai/README.md): original research models, including negative results.

A component has one canonical ID in [registry.json](registry.json). Experimental evidence is a separate cross-reference, not a second component record or automatic promotion.

## Admission and evidence policy

Record origin, cell identity, platform, exact PDK revision, upstream source, license, local evidence, model type, scope and limitations. Keep geometry, DRC, simulation, measured data and process qualification separate: a parent layout DRC pass does not establish component model accuracy. A paper about a design family does not certify the current PDK revision. Unknown measurements and qualification are null. Never invent loss, phase, bandwidth or power values.

Before importing any third-party bytes check the specific file license, attribution and redistribution rights; a software MIT license does not automatically cover foundry data, all models, fabrication rights or NDA materials. Keep restricted data outside the public repo. Pin revisions and file hashes for imported artifacts. This release imports no third-party layout/model bytes.

## Circuit handoff

OPA-CIR-001 should start with an ideal MZI reference, then evaluate a pinned PDK component model. Before accepting a complex linear scattering model document port order, modes/polarization, reference planes, wavelength grid and units, complex normalization, phase convention, bias/temperature, provenance, validity range and uncertainty. Check passivity (where applicable), reciprocity (where applicable), reference-plane consistency and interpolation. Never infer phase from power-only curves. Model active electrical interfaces and nonlinear dynamics separately; never assign a fixed linear S matrix to C2. Do not connect different material/process platforms without a separately modeled and physically justified interface.

Use existing libraries first. Optimize or design a custom component only when a system-level requirement is unmet or a suitable verified model is unavailable. Prefer measured, revision-matched and process-qualified evidence. The present registry has no imported complex S dataset and no exact revision qualified for fabrication.

Run `python3 tools/check_component_library.py`. CI validates registry structure, references and conservative evidence claims; it does not simulate or measure components.

## Discovery backlog

CORNERSTONE, VTT and AIM Photonics are leads only; establish process, access, license and component-specific evidence before admission. No process choice or purchase is implied.
