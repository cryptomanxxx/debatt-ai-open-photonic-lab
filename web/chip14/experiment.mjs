import { compare, dot, opticalLayer, sampler } from '../opa-w/model.mjs';
import { action, bindControls, chart, chipLink, flow, fmt, frame, inputControls, matrixEditor, number, playback, precisionControls, register, select, setField, settings, slider, table, updateWeightButtons, vector } from '../opa-w/ui.mjs';

const examples = {
  identity: { x: [0.75, -0.5, 0.25, 1], w: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]] },
  signed: { x: [0.8, -0.5, 0.25, 0.2], w: [[0.5, -0.8, 0, 0.2], [0, 0.4, -0.6, 1], [-0.75, 0, 1, 0.4], [0.2, 0.3, -0.3, 0.6]] },
};

register('opa-in-memory', root => {
  root.innerHTML = frame('Chip 14 · Photonic In-Memory Computing',
    'Multiply an input vector by a matrix of weights stored locally in optical cells.',
    '<div class="ow-layout"><div class="ow-block">' +
    flow([['Input lasers', 'laser'], ['Stored W⁺ / W⁻', 'cell'], ['Sum P⁺ / P⁻', 'cell'], ['Detector subtraction', 'detector']],
      'Intensity-coded inputs illuminate paired weight cells. Independent powers are added on two rails and subtracted after detection.') +
    '<h3><code>y = W × x</code></h3><p>Each row emits one output. Click a cell to program its signed weight. The tiles show the programmed values.</p>' +
    matrixEditor(examples.identity.w, 'Weight') +
    slider('weight', 'Selected weight', -1, 1, 0.01, 1) +
    '<div class="ow-actions">' + action('start', 'Start optical signal', true) + action('stop', 'Stop optical signal') +
    action('reset', 'Reset') + '</div><p class="ow-status" role="status"></p><div data-result></div></div>' +
    '<div class="ow-block"><h3>Inputs and readout</h3><div class="ow-fields">' +
    select('preset', 'Experiment', [['identity', 'Identity pass-through'], ['signed', 'Signed multiplication'], ['coarse', 'Coarse detector and loss']]) +
    inputControls(examples.identity.x) + precisionControls(false) +
    '</div><h3>Inspect the four products for one output</h3><div data-products></div><div data-chart></div></div></div>' +
    '<details open><summary>From memory interconnect to local computation</summary><p>' + chipLink('interconnect') +
    ' streams weights from electronic memory over a link. ' + chipLink('memory') +
    ' programs a cell and reads its transmission. Here the input passes through two cells per signed weight. Two complementary input rails also encode signed inputs. Summing each rail as independent powers and subtracting gives each signed product. A photodetector converts the resulting powers to electrical signals.</p>' +
    '<p>For output i, <code>yᵢ = Σⱼ Wᵢⱼxⱼ</code>. The electronic reference uses the requested weights without quantization. The optical model rounds stored weights, attenuates each path, adds bounded detector noise, then rounds the differential readout. Agreement bits use RMS error relative to full scale for this input vector.</p><p>Continue to ' + chipLink('network') + ' to feed one layer into another.</p></details>');
  let weights;
  let chosen;
  let seed = 311;
  const status = root.querySelector('[role="status"]');
  const player = playback(root, running => {
    status.textContent = running ? 'Input lasers on. Detectors receive the two power sums.' : 'Input lasers off. The matrix stays programmed.';
    render();
  });

  function render() {
    const input = [0, 1, 2, 3].map(i => number(root, 'x' + i));
    const rows = opticalLayer(weights, input, settings(root), sampler(seed));
    const actual = rows.map(row => row.output);
    const reference = weights.map(row => dot(row, input));
    const error = compare(actual, reference, 4);
    const rowIndex = chosen[0];
    const row = rows[rowIndex];
    updateWeightButtons(root, weights, chosen, rows.map(value => value.stored), 'Weight');
    root.querySelector('[data-result]').innerHTML = table(['Output', 'Photonic', 'Electronic', 'Error'],
      actual.map((value, i) => ['y' + (i + 1), fmt(value), fmt(reference[i]), fmt(error.errors[i])])) +
      '<p>RMS error <b>' + fmt(error.rms) + '</b> · Agreement bits <b>' +
      (Number.isFinite(error.bits) ? error.bits.toFixed(2) : 'Exact for this vector') + '</b></p>';
    root.querySelector('[data-products]').innerHTML = table(['Input', 'W stored', 'P⁺', 'P⁻', 'Product'],
      row.products.map((value, i) => ['x' + (i + 1) + ' = ' + fmt(input[i]), fmt(row.stored[i]),
        fmt(row.plus[i]), fmt(row.minus[i]), fmt(value)])) +
      '<code class="ow-equation">y' + (rowIndex + 1) + ' = Σ(P⁺ − P⁻) = ' + fmt(row.sum) +
      ' before detector noise and rounding</code><p>Input vector ' + vector(input) + '</p>';
    root.querySelector('[data-chart]').innerHTML = chart([
      ['Photonic y' + (rowIndex + 1), actual[rowIndex], ''], ['Electronic y' + (rowIndex + 1), reference[rowIndex], 'alt'],
    ], 4, 'Selected output magnitude comparison');
  }

  function reset(preset = 'identity') {
    const example = examples[preset] ?? examples.signed;
    weights = example.w.map(row => [...row]);
    chosen = [0, 0];
    seed = 311;
    const coarse = preset === 'coarse';
    const fields = { preset, weight: weights[0][0], bits: coarse ? 4 : 0, detectorBits: coarse ? 4 : 0,
      loss: coarse ? 4 : 0, noise: coarse ? 0.04 : 0 };
    example.x.forEach((value, i) => { fields['x' + i] = value; });
    Object.entries(fields).forEach(([name, value]) => setField(root, name, value));
    player.stop();
    status.textContent = 'Input lasers off. Change a setting to update the numerical preview.';
    render();
  }

  bindControls(root, field => {
    if (field.name === 'preset') return reset(field.value);
    if (field.name === 'weight') weights[chosen[0]][chosen[1]] = Number(field.value);
    render();
  }, (key, button) => {
    if (key === 'reset') return reset();
    if (key === 'stop') return player.stop();
    if (key === 'start') { seed += 1; return player.start(); }
    chosen = [Number(button.dataset.row), Number(button.dataset.column)];
    setField(root, 'weight', weights[chosen[0]][chosen[1]]);
    render();
  });
  reset();
  return player;
});
