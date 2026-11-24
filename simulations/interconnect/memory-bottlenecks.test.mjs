import assert from 'node:assert/strict';
import test from 'node:test';
import {assumptions, evaluate} from './photonic-memory-model.mjs';
import {cases, compare} from './memory-bottlenecks.mjs';

const caseById = id => cases.find(entry => entry.id === id);
const run = id => compare(caseById(id));
const close = (actual, expected, tolerance = 1e-9) => assert.ok(
  Math.abs(actual - expected) <= tolerance * Math.max(1,Math.abs(expected)), `${actual} ≠ ${expected}`);

test('transport substitution at matched payload leaves only propagation in the time difference', () => {
  const inputs = caseById('dense-link-limited');
  const r = compare(inputs);
  const base = evaluate(inputs.settings);
  close(r.electronic.payloadGBs,r.matchedWdm.payloadGBs);
  close(r.electronic.metrics.tokenSeconds,base.electronic.metrics.tokenSeconds);
  close(r.matchedWdm.metrics.tokenSeconds - r.electronic.metrics.tokenSeconds,
    base.optical.flightSeconds * inputs.settings.layers);
  assert.ok(r.widerWdm.speedupVsPcie > 1);
  assert.equal(r.electronic.metrics.bottleneck,'PCIe');
});

test('storage, host RAM, the controller and accelerator ingress independently cap a faster link', () => {
  for (const [id, bottleneck] of [
    ['dense-ssd-limited','SSD'],['dense-host-ram-limited','Host RAM'],
    ['dense-controller-limited','Memory controller'],['dense-ingress-limited','Accelerator ingress'],
  ]) {
    const r = run(id);
    assert.equal(r.electronic.metrics.bottleneck,bottleneck);
    assert.equal(r.widerWdm.metrics.bottleneck,bottleneck);
    close(r.widerWdm.speedupVsPcie,1,1e-5);
  }
  const r = run('dense-ingress-limited');
  close(r.electronic.metrics.effectiveGBs,r.ingressGBs);
  close(r.electronic.metrics.ingressSeconds,r.linkGBPerToken / r.ingressGBs);
  assert.equal(run('dense-long-context').widerWdm.metrics.bottleneck,'Local weight reads');
});

test('sparse activity and overfetch preserve the checkpoint inventory and peak KV size', () => {
  const sparse = run('moe-tiered');
  const dense = run('moe-dense-control');
  const amplified = run('moe-with-overfetch');
  assert.equal(sparse.checkpointGB,dense.checkpointGB);
  assert.ok(sparse.activeWeightGB < dense.activeWeightGB);
  assert.equal(sparse.activeWeightGB,amplified.activeWeightGB);
  assert.equal(sparse.kvPeakGB,dense.kvPeakGB);
  assert.ok(sparse.linkGBPerToken < amplified.linkGBPerToken && amplified.linkGBPerToken < dense.linkGBPerToken);
});

test('an unused optical path costs nothing while a required failed path stays blocked', () => {
  const resident = run('dense-vram-resident');
  assert.equal(resident.linkGBPerToken,0);
  assert.equal(resident.widerWdm.metrics.energy.link,0);
  assert.equal(resident.widerWdm.speedupVsPcie,1);
  assert.equal(resident.widerWdm.breakEvenOpticalDynamicPjPerPayloadBit,null);
  const failed = run('dense-optical-power-failure');
  assert.ok(failed.electronic.metrics);
  assert.equal(failed.widerWdm.metrics,null);
  assert.equal(failed.matchedWdm.speedupVsPcie,null);
});

test('ingress adds static energy and the break-even value solves system energy equality', () => {
  const inputs = caseById('dense-ingress-limited');
  const base = evaluate(inputs.settings);
  const r = compare(inputs), optical = r.widerWdm.metrics;
  const extra = optical.answerSeconds - base.photonic.metrics.answerSeconds;
  close(optical.energy.platform - base.photonic.metrics.energy.platform,extra * assumptions.platformW);
  const opticalFixedW = inputs.settings.pumpMw / 1000 / assumptions.laserEfficiency + assumptions.opticalBiasW;
  close(optical.energy.link - base.photonic.metrics.energy.link,extra * opticalFixedW);
  const dynamicLinePj = r.widerWdm.breakEvenOpticalDynamicPjPerPayloadBit * assumptions.wdmPayload;
  assert.ok(dynamicLinePj > 0);
  const breakEven = compare({...inputs,settings:{...inputs.settings,modulatorPj:dynamicLinePj,detectorPj:0,eoPj:0,oePj:0}});
  close(breakEven.widerWdm.systemEnergyRatioVsPcie,1);
  for (const ingressGBs of [0,-1,Infinity,NaN]) {
    assert.throws(() => compare({...inputs,ingressGBs}),RangeError);
  }
});
