import assert from 'node:assert/strict';
import { test } from 'node:test';
import { compare, dot, infer, materials, opticalLayer, quantize, readCell, sampler, transmission, writeCell, writeFraction } from './model.mjs';

const ideal = { bits: 0, detectorBits: 0, loss: 0, noise: 0, drift: 0 };
const probe = { levels: 16, material: 'GST', readPower: 0.8, loss: 0, noise: 0, drift: 0, retention: 500 };
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-12, `${actual} != ${expected}`);

test('write threshold, partial update and all nominal binary and 4-bit levels', () => {
  assert.equal(writeFraction(0.1, 1), 0);
  assert.equal(writeCell(0.8, 0, 2, 1, 0.1), 0.8);
  close(writeCell(0, 1, 2, 0.575, 1), 0.5);
  for (const material of Object.keys(materials)) {
    for (const levels of [2, 16]) {
      for (let level = 0; level < levels; level++) {
        const state = writeCell(0, level, levels, 1, 1);
        assert.equal(readCell(state, 0, { ...probe, material, levels }).level, level);
        assert.equal(readCell(state, 0, { ...probe, material, levels, readPower: 0 }).level, null);
      }
    }
    assert.ok(transmission(0, material) > transmission(1, material));
  }
});

test('retention advances independently of read laser and loss reduces the detector signal', () => {
  const before = readCell(1, 0, probe);
  const off = readCell(1, 100, { ...probe, readPower: 0 });
  const later = readCell(1, 100, probe);
  assert.ok(later.t > before.t);
  assert.equal(later.aged, off.aged);
  assert.equal(later.t, off.t);
  close(readCell(1, 0, { ...probe, loss: 10 }).signal, before.signal / 10);
  assert.notEqual(readCell(0.5, 0, { ...probe, readPower: 0.10, noise: 0.12 }, 1).level, 8);
  assert.ok(readCell(0.5, 10, { ...probe, drift: 0.02 }).aged > readCell(0.5, 10, probe).aged);
});

test('signed optical encoding uses nonnegative power rails and agrees with independent dot products', () => {
  const random = sampler(1027);
  for (let i = 0; i < 100; i++) {
    const input = Array.from({ length: 4 }, random);
    const matrix = Array.from({ length: 4 }, () => Array.from({ length: 4 }, random));
    opticalLayer(matrix, input, ideal, random).forEach((row, j) => {
      assert.ok([...row.plus, ...row.minus].every(value => value >= 0));
      close(row.output, dot(matrix[j], input));
    });
  }
});

test('weight and detector precision, loss, saturation and sampled noise affect the modeled readout', () => {
  const input = [1, -1, 1, -1];
  assert.equal(quantize(0.5, 4), 4 / 7);
  assert.equal(quantize(-0.5, 4), -4 / 7);
  const [attenuated] = opticalLayer([[0.5, -0.5, 0, 0]], input, { ...ideal, bits: 4, loss: 10 }, () => 0);
  close(attenuated.output, 0.8 / 7);
  const [rounded] = opticalLayer([[0, 0, 0, 0]], input, { ...ideal, detectorBits: 4, noise: 0.3 }, () => -1);
  assert.equal(rounded.output, -4 / 7);
  const [saturated] = opticalLayer([[1, -1, 1, -1]], input, { ...ideal, noise: 0.1 }, () => 1);
  assert.equal(saturated.output, 4);
  assert.deepEqual(compare([0.75, -0.75], [1, -1], 4), { errors: [-0.25, 0.25], rms: 0.25, bits: 4 });
});

test('inference propagates detected electronic activations in the two numerical paths', () => {
  const matrices = [[[1, 1, 0, 0], [-1, 0, 0, 0]], [[-1, 1]], [[0.5], [-1]]];
  const x = [0.8, 0.6, 0, 0];
  const reference = infer(matrices, x, ideal, 'relu', () => 0);
  assert.deepEqual(reference[0].optical, [1, 0]);
  assert.deepEqual(reference[1].opticalIn, [1, 0]);
  assert.deepEqual(reference[1].optical, [0]);
  assert.deepEqual(reference[2].optical, [0, 0]);
  const noisy = infer(matrices, x, { ...ideal, loss: 3, drift: 0.25 }, 'tanh', () => 0);
  assert.ok(noisy[0].rms > 0);
  assert.deepEqual(noisy[1].opticalIn, noisy[0].optical);
  assert.ok(noisy[2].rms > 0);
  assert.deepEqual(noisy[2].reference, infer(matrices, x, ideal, 'tanh', () => 0)[2].optical);
});
