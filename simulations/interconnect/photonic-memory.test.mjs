import assert from 'node:assert/strict';
import test from 'node:test';
import {assumptions as a, defaults, evaluate, opticalLink, presets, presetSettings} from './photonic-memory-model.mjs';

const preset = id => presetSettings(presets.find(entry => entry.id === id));
const approx = (actual, expected) => assert.ok(Math.abs(actual - expected) <= Math.max(1e-12, Math.abs(expected) * 1e-10), `${actual} != ${expected}`);

test('405B streaming checkpoints fit one modeled layer and remain SSD limited', () => {
  const s = preset('airllm');
  const r = evaluate(s);
  assert.equal(r.totalGB,810);
  assert.equal(r.linkGB,810);
  assert.equal(r.ssdGB,810);
  assert.ok(r.stagingGB < r.vramAvailable);
  for (const key of ['electronic','photonic']) {
    assert.equal(r[key].metrics.bottleneck,'SSD');
    assert.ok(r[key].metrics.tokenSeconds >= 810 / (s.ssdGBs * a.ssdPayload));
  }
  assert.equal(evaluate({...s,vramGB:7}).electronic.metrics,null);
  assert.equal(evaluate({...s,ramGB:4}).photonic.metrics,null);
});

test('precision affects checkpoint size while context controls a separate KV budget', () => {
  for (const [precision,bits] of [['FP32',32],['FP16',16],['FP8',8],['4-bit',4]]) {
    const r = evaluate({...defaults,precision});
    assert.equal(r.totalGB,defaults.parametersB * bits / 8);
    approx(r.kvPeakGB,2 * defaults.layers * defaults.kvHeads * 128 * 2 * (defaults.context + defaults.tokens) / 1e9);
  }
  const r = evaluate({...defaults,context:131072});
  assert.equal(r.electronic.metrics,null);
  assert.match(r.electronic.blocked[0],/KV cache/);
});

test('RAM residency removes SSD reads; VRAM residency bypasses a failed optical link', () => {
  const cold = preset('ram');
  assert.ok(evaluate(cold).ssdGB > 0);
  const warm = evaluate({...cold,ramGB:64});
  assert.equal(warm.ssdGB,0);
  assert.ok(warm.electronic.metrics.tokenRate > evaluate(cold).electronic.metrics.tokenRate);
  const resident = evaluate({...defaults,vramGB:64,pumpMw:.1});
  assert.equal(resident.linkGB,0);
  assert.equal(resident.gpuResidentGB,resident.totalGB);
  assert.equal(resident.photonic.metrics.linkPj,null);
  assert.equal(resident.photonic.metrics.energy.link,0);
  assert.equal(resident.photonic.metrics.totalJ,resident.electronic.metrics.totalJ);
});

test('faster compute cannot remove the PCIe bottleneck; an optical link can move it to the controller', () => {
  const s = preset('pcie');
  const r = evaluate(s);
  approx(r.electronic.rawGBs,4);
  approx(r.electronic.payloadGBs,4 * 128 / 130 * .85);
  assert.equal(r.electronic.metrics.bottleneck,'PCIe');
  assert.ok(r.photonic.metrics.tokenRate > r.electronic.metrics.tokenRate);
  assert.equal(evaluate({...s,computeTops:10000}).electronic.metrics.bottleneck,'PCIe');
  assert.equal(evaluate({...s,controllerGBs:2}).photonic.metrics.bottleneck,'Memory controller');
  assert.equal(evaluate({...s,pcieGen:6,lanes:16}).electronic.rawGBs,128);
  assert.equal(evaluate({...s,pcieGen:1,lanes:1}).electronic.payloadGBs,2.5 / 8 * .8 * .85);
});

test('WDM shares laser power, checks spacing and bandwidth, and reports invalid links separately', () => {
  const s = preset('wdm');
  const one = opticalLink(s);
  const many = opticalLink({...s,channels:64});
  assert.equal(one.rawGBs,6.25);
  assert.equal(many.rawGBs,400);
  assert.equal(many.payloadGBs,340);
  assert.equal(many.wavelengthNm.length,64);
  assert.ok(many.wavelengthNm[0] > many.wavelengthNm.at(-1));
  approx(many.receivedUw * 64,one.receivedUw);
  approx(many.marginDb,10 * Math.log10(many.receivedUw / s.sensitivityUw));
  const broken = evaluate({...s,channels:64,pumpMw:.1,spacingGHz:10,combSpanTHz:.1});
  assert.equal(broken.optical.problems.length,3);
  assert.equal(broken.photonic.metrics,null);
  assert.ok(broken.electronic.metrics);
  assert.equal(evaluate(preset('ssd')).photonic.metrics.bottleneck,'SSD');
});

test('MoE distinguishes inventory, active weights, overfetch, and tier misses', () => {
  const s = preset('moe');
  const sparse = evaluate(s);
  const dense = evaluate({...s,workload:'Dense'});
  assert.equal(sparse.totalGB,dense.totalGB);
  assert.ok(sparse.activeGB < dense.activeGB);
  approx(sparse.linkGB,(sparse.totalGB - sparse.gpuResidentGB) * .12);
  approx(sparse.ssdGB,(sparse.totalGB - sparse.gpuResidentGB - sparse.hostResidentGB) * .12);
  assert.ok(sparse.ssdGB < sparse.linkGB && sparse.linkGB < dense.linkGB);
  assert.equal(evaluate({...s,residency:'Stream every layer',activePercent:100,readAmp:5}).linkGB,dense.totalGB);
});

test('timing and energy use separate weight, KV, compute and platform terms', () => {
  for (const p of presets) {
    const s = presetSettings(p);
    const r = evaluate(s);
    for (const path of [r.electronic,r.photonic]) {
      assert.ok(path.metrics, p.id);
      approx(path.metrics.answerSeconds,path.metrics.tokenSeconds * s.tokens);
      approx(path.metrics.tokenRate,1 / path.metrics.tokenSeconds);
      approx(path.metrics.totalJ,Object.values(path.metrics.energy).reduce((sum,value) => sum + value,0));
      approx(path.metrics.energy.link,path.metrics.linkPj * r.linkGB * 8e9 * s.tokens * 1e-12);
      assert.ok(path.metrics.transferSeconds >= Math.max(...path.stages.map(stage => stage.seconds)));
    }
    approx(r.photonic.metrics.energy.link,
      (s.modulatorPj + s.detectorPj + s.eoPj + s.oePj) / a.wdmPayload * r.linkGB * 8e9 * s.tokens * 1e-12 +
      (s.pumpMw / 1000 / a.laserEfficiency + a.opticalBiasW) * r.photonic.metrics.answerSeconds);
  }
});
