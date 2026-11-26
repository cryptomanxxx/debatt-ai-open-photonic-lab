'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {defaults, intersection, bounds, compare, rays, opticalSide} = require('./model.js');

test('forward slab reference handles geometric edge cases', () => {
  const min = [0, 0];
  const max = [2, 2];
  assert.deepEqual(intersection([-1, 1], [1, 0], min, max), {entry:1, exit:3});
  assert.deepEqual(intersection([3, 1], [-1, 0], min, max), {entry:1, exit:3});
  assert.deepEqual(intersection([1, 1], [0, 1], min, max), {entry:0, exit:1});
  assert.deepEqual(intersection([-1, 1], [1, -1], min, max), {entry:1, exit:1});
  assert.deepEqual(intersection([-1, 1], [1, 0], [1, 1], [1, 1]), {entry:2, exit:2});
  assert.equal(intersection([-1, 3], [1, 0], min, max), null);
  assert.equal(intersection([-1, 1], [-1, 0], min, max), null);
  assert.equal(intersection([1, 1], [0, 0], min, max), null);
});

test('slab result matches independent ray/segment checks on seeded scenes', () => {
  let state = 259;
  const random = () => (state = (Math.imul(1664525, state) + 1013904223) >>> 0) / 2 ** 32;
  const cross = (a,b) => a[0]*b[1] - a[1]*b[0];
  for (let i = 0; i < 2000; i++) {
    const origin = [16*random()-8, 10*random()-5];
    const angle = 2*Math.PI*random();
    const direction = [Math.cos(angle), Math.sin(angle)];
    const {min,max} = bounds({x:10*random()-5,y:6*random()-3,w:.4+4*random(),h:.4+3*random()});
    const corners = [min, [max[0],min[1]], max, [min[0],max[1]]];
    const inside = origin.every((value,axis) => value >= min[axis] && value <= max[axis]);
    const intersects = corners.some((p,index) => {
      const q = corners[(index+1)%4];
      const edge = [q[0]-p[0], q[1]-p[1]];
      const delta = [p[0]-origin[0], p[1]-origin[1]];
      const denominator = cross(direction,edge);
      const t = cross(delta,edge)/denominator;
      const u = cross(delta,direction)/denominator;
      return t >= 0 && u >= 0 && u <= 1;
    });
    assert.equal(Boolean(intersection(origin,direction,min,max)), inside || intersects);
  }
});

test('proxy presets demonstrate both error types and finer precision resolves center ray', () => {
  const cases = [[1.15,1,'fp'], [-2,6,'fn']];
  for (const [y,angle,status] of cases) {
    const settings = {...defaults,y,angle,bits:1};
    const result = rays(settings,settings.a);
    assert.equal(result.length,5);
    assert.equal(result[2].status,status);
    assert.equal(rays({...settings,bits:12},settings.a)[2].status,status === 'fp' ? 'miss' : 'hit');
  }
  assert.equal(compare([1.49,0],[1,0],{x:1,y:0,w:1,h:1},4).exact.entry,0);
});

test('normalized coherent readout preserves positive, negative and zero in reference cases', () => {
  for (const [point,expected] of [[[1,1],1],[[1,-1],-1],[[5,0],0]]) {
    const report = opticalSide([0,0],[1,0],point);
    assert.equal(Math.sign(report.side),expected);
    assert.equal(Math.sign(report.delta),expected);
    assert.equal(report.field,1+report.branch1+report.branch2);
  }
});
