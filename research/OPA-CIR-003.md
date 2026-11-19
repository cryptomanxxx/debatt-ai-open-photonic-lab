# OPA-CIR-003 — four-port electro-optic MZI core

CIR-002 passed 5/5 checks and 63 cases; maximum SAX difference 3.4989384658674724e-14, no passivity excess in either MMI or circuit. [Run 44513345216](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44513345216), [artifact 14522744683](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44513345216/artifacts/14522744683), ZIP SHA256 6272dc7414fa970ed7e8fe6f995a0a9c983c6660649bd8cc161695ee6c6bad10. This is numerical eligibility only.

## Hypothesis and scope

Reuse pinned lnoi400 MMI2x2, EO and TO compact models. Construct a four-port push-pull core using the topology and 5000 um modulation length of [LAYOUT-005](../results/opa-layout-005/result.json) and the 700 um heater default in [upstream cells](https://github.com/Luxtelligence/lxt_pdk_gf/blob/d16db6a4882657feb1ce696c16c604ff6cb7ccfa/lnoi400/cells.py). The actual layout uses reversed combiner, top splitter o3 / bottom o4, with combiner o1/o2 exposed. Thermal bias on the top (long branch at zero imbalance). Preserve reflections and native model phases. Opposite EO voltages, heater top only, bottom dummy TO section. No new component optimization.

This is deliberately a core abstraction, not full GDS extraction. The flattened layout has additional bends, tapers, bias routes and facet routing that are not represented; do not infer absolute chip insertion loss or phase. The upstream mzm_unbalanced compact model uses 1x2 MMIs, so it is not a four-port reference. Instead compare the identical explicit four-port netlist in SAX and OPA. Nominal 6.6 V push-pull Vpi comes from existing PDK model evaluation, not measurement. No arbitrary 2x2 unitary claim (theta only).

## Frozen tests

5 wavelengths 1540–1560 nm, 2 heater settings (0,1 V), 33 EO settings 0–13.2 V: 330 cases. Full complex 4x4 S, all entries and both incident-port power budgets; report reflection, transmission, unaccounted power and heater power based on upstream 25 ohm assumption. Maximum full-matrix SAX difference and reciprocity error <=1e-10. Require finite grid and central output power excursion >0.5 as a basic modulation control. Passivity of all blocks and core evaluated separately; block promotion if violated, never clip. Archive CSV and result with pinned model identity. No device measurement, RF bandwidth, system energy or fabrication claim.

Next: integrate routing/interface models where supported and add independent phase control for a programmable 2x2 building block before 4x4 mesh. 

## Recorded results

[Run 44514440625](https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/actions/runs/44514440625): 5/5 checks, 330 cases, SAX error 1.608206982491765e-11, reciprocity error 5.558049685633556e-16, zero passivity excess for components and core; passivity_eligible true. Central in1/out1 power range 0.000017495673080302988 to 0.9297678675132858. Artifact 14524464961, ZIP SHA256 c5787503483007e4e2458757c206c18f309b2882a7602d9ddb814598ba068ebd. Full artifact not yet permanently archived. Next [CIR-004](OPA-CIR-004.md).
