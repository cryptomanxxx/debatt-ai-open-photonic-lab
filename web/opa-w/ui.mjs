const linked = {
  network: ['stored-weight-network', 'Chip 15 · Photonic Neural Network', '../chip15/'],
  compute: ['in-memory-computing', 'Chip 14 · Photonic In-Memory Computing', '../chip14/'],
  memory: ['weight-memory', 'Chip 13 · Photonic Weight Memory', '../chip13/'],
  interconnect: ['photonic-memory', 'Chip 12 · Photonic Memory Interconnect'],
  multilayer: ['multilayer', 'Chip 9 · Multilayer Photonic Neural Network'],
};

export function chipLink(name) {
  const [key, title, standalone] = linked[name];
  const hash = '#photonic-circuit-lab/' + key;
  const site = 'https://debatt-ai-open-photonic-lab.mr-marcus-sweden.chatgpt.site/';
  const href = document.getElementById('pulse-design') ? hash : standalone ?? site + hash;
  return '<a href="' + href + '">' + title + '</a>';
}

export const fmt = value => Math.abs(value) < 0.00005 ? '0.0000' : value.toFixed(4);
export const vector = values => '[' + values.map(fmt).join(', ') + ']';

export function slider(key, label, min, max, step, value) {
  return '<label class="ow-control"><span>' + label + ' <output data-value="' + key + '">' + value +
    '</output></span><input name="' + key + '" type="range" min="' + min + '" max="' + max +
    '" step="' + step + '" value="' + value + '"></label>';
}

export function select(key, label, options) {
  return '<label class="ow-control"><span>' + label + '</span><select name="' + key + '">' +
    options.map(([value, title]) => '<option value="' + value + '">' + title + '</option>').join('') +
    '</select></label>';
}

export function action(key, label, primary = false) {
  return '<button class="btn' + (primary ? ' primary' : '') + '" type="button" data-action="' + key + '">' + label + '</button>';
}

export function flow(stages, label) {
  return '<div class="ow-flow" role="img" aria-label="' + label + '">' +
    stages.map(([name, kind], i) => '<span class="ow-node ow-' + kind + '" style="--ow-stage:' + i + '">' + name + '</span>').join('') + '</div>';
}

export function chart(values, fullScale, label) {
  return '<div class="ow-chart" role="group" aria-label="' + label + '">' + values.map(([name, value, tone]) =>
    '<div class="ow-series ' + tone + '"><span>' + name + '</span><meter min="0" max="' + fullScale +
    '" value="' + Math.min(fullScale, Math.abs(value)) + '" aria-label="' + name + ' magnitude"></meter><b>' +
    fmt(value) + '</b></div>').join('') + '</div>';
}

export function table(headers, rows) {
  return '<div class="ow-table" tabindex="0" role="region" aria-label="Numerical results"><table><thead><tr>' +
    headers.map(header => '<th scope="col">' + header + '</th>').join('') + '</tr></thead><tbody>' +
    rows.map(([label, ...values]) => '<tr><th scope="row">' + label + '</th>' +
      values.map(value => '<td>' + value + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
}

export function frame(title, description, content) {
  return '<section class="ow-lab card"><header><h2>' + title + '</h2><p>' + description + '</p></header>' +
    content + '</section>';
}

export function bindControls(root, onInput, onAction) {
  root.addEventListener('input', event => {
    const field = event.target;
    if (!field.name) return;
    const value = root.querySelector('[data-value="' + field.name + '"]');
    if (value) value.textContent = field.value;
    onInput(field);
  });
  root.addEventListener('click', event => {
    const button = event.target.closest('[data-action]');
    if (button) onAction(button.dataset.action, button);
  });
}

export function setField(root, name, value) {
  const field = root.querySelector('[name="' + name + '"]');
  field.value = value;
  const output = root.querySelector('[data-value="' + name + '"]');
  if (output) output.textContent = value;
}

export function number(root, name) {
  return Number(root.querySelector('[name="' + name + '"]').value);
}

export function precisionControls(drift) {
  return select('bits', 'Weight precision', [[0, 'Continuous idealization'], [2, '2 bits'], [4, '4 bits'], [8, '8 bits']]) +
    select('detectorBits', 'Detector precision', [[0, 'Continuous idealization'], [4, '4 bits'], [8, '8 bits'], [12, '12 bits']]) +
    slider('loss', 'Optical loss (dB)', 0, 12, 0.25, 0) +
    slider('noise', 'Peak detector noise', 0, 0.2, 0.005, 0) +
    (drift ? slider('drift', 'Memory drift strength', 0, 0.5, 0.01, 0) : '');
}

export function settings(root, drift = false) {
  return {
    bits: number(root, 'bits'),
    detectorBits: number(root, 'detectorBits'),
    loss: number(root, 'loss'),
    noise: number(root, 'noise'),
    drift: drift ? number(root, 'drift') : 0,
  };
}

export function matrixEditor(matrix, prefix) {
  return '<div class="ow-grid ow-weights" style="--ow-columns:' + matrix[0].length + '">' +
    matrix.map((row, r) => row.map((weight, c) =>
      action('weight', fmt(weight), false).replace('data-action="weight"', 'data-action="weight" data-row="' +
        r + '" data-column="' + c + '" aria-label="' + prefix + ' row ' + (r + 1) + ', column ' + (c + 1) +
        ', weight ' + fmt(weight) + '"')).join('')).join('') + '</div>';
}

export function updateWeightButtons(root, matrix, selected, programmed, prefix) {
  root.querySelectorAll('[data-action="weight"]').forEach(button => {
    const { row, column } = button.dataset;
    const weight = matrix[row][column];
    const stored = programmed[row][column];
    button.textContent = fmt(stored);
    button.dataset.sign = Math.sign(stored);
    button.setAttribute('aria-pressed', String(Number(row) === selected[0] && Number(column) === selected[1]));
    button.setAttribute('aria-label', prefix + ' row ' + (+row + 1) + ', column ' + (+column + 1) +
      ', target ' + fmt(weight) + ', stored ' + fmt(stored));
  });
}

export function inputControls(values) {
  return values.map((value, i) => slider('x' + i, 'Input x' + (i + 1), -1, 1, 0.01, value)).join('');
}

// Mount lazily and pause animation when the chip or its parent lab tab is left.
export function register(tag, mount) {
  customElements.define(tag, class extends HTMLElement {
    connectedCallback() {
      const tab = this.closest('[role="tabpanel"]');
      const sync = () => {
        if (this.hidden || tab?.hidden) {
          this.controller?.stop();
        } else {
          this.controller ??= mount(this);
        }
      };
      this.observer = new MutationObserver(sync);
      this.observer.observe(this, { attributes: true, attributeFilter: ['hidden'] });
      if (tab) this.observer.observe(tab, { attributes: true, attributeFilter: ['hidden'] });
      sync();
    }

    disconnectedCallback() {
      this.observer?.disconnect();
      this.controller?.stop();
    }
  });
}

export function playback(root, refresh) {
  let running = false;
  return {
    start() {
      running = true;
      root.dataset.running = 'true';
      refresh(running);
    },
    stop() {
      if (!running) return;
      running = false;
      root.dataset.running = 'false';
      refresh(running);
    },
    get running() { return running; },
  };
}
