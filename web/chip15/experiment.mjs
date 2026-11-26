import { infer, quantize, sampler } from '../opa-w/model.mjs';
import { action, bindControls, chart, chipLink, flow, fmt, frame, inputControls, matrixEditor, number, playback, precisionControls, register, select, setField, settings, slider, table, updateWeightButtons, vector } from '../opa-w/ui.mjs';

const examples = {
  features: {
    x: [0.65, -0.35, 0.5, 0.2],
    weights: [
      [[0.8, -0.4, 0.2, 0], [-0.5, 0.9, 0.1, 0.15], [0.1, 0.3, 0.65, -0.4], [0.35, -0.3, -0.2, 0.8]],
      [[0.7, -0.25, 0.35, 0.05], [-0.6, 0.9, 0.2, 0.55], [0.35, 0.45, -0.65, 0.7]],
      [[0.55, -0.25, 0.4], [-0.3, 0.8, 0.55]],
    ],
  },
  boundary: {
    x: [1, 0.4, -0.3, 0.15],
    weights: [
      [[0.7, 0.4, 0.1, 0.0], [0.55, 0.45, -0.2, 0.2], [-0.1, 0.65, 0.15, 0], [0.1, 0.2, 0.4, 0.7]],
      [[0.5, 0.4, 0, 0.05], [0.45, 0.5, 0.1, 0], [0.2, 0.1, 0.65, 0.4]],
      [[0.56, 0.17, 0.23], [0.33, 0.35, 0.26]],
    ],
  },
};

register('opa-stored-network', root => {
  root.innerHTML = frame('Chip 15 · Photonic Neural Network',
    'Run a four-input, two-output teaching network with three layers of locally stored weights and electronic activations between layers.',
    flow([['Input lasers', 'laser'], ['Stored W₁', 'cell'], ['Detector 1', 'detector'], ['Activation + re-encoding', 'electronic'],
      ['Stored W₂', 'cell'], ['Detector 2', 'detector'], ['Activation + re-encoding', 'electronic'], ['Stored W₃', 'cell'],
      ['Output detector', 'detector']], 'An optical multiply stage and detector are followed by electronic activation and optical re-encoding in each hidden layer. The last detector produces two scores.') +
    '<div class="ow-layout"><div class="ow-block"><h3>Program the network</h3><div class="ow-fields">' +
    select('layer', 'Layer to edit', [[0, 'Layer 1 · 4 → 4'], [1, 'Layer 2 · 4 → 3'], [2, 'Layer 3 · 3 → 2']]) +
    select('preset', 'Experiment', [['features', 'Layer-by-layer inference'], ['degraded', 'Error across layers'], ['boundary', 'Near a decision boundary']]) +
    '</div><div data-matrix></div>' + slider('weight', 'Selected weight', -1, 1, 0.01, 0.8) +
    '<div class="ow-fields">' + inputControls(examples.features.x) + '</div>' +
    '<div class="ow-actions">' + action('start', 'Run inference', true) + action('stop', 'Stop optical signal') +
    action('reset', 'Reset') + '</div><p class="ow-status" role="status"></p></div>' +
    '<div class="ow-block"><h3>Readout and activation</h3><div class="ow-fields">' +
    select('activation', 'Hidden-layer activation', [['relu', 'Clipped ReLU'], ['tanh', 'Tanh']]) +
    precisionControls(true) + '</div><div data-output></div></div></div>' +
    '<div class="ow-block"><h3>Follow the signal through the layers</h3><div data-layers></div><div data-chart></div></div>' +
    '<details open><summary>Where optics and electronics are used</summary><p>Each layer reads paired weight cells, sums powers, and takes their difference at the detector as in ' + chipLink('compute') +
    '. Hidden layers apply <code>tanh(z)</code> or <code>min(1, max(0, z))</code> electronically and re-encode those values onto light for the next layer. The final layer returns two comparison scores. This is a hybrid browser model with handcrafted matrices and no experimental validation.</p>' +
    '<p>' + chipLink('multilayer') + ' explores multilayer photonic computation. Chip 15 holds its weights in a stationary, nonvolatile-cell model and exposes weight quantization and contrast drift. Programmed weights stay available when illumination stops. The electronic reference follows the same network with the original weights. Layer errors include effects propagated from previous layers and can grow or shrink.</p></details>');
  let weights;
  let chosen = [0, 0];
  let seed = 419;
  const status = root.querySelector('[role="status"]');
  const player = playback(root, running => {
    status.textContent = running ? 'Inference readout active. Follow the detector and re-encoding stages.' :
      'Input lasers off. All layers retain their programmed weights.';
    render();
  });

  function showMatrix() {
    const layer = number(root, 'layer');
    chosen = [0, 0];
    root.querySelector('[data-matrix]').innerHTML = matrixEditor(weights[layer], 'Layer ' + (layer + 1) + ' weight');
    setField(root, 'weight', weights[layer][0][0]);
  }

  function render() {
    const config = settings(root, true);
    const input = [0, 1, 2, 3].map(i => number(root, 'x' + i));
    const mode = root.querySelector('[name="activation"]').value;
    const results = infer(weights, input, config, mode, sampler(seed));
    const layer = number(root, 'layer');
    updateWeightButtons(root, weights[layer], chosen,
      weights[layer].map(row => row.map(weight => quantize(weight, config.bits))), 'Layer ' + (layer + 1) + ' weight');
    const { optical, reference, errors } = results.at(-1);
    const winner = values => Math.abs(values[0] - values[1]) < 1e-12 ? 'Tie' : 'Output ' + (values[0] > values[1] ? '1' : '2');
    root.querySelector('[data-output]').innerHTML = '<h3>Inference scores</h3>' +
      table(['Score', 'Photonic', 'Electronic', 'Error'], optical.map((value, i) =>
        ['Output ' + (i + 1), fmt(value), fmt(reference[i]), fmt(errors[i])])) +
      '<p>Higher score · Photonic <b>' + winner(optical) + '</b> · Electronic <b>' + winner(reference) + '</b></p>';
    root.querySelector('[data-layers]').innerHTML =
      table(['Layer', 'Optical input', 'Detected linear', 'Electronic linear reference', 'Photonic output', 'Electronic output', 'RMS error'],
        results.map((result, index) => ['Layer ' + (index + 1), vector(result.opticalIn), vector(result.linear),
          vector(result.linearReference), vector(result.optical), vector(result.reference), fmt(result.rms)])) +
      '<p>Hidden-layer outputs are electronic activations. Layer 3 passes through the detector scores.</p>';
    root.querySelector('[data-chart]').innerHTML = chart(results.map((result, index) =>
      ['Layer ' + (index + 1) + ' RMS', result.rms, index === layer ? 'alt' : '']),
    Math.max(0.1, ...results.map(result => result.rms)), 'Error magnitude across layers on a shared scale');
  }

  function reset(preset = 'features') {
    const example = examples[preset] ?? examples.features;
    const degraded = preset === 'degraded';
    const boundary = preset === 'boundary';
    weights = example.weights.map(matrix => matrix.map(row => [...row]));
    seed = 419;
    const fields = { layer: 0, preset, activation: boundary ? 'tanh' : 'relu',
      bits: degraded || boundary ? 4 : 0, detectorBits: degraded || boundary ? 4 : 0,
      loss: degraded ? 3 : 0, noise: degraded ? 0.05 : 0, drift: degraded ? 0.22 : 0 };
    example.x.forEach((value, i) => { fields['x' + i] = value; });
    Object.entries(fields).forEach(([name, value]) => setField(root, name, value));
    showMatrix();
    player.stop();
    status.textContent = 'Input lasers off. Edit the stored weights or run inference.';
    render();
  }

  bindControls(root, field => {
    if (field.name === 'preset') return reset(field.value);
    if (field.name === 'layer') showMatrix();
    if (field.name === 'weight') weights[number(root, 'layer')][chosen[0]][chosen[1]] = Number(field.value);
    render();
  }, (key, button) => {
    if (key === 'reset') return reset();
    if (key === 'stop') return player.stop();
    if (key === 'start') { seed += 1; return player.start(); }
    chosen = [Number(button.dataset.row), Number(button.dataset.column)];
    setField(root, 'weight', weights[number(root, 'layer')][chosen[0]][chosen[1]]);
    render();
  });
  reset();
  return player;
});
