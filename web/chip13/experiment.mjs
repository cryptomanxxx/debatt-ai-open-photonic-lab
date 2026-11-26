import { readCell, sampler, transmission, writeCell, writeFraction } from '../opa-w/model.mjs';
import { action, bindControls, chart, chipLink, flow, fmt, frame, number, register, select, setField, slider, table } from '../opa-w/ui.mjs';

register('opa-weight-memory', root => {
  root.innerHTML = frame('Chip 13 · Photonic Weight Memory',
    'Program a phase-change cell, switch off the write laser, then probe the state with a read laser.',
    '<div class="ow-layout"><div class="ow-block">' +
    '<div class="ow-write">' + flow([['Write laser', 'laser'], ['Selected PCM cell', 'cell']], 'Write path from laser to the selected phase-change cell') + '</div>' +
    '<div class="ow-read">' + flow([['Read laser', 'laser'], ['Same PCM cell', 'cell'], ['Photodetector', 'detector']], 'Read path from the probe laser through the selected cell to the detector') + '</div>' +
    '<h3>Addressable cells</h3><p>Choose a cell. Its tile shows the intended level and the current modeled state as a fill bar.</p><div data-cells></div>' +
    '<div class="ow-actions">' + action('write', 'Write selected cell', true) + action('start', 'Start optical read') +
    action('stop', 'Stop lasers') + action('age', 'Advance 10 time units') + action('reset', 'Reset') +
    '</div><p class="ow-status" role="status"></p><div data-readout></div></div>' +
    '<div class="ow-block"><h3>Programming and readout</h3><div class="ow-fields">' +
    select('size', 'Array size', [[4, '4 × 4'], [8, '8 × 8']]) +
    select('levels', 'Storage mode', [[2, 'Binary · 2 levels'], [16, '4-bit · 16 levels']]) +
    select('material', 'Illustrative transmission profile', [['GST', 'GST example'], ['GSSe', 'GSSe example']]) +
    select('preset', 'Experiment', [['initial', 'Binary retention'], ['multilevel', '16-level read errors'], ['weak', 'Below the write threshold']]) +
    slider('target', 'Target level', 0, 1, 1, 1) +
    slider('intensity', 'Write intensity (normalized)', 0, 2, 0.05, 1) +
    slider('duration', 'Write duration (normalized)', 0, 2, 0.05, 1) +
    slider('readPower', 'Read intensity (normalized)', 0, 1, 0.01, 0.8) +
    slider('loss', 'Path loss (dB)', 0, 12, 0.25, 0) +
    slider('noise', 'Peak detector noise', 0, 0.12, 0.005, 0) +
    slider('drift', 'State drift strength', -0.04, 0.04, 0.002, 0) +
    slider('retention', 'Retention time constant (model units)', 5, 500, 5, 500) +
    '</div><h3>Compare all hypothetical levels</h3><div data-levels></div></div></div>' +
    '<details open><summary>What the components do</summary><p>A phase-change film can change how much light a waveguide transmits as regions of the film change between amorphous and crystalline states. The write pulse changes the modeled phase fraction. That fraction is stored when the write pulse ends. The read laser sends a probe and the photodetector measures the transmitted power.</p>' +
    '<p><code>Pout = Pin × 10^(−loss/10) × T</code>. Loss lowers the signal at the detector. Noise and closely spaced levels can make the decoded level differ from the intended level. Stop the lasers and advance the model clock to see retention and drift independently of reading.</p>' +
    '<p>GST and GSSe here are hypothetical profiles with invented coefficients and normalized pulses. Published GST optical programming and published electrically written GSSe with optical readout are described in <a href="https://doi.org/10.1038/nphoton.2015.182">Ríos et al.</a> and <a href="https://doi.org/10.1038/s41377-023-01213-3">Meng et al.</a>. This browser model has no material calibration.</p><p>Next, use a stored transmission to multiply an input in ' + chipLink('compute') + '.</p></details>');
  const status = root.querySelector('[role="status"]');
  const target = root.querySelector('[name="target"]');
  let cells;
  let selected;
  let clock;
  let mode = 'off';
  let sampleIndex = 0;
  let writeTimer;
  let readTimer;

  function options() {
    const values = Object.fromEntries(['levels', 'readPower', 'loss', 'noise', 'drift', 'retention'].map(name => [name, number(root, name)]));
    return { ...values, material: root.querySelector('[name="material"]').value };
  }

  function render() {
    const config = options();
    const probe = sampler(197 + sampleIndex);
    const readings = cells.map(cell => readCell(cell.state, clock - cell.writtenAt, config, probe()));
    const visibleCells = [...root.querySelectorAll('[data-action="cell"]')];
    visibleCells.forEach(button => {
      const i = Number(button.dataset.index);
      const cell = cells[i];
      button.style.setProperty('--ow-fill', (readings[i].aged * 100).toFixed(2) + '%');
      const intended = Math.round(cell.target * (config.levels - 1));
      button.textContent = intended;
      button.setAttribute('aria-pressed', String(i === selected));
      button.setAttribute('aria-label', 'Cell ' + (Math.floor(i / 8) + 1) + ', ' + (i % 8 + 1) + ', intended level ' + intended);
    });
    const cell = cells[selected];
    const read = readings[selected];
    const intended = Math.round(cell.target * (config.levels - 1));
    const readable = mode === 'read' && config.readPower > 0;
    const errors = visibleCells.filter(button => {
      const i = Number(button.dataset.index);
      return readings[i].level !== Math.round(cells[i].target * (config.levels - 1));
    }).length;
    root.querySelector('[data-readout]').innerHTML =
      table(['Measurement', 'Value'], [
        ['Model clock', clock + ' units'], ['Programmed phase fraction', fmt(cell.state)],
        ['Current phase fraction', fmt(read.aged)], ['Transmission T', fmt(read.t)],
        ['Detector power', readable ? fmt(read.signal) : '—'], ['Intended level', intended],
        ['Decoded level', readable ? read.level : '—'], ['Cells with read errors', readable ? errors + ' / ' + visibleCells.length : '—'],
      ]);
    root.querySelector('[data-levels]').innerHTML = chart(Array.from({ length: config.levels }, (_, i) =>
      ['Level ' + i, transmission(i / (config.levels - 1), config.material), i === intended ? 'alt' : '']), 1, 'Nominal cell transmission by level');
  }

  function setMode(next, message) {
    clearTimeout(writeTimer);
    clearInterval(readTimer);
    mode = next;
    root.dataset.mode = next;
    root.dataset.running = String(next !== 'off');
    status.textContent = message;
    render();
  }

  function stop() {
    if (mode === 'off') return;
    setMode('off', 'Lasers off. The programmed state is still stored.');
  }

  function buildGrid() {
    const size = number(root, 'size');
    root.querySelector('[data-cells]').innerHTML =
      '<div class="ow-grid ow-memory" style="--ow-columns:' + size + '">' +
      Array.from({ length: size ** 2 }, (_, i) => {
        const index = Math.floor(i / size) * 8 + i % size;
        return '<button class="btn" type="button" data-action="cell" data-index="' + index + '"></button>';
      }).join('') +
      '</div>';
  }

  function reset(preset = 'initial') {
    clearTimeout(writeTimer);
    clearInterval(readTimer);
    const multi = preset === 'multilevel';
    const weak = preset === 'weak';
    const fields = { size: 4, levels: multi ? 16 : 2, material: multi ? 'GSSe' : 'GST', target: multi ? 11 : 1,
      intensity: weak ? 0.1 : 1, duration: 1, readPower: multi ? 0.35 : 0.8, loss: multi ? 4 : 0,
      noise: multi ? 0.025 : 0, drift: 0, retention: 500, preset };
    target.max = fields.levels - 1;
    Object.entries(fields).forEach(([name, value]) => setField(root, name, value));
    selected = 0;
    clock = 0;
    sampleIndex = 0;
    cells = Array.from({ length: 64 }, (_, index) => {
      const row = Math.floor(index / 8);
      const column = index % 8;
      const state = multi && row < 4 && column < 4 ? (row * 4 + column) / 15 : 0;
      return { state, target: state, writtenAt: clock };
    });
    buildGrid();
    setMode('off', multi ? 'The array contains one of each level. Start optical read to compare the decoded levels.' :
      'Lasers off. Choose a cell and apply a write pulse.');
  }

  bindControls(root, field => {
    if (field.name === 'preset') {
      reset(field.value);
      return;
    }
    if (field.name === 'size') {
      const size = number(root, 'size');
      const row = Math.floor(selected / 8);
      const column = selected % 8;
      selected = Math.min(row, size - 1) * 8 + Math.min(column, size - 1);
      setField(root, 'target', Math.round(cells[selected].target * Number(target.max)));
      buildGrid();
    }
    if (field.name === 'levels') {
      const fraction = Number(target.value) / Number(target.max);
      target.max = Number(field.value) - 1;
      setField(root, 'target', Math.round(fraction * Number(target.max)));
    }
    render();
  }, (key, button) => {
    if (key === 'reset') return reset();
    if (key === 'stop') return stop();
    if (key === 'age') clock += 10;
    if (key === 'cell') {
      selected = Number(button.dataset.index);
      setField(root, 'target', Math.round(cells[selected].target * Number(target.max)));
    }
    if (key === 'write') {
      const cell = cells[selected];
      const config = options();
      const before = readCell(cell.state, clock - cell.writtenAt, config).aged;
      const level = number(root, 'target');
      const intensity = number(root, 'intensity');
      const duration = number(root, 'duration');
      const switched = writeFraction(intensity, duration) > 0;
      if (switched) {
        cell.state = writeCell(before, level, config.levels, intensity, duration);
        cell.writtenAt = clock;
      }
      cell.target = level / (config.levels - 1);
      setMode('write', switched ? 'Write pulse applied to the selected cell.' :
        'Pulse below the write threshold. The programmed state is unchanged.');
      writeTimer = setTimeout(stop, 1600);
    }
    if (key === 'start') {
      setMode('read', 'Read laser on. Write laser off. The stored state is unchanged by the probe.');
      readTimer = setInterval(() => { sampleIndex += 1; render(); }, 1200);
    }
    render();
  });

  reset();
  return { stop };
});
