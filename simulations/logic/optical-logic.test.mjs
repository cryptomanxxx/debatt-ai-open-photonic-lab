import test from 'node:test';
import assert from 'node:assert/strict';
import {defaults, energy, evaluate, ring, spectrum, truthTable} from './optical-logic-model.mjs';

const close = (actual, expected, tolerance=1e-10) =>
  assert.ok(Math.abs(actual-expected)<tolerance,`${actual} differs from ${expected}`);
const expected = {AND:[0,0,0,1], OR:[0,1,1,1], XOR:[0,1,1,0], NAND:[1,1,1,0]};

test('physical detector outputs reproduce all four truth tables at the nominal point', () => {
  for (const [gate,bits] of Object.entries(expected)) {
    assert.deepEqual(truthTable(defaults,gate).map(row=>row.observed),bits);
  }
  const nand=evaluate(defaults,'NAND',0,0);
  assert.deepEqual(nand.opticalInputsMw,[0,0]);
  assert.ok(nand.outputMw>defaults.thresholdMw);
});

test('the passive ring conserves power and gives a drop peak on resonance', () => {
  const nominal=ring(defaults,defaults.voltageV);
  for (const gapNm of [130,200,330]) {
    for (const intrinsicQ of [10000,500000,800000]) {
      for (const sample of spectrum({...defaults,gapNm,intrinsicQ},0)) {
        close(sample.through+sample.drop+sample.loss,1);
        assert.ok(sample.through>=0 && sample.drop>=0 && sample.loss>=0);
      }
    }
  }
  assert.ok(nominal.dropPower>.95);
  assert.ok(nominal.throughPower<.001);
  assert.ok(nominal.dropPower>ring(defaults).dropPower);
  assert.ok(ring({...defaults,gapNm:300}).linewidthGhz<nominal.linewidthGhz);
  assert.ok(ring({...defaults,radiusUm:10.01}).resonanceNm>ring(defaults).resonanceNm);
  assert.ok(ring({...defaults,intrinsicQ:10000}).absorbed>ring(defaults).absorbed);
});

test('the full probe power budget conserves flux, including combiner dumps', () => {
  for (const gate of Object.keys(expected)) {
    for (const routeLossDb of [0,.5,6]) {
      for (const pathPhaseDeg of [-180,-45,0,90]) {
        for (const r of truthTable({...defaults,routeLossDb,pathPhaseDeg},gate)) {
          close(r.outputMw+r.combinerOtherMw+r.unselectedMw+r.routeLossMw+r.ringLossMw,defaults.sourceMw);
          assert.ok(r.routeLossMw>-1e-12);
        }
      }
    }
  }
});

test('turning off drive or starving the input receiver disables data routing', () => {
  const noDrive=truthTable({...defaults,voltageV:0},'AND');
  assert.ok(noDrive.every(r=>r.outputMw===noDrive[0].outputMw));
  const dark=evaluate({...defaults,sourceMw:.015},'AND',1,1);
  assert.deepEqual(dark.drives,[0,0]);
  assert.equal(dark.observed,0);
  const externallyRouted=evaluate(defaults,'XOR',1,0,[.002,0]);
  assert.deepEqual(externallyRouted.drives,[0,0]);
  assert.equal(externallyRouted.observed,0);
});

test('energy counts wall-plug input, electronics and switching exactly once', () => {
  const e=energy(defaults,evaluate(defaults,'AND',1,1));
  close(e.opticalInFj,90);
  close(e.ringEdgeFj,160);
  close(e.switchingFj,240);
  close(e.laserFj,450);
  close(e.systemFj,1170);
  const weak={...defaults,sourceMw:.01};
  assert.equal(energy(weak,evaluate(weak,'AND',1,1)).switchingFj,0);
});
