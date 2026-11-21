const C = 299792458;
const TAU = 2 * Math.PI;
const CENTER_NM = 1550;
const GROUP_INDEX = 4.1;
const REFERENCE_RADIUS_UM = 10;
const SHIFT_NM_PER_V = 0.13;
const CAPACITANCE_FF = 20;
export const pairs = [[0, 0], [0, 1], [1, 0], [1, 1]];
export const gates = {AND: [3], OR: [1, 2, 3], XOR: [1, 2], NAND: [0, 1, 2]};
export const defaults = Object.freeze({
  radiusUm: 10, wavelengthNm: 1550, sourceMw: 0.30, gapNm: 200, intrinsicQ: 500000,
  trimNm: 0, voltageV: 4, routeLossDb: 0.5, pathPhaseDeg: 0, thresholdMw: 0.035, rateGhz: 10,
  wallPlug: 0.20, receiverFj: 100, driverFj: 40, overheadMw: 1
});
export const inputThresholdMw = 0.025;
const powerRatio = db => 10 ** (-db / 10);
const magnitude2 = ([re, im]) => re * re + im * im;
const multiply = ([ar, ai], [br, bi]) => [ar * br - ai * bi, ar * bi + ai * br];
const sumFields = fields => fields.reduce(([re, im], [x, y]) => [re + x, im + y], [0, 0]);

export function ring(p, drive = 0, laserNm = p.wavelengthNm) {
  // Local mode branch around the reference resonance. Radius sensitivity assumes
  // n_eff = 2.4 and n_g = 4.1, using dλ/dR = λ n_eff / (R n_g).
  const fsrGhz = C / (TAU * GROUP_INDEX * p.radiusUm * 1e-6) / 1e9;
  const resonanceNm = CENTER_NM - defaults.voltageV * SHIFT_NM_PER_V + CENTER_NM * (2.4 / GROUP_INDEX) *
    (p.radiusUm / REFERENCE_RADIUS_UM - 1) + p.trimNm + drive * SHIFT_NM_PER_V;
  const resonanceHz = C / (resonanceNm * 1e-9);
  const detuningGhz = (C / (laserNm * 1e-9) - resonanceHz) / 1e9;
  // Rates in κ/2π units. The two directional couplers are symmetric.
  const intrinsicGhz = resonanceHz / p.intrinsicQ / 1e9;
  const couplingGhz = 12 * Math.exp((200 - p.gapNm) / 65);
  const linewidthGhz = intrinsicGhz + 2 * couplingGhz;
  const half = linewidthGhz / 2;
  const denominator = half ** 2 + detuningGhz ** 2;
  const unitField = [half / denominator, detuningGhz / denominator];
  const drop = unitField.map(value => -couplingGhz * value);
  const through = [1 + drop[0], drop[1]];
  const absorbed = intrinsicGhz * couplingGhz / denominator;
  return {resonanceNm, fsrGhz, detuningGhz, linewidthGhz,
    loadedQ: resonanceHz / (linewidthGhz * 1e9), lifetimePs: 1000 / (TAU * linewidthGhz),
    through, drop, throughPower: magnitude2(through), dropPower: magnitude2(drop), absorbed,
    buildup: fsrGhz * couplingGhz / (TAU * denominator)};
}

export function evaluate(p, gate, a, b, opticalInputsMw = [a, b].map(bit => bit * p.sourceMw)) {
  const chosen = gates[gate];
  const link = powerRatio(p.routeLossDb);
  const drives = opticalInputsMw.map(power => power * link >= inputThresholdMw ? p.voltageV : 0);
  const r1 = ring(p, drives[0]);
  const r2 = ring(p, drives[1]);
  const probeAtRingMw = p.sourceMw * link;
  const tree = [r1.through, r1.drop].flatMap(parent =>
    [r2.through, r2.drop].map(child => multiply(parent, child)));
  const leafPowersMw = tree.map(field => magnitude2(field) * probeAtRingMw * link ** 2);
  // One row of a lossless symmetric k-port combiner with an optional relative path phase ramp.
  // Its orthogonal ports carry the rest of the selected power.
  const field = sumFields(chosen.map(index => {
    const radians = index * p.pathPhaseDeg * Math.PI / 180;
    return multiply(tree[index], [Math.cos(radians), Math.sin(radians)]);
  }));
  const selectedMw = chosen.reduce((sum, index) => sum + leafPowersMw[index], 0);
  const outputMw = magnitude2(field) * probeAtRingMw * link ** 2 / chosen.length;
  const unselectedMw = leafPowersMw.reduce((sum, power) => sum + power, 0) - selectedMw;
  const combinerOtherMw = Math.max(0, selectedMw - outputMw);
  const ringLossMw = probeAtRingMw * (r1.absorbed +
    (r1.throughPower + r1.dropPower) * link * r2.absorbed);
  const beforeCombinerMw = selectedMw + unselectedMw;
  const routeLossMw = Math.max(0, p.sourceMw - beforeCombinerMw - ringLossMw);
  const expected = Number(chosen.includes(2 * a + b));
  const observed = Number(outputMw >= p.thresholdMw);
  return {a, b, expected, observed, outputMw, opticalInputsMw, drives, r1, r2, leafPowersMw,
    probeAtRingMw, unselectedMw, combinerOtherMw, ringLossMw, routeLossMw,
    insertionLossDb: outputMw > 0 ? 10 * Math.log10(p.sourceMw / outputMw) : null};
}

export function truthTable(p, gate) {
  return pairs.map(([a, b]) => evaluate(p, gate, a, b));
}

export function energy(p, row) {
  // mW/GHz = pJ. Operation = one clock slot, with three powered receivers.
  const opticalInMw = p.sourceMw + row.opticalInputsMw[0] + row.opticalInputsMw[1];
  const opticalInFj = 1000 * opticalInMw / p.rateGhz;
  const opticalOutFj = 1000 * row.outputMw / p.rateGhz;
  const laserFj = opticalInFj / p.wallPlug;
  const ringEdgeFj = 0.5 * CAPACITANCE_FF * p.voltageV ** 2;
  // Independent, equiprobable decoded data bits give one transition every two slots.
  // A drives one ring and B drives both copies. This is an activity assumption.
  const link = powerRatio(p.routeLossDb);
  const switchingFj = p.sourceMw * link >= inputThresholdMw ? 1.5 * ringEdgeFj : 0;
  const driverFj = 2 * p.driverFj;
  const receiversFj = 3 * p.receiverFj;
  const otherFj = 1000 * p.overheadMw / p.rateGhz;
  const systemFj = laserFj + switchingFj + driverFj + receiversFj + otherFj;
  return {opticalInMw, opticalInFj, opticalOutFj, laserFj, ringEdgeFj, switchingFj, driverFj,
    receiversFj, otherFj, systemFj};
}

export function spectrum(p, drive) {
  const active = ring(p, drive);
  const span = Math.max(active.resonanceNm * active.linewidthGhz / (C / active.resonanceNm) * 4, 0.25);
  return Array.from({length: 121}, (_, i) => {
    const wavelengthNm = active.resonanceNm + (i / 60 - 1) * span;
    const sample = ring(p, drive, wavelengthNm);
    return {wavelengthNm, through: sample.throughPower, drop: sample.dropPower, loss: sample.absorbed};
  });
}
