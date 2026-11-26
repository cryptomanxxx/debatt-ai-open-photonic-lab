export const limit = (value, min, max) => Math.max(min, Math.min(max, value));
export const materials = Object.freeze({
  GST: Object.freeze({ floor: 0.24, span: 0.57, curve: 1.25 }),
  GSSe: Object.freeze({ floor: 0.40, span: 0.50, curve: 0.90 }),
});

const powerRatio = db => 10 ** (-db / 10);

export function transmission(state, material) {
  const { floor, span, curve } = materials[material];
  return floor + span * (1 - state) ** curve;
}

export function writeFraction(intensity, duration) {
  return limit((intensity * duration - 0.15) / 0.85, 0, 1);
}

export function writeCell(previous, level, levels, intensity, duration) {
  const target = level / (levels - 1);
  const fraction = writeFraction(intensity, duration);
  return fraction === 1 ? target : previous + (target - previous) * fraction;
}

export function readCell(state, age, options, noiseSample = 0) {
  const retained = state * Math.exp(-age / options.retention);
  const aged = limit(retained + options.drift * Math.log1p(age), 0, 1);
  const t = transmission(aged, options.material);
  const incident = options.readPower * powerRatio(options.loss);
  const signal = Math.max(0, incident * t + options.noise * noiseSample);
  const { floor, span, curve } = materials[options.material];
  const estimated = incident > 0 ? 1 - limit((signal / incident - floor) / span, 0, 1) ** (1 / curve) : null;
  return { aged, t, signal, level: estimated === null ? null : Math.round(estimated * (options.levels - 1)) };
}

// Symmetric sign-magnitude coding. Code zero is shared across both signs.
export function quantize(value, bits, fullScale = 1) {
  if (!bits) return value;
  const steps = 2 ** (bits - 1) - 1;
  const scaled = limit(Math.abs(value) / fullScale, 0, 1);
  return Math.sign(value) * Math.round(scaled * steps) * fullScale / steps || 0;
}

export function dot(weights, inputs) {
  return weights.reduce((sum, weight, i) => sum + weight * inputs[i], 0);
}

export function opticalLayer(matrix, input, { bits, detectorBits, loss, noise, drift }, sample) {
  const factor = powerRatio(loss);
  return matrix.map(row => {
    const stored = row.map(weight => quantize(weight, bits));
    // Higher programmed contrast fades more in this illustrative drift setting.
    const effective = stored.map(weight => weight * (1 - drift * Math.abs(weight)));
    const plus = [];
    const minus = [];
    effective.forEach((weight, i) => {
      const xPositive = Math.max(0, input[i]);
      const xNegative = Math.max(0, -input[i]);
      const tPositive = Math.max(0, weight);
      const tNegative = Math.max(0, -weight);
      plus.push(factor * (xPositive * tPositive + xNegative * tNegative));
      minus.push(factor * (xPositive * tNegative + xNegative * tPositive));
    });
    const products = plus.map((p, i) => p - minus[i]);
    const sum = products.reduce((total, product) => total + product, 0);
    const analog = limit(sum + noise * sample(), -row.length, row.length);
    return { stored, plus, minus, products, sum, output: quantize(analog, detectorBits, row.length) };
  });
}

// Repeatable, bounded independent samples for successive detections.
export function sampler(seed) {
  let state = Math.imul(seed, 0x9e3779b1) >>> 0;
  return () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 2 ** 31 - 1;
  };
}

export function compare(actual, reference, fullScale) {
  const errors = actual.map((value, i) => value - reference[i]);
  const rms = Math.hypot(...errors) / Math.sqrt(errors.length);
  // Error-based agreement estimate for this particular vector, not ADC ENOB.
  const bits = rms === 0 ? Infinity : Math.max(0, Math.log2(fullScale / rms));
  return { errors, rms, bits };
}

function activation(value, mode) {
  return mode === 'tanh' ? Math.tanh(value) : limit(value, 0, 1);
}

export function infer(matrices, input, settings, mode, sample) {
  let optical = input;
  let reference = input;
  return matrices.map((matrix, index) => {
    const opticalIn = optical;
    const rows = opticalLayer(matrix, opticalIn, settings, sample);
    const linear = rows.map(row => row.output);
    const linearReference = matrix.map(row => dot(row, reference));
    const last = index === matrices.length - 1;
    optical = last ? linear : linear.map(value => activation(value, mode));
    reference = last ? linearReference : linearReference.map(value => activation(value, mode));
    return { opticalIn, linear, linearReference, optical, reference, ...compare(optical, reference, last ? matrix[0].length : 1) };
  });
}
