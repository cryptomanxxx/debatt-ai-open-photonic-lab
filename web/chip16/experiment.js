'use strict';

class PhotonicRayLab extends HTMLElement {
  connectedCallback() {
    if (this.firstElementChild) return;
    const model = Chip16Model;
    const labels = {
      hit: 'Both hit', miss: 'Both miss', fp: 'False positive', fn: 'False negative',
    };
    const presets = {
      default: model.defaults,
      fp: {...model.defaults, y: 1.15, angle: 1, bits: 1},
      fn: {...model.defaults, y: -2, angle: 6, bits: 1},
    };
    const slider = (id, label, min, max, step) => `
      <div class="rt-range">
        <div><label for="rt-${id}">${label}</label><output for="rt-${id}" data-value="${id}"></output></div>
        <input id="rt-${id}" name="${id}" type="range" min="${min}" max="${max}" step="${step}">
      </div>`;
    const view = (mode, name) => `<figure><figcaption>${name}</figcaption>
      <svg data-view="${mode}" viewBox="0 0 520 318" role="img" aria-label="${name} ray paths">
        <g class="rt-grid" aria-hidden="true"></g><g class="rt-scene"></g>
      </svg></figure>`;
    this.innerHTML = `
      <section class="card rt-card">
        <h2>Chip 16 · Photonic Ray Tracing Accelerator</h2>
        <p>Cast five rays at two movable bounding boxes. Compare the electronic geometry reference with a reduced-precision numerical proxy. Choose a box to inspect, then try coarse precision near an edge.</p>
        <div class="rt-presets">
          <button class="btn" type="button" data-preset="default">Reset scene</button>
          <button class="btn" type="button" data-preset="fp">Try a false positive</button>
          <button class="btn" type="button" data-preset="fn">Try a false negative</button>
        </div>
        <div class="rt-controls">
          <fieldset><legend>Ray fan</legend>
            ${slider('x', 'Origin X', -7, 7, .05)}
            ${slider('y', 'Origin Y', -4, 4, .05)}
            ${slider('angle', 'Direction (degrees)', -180, 180, 1)}
            ${slider('bits', 'Proxy fractional bits', 1, 12, 1)}
          </fieldset>
          <fieldset><legend>Bounding boxes</legend>
            <label>Box to edit and test
              <select name="box"><option value="a">Box A</option><option value="b">Box B</option></select>
            </label>
            ${slider('bx', 'Center X', -5, 5, .05)}
            ${slider('by', 'Center Y', -3, 3, .05)}
            ${slider('w', 'Width', .4, 5, .05)}
            ${slider('h', 'Height', .4, 4, .05)}
          </fieldset>
        </div>
        <p class="rt-summary" role="status"></p>
        <div class="rt-views">
          ${view('exact', 'Electronic reference')}
          ${view('proxy', 'Quantized accelerator proxy')}
        </div>
        <p class="muted">The bold box is under test. The proxy view draws rounded rays and rounded bounds for the selected box. Dots mark the first contact, including the origin for a ray starting inside. Paths use the same agreement colors in both views.</p>
        <table class="data-table rt-results"><caption>Results for the selected box</caption>
          <thead><tr><th scope="col">Ray</th><th scope="col">Reference</th><th scope="col">Proxy</th><th scope="col">Comparison</th></tr></thead>
          <tbody></tbody>
        </table>
      </section>
      <section class="card rt-card">
        <h2>From a box test to a VR frame</h2>
        <p>Each eye has a virtual camera. Primary rays locate surfaces and secondary rays help compute shadows and reflections. A bounding volume hierarchy (BVH) groups geometry into nested boxes. When a ray misses a box, the renderer can skip its contents. A false positive adds work. A false negative can hide geometry and introduce visible artifacts.</p>
        <details><summary>What the simulation computes</summary>
          <p>The reference intersects X and Y parameter intervals with the forward ray, using JavaScript double precision and a near-parallel tolerance. The proxy first rounds the origin, direction and box bounds to a grid of size 2<sup>−b</sup> and then applies the same test. The bit slider changes the grid spacing. It does not change the optical output bit in the paper.</p>
        </details>
      </section>
      <section class="card rt-card">
        <h2>How four modulators can test an edge</h2>
        <figure class="rt-circuit">
          <svg viewBox="0 16 540 201" role="img" aria-label="A laser splits into two branches with two MZMs each and a reference branch. The three fields recombine at a photodetector. A one-bit comparison reads the sign.">
            <g class="rt-optical-lines">
              <path d="M78 118H96V59H339L370 118M96 118H370M96 118V177H339L370 118M370 118H463"/>
            </g>
            <g class="rt-components">
              <rect x="12" y="99" width="66" height="38" rx="7"/>
              <rect x="132" y="40" width="87" height="38" rx="7"/>
              <rect x="236" y="40" width="87" height="38" rx="7"/>
              <rect x="132" y="158" width="87" height="38" rx="7"/>
              <rect x="236" y="158" width="87" height="38" rx="7"/>
              <circle cx="370" cy="118" r="8"/>
              <rect x="394" y="99" width="68" height="38" rx="7"/>
              <rect x="463" y="99" width="65" height="38" rx="7"/>
            </g>
            <g class="rt-diagram-labels" text-anchor="middle">
              <text x="45" y="124">Laser</text>
              <text x="175" y="65">MZM r₁</text><text x="280" y="65">MZM v₁</text>
              <text x="175" y="183">MZM r₂</text><text x="280" y="183">MZM v₂</text>
              <text x="220" y="106">Reference field</text>
              <text x="428" y="124">PD</text><text x="495" y="124">1 bit</text>
              <text x="370" y="96">Sum</text>
            </g>
          </svg>
          <figcaption class="muted">Functional schematic based on the published architecture. PD is the photodetector. The one-bit output indicates the sign of one side test. A box decision combines several side tests.</figcaption>
        </figure>
        <p class="rt-formula"><code>E<sub>out</sub> = E<sub>ref</sub> + E<sub>0</sub>[sin(r₁) sin(v₁) + sin(r₂) sin(v₂)]</code></p>
        <p>Each push–pull Mach–Zehnder modulator changes the phase in its two arms in opposite directions. Around the null bias, output field is nearly proportional to the input. Cascaded modulators multiply two factors per branch. Coherent recombination adds both products to a reference field so the detector and comparator can compare |E<sub>out</sub>|² with |E<sub>ref</sub>|² and read the sign.</p>
        <label class="rt-corner">Inspect the center ray against a corner of the selected box
          <select name="corner">
            <option value="0">Upper left</option><option value="1">Upper right</option>
            <option value="2">Lower left</option><option value="3">Lower right</option>
          </select>
        </label>
        <p class="rt-side" role="status"></p>
        <p class="muted">This separate calculation feeds a 2D ray–point side expression into a dimensionless version of the optical readout. The experiment uses small phases and a unit reference field. The resulting side sign illustrates the circuit principle. The published 3D ray–box algorithm uses ray and edge coordinates, and the browser box classification uses the interval method above.</p>
      </section>
      <section class="card rt-card">
        <h2>Published results and open questions</h2>
        <dl class="rt-evidence">
          <div><dt>Published experiment</dt><dd>Zhang et al. demonstrated a thin-film lithium-niobate photonic ray-tracing core with 16 GS/s experimental signaling and approximately 100 GHz electro-optic modulator bandwidth. The paper reports 326 fJ per operation under its stated accounting.</dd></div>
          <div><dt>Debatt-AI simulation</dt><dd>Browser geometry, arithmetic quantization and an illustrative optical side calculation. Displayed errors are specific to the selected numerical scene.</dd></div>
          <div><dt>Future research</dt><dd>Reproduce the published 3D side-function algorithm, calibrate optical error sources and compare matched GPU workloads including memory transfers, conversions and wall-plug power.</dd></div>
        </dl>
        <p><a href="https://doi.org/10.1038/s41467-025-61234-x">Zhang et al., Nature Communications 16, 5938 (2025), Fig. 1 and Eq. 1</a></p>
      </section>`;

    const get = name => this.querySelector('[name="' + name + '"]');
    const svg = (tag, attributes, parent, text) => {
      const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
      for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
      if (text !== undefined) node.textContent = text;
      parent.append(node);
    };
    const sx = x => 260 + x * 30;
    const sy = y => 159 - y * 30;
    for (const grid of this.querySelectorAll('.rt-grid')) {
      for (let x = -8; x <= 8; x++) svg('line', {x1:sx(x), x2:sx(x), y1:0, y2:318}, grid);
      for (let y = -5; y <= 5; y++) svg('line', {x1:0, x2:520, y1:sy(y), y2:sy(y)}, grid);
    }
    let settings;
    const boxFields = {bx:'x', by:'y', w:'w', h:'h'};
    const number = name => Number(get(name).value);
    const display = value => Number(value.toFixed(6)).toString();
    const reportSign = value => value === 0 ? 'on the line' : value > 0 ? 'left' : 'right';

    const draw = (mode, boxKey, box, rays, corner) => {
      const layer = this.querySelector('[data-view="' + mode + '"] .rt-scene');
      const {min, max} = model.bounds(box);
      layer.replaceChildren();
      for (const key of ['a', 'b']) {
        const {min: low, max: high} = key === boxKey && mode === 'proxy'
          ? rays[0].rounded : model.bounds(settings[key]);
        svg('rect', {x:sx(low[0]), y:sy(high[1]), width:(high[0]-low[0])*30,
          height:(high[1]-low[1])*30, class:key === boxKey ? 'rt-box-active' : 'rt-box-context'}, layer);
        svg('text', {x:sx(low[0])+5, y:sy(high[1])+20}, layer, key.toUpperCase());
      }
      for (const ray of rays) {
        const {origin, direction} = mode === 'proxy' ? ray.rounded : ray;
        const hit = ray[mode];
        const point = t => [sx(origin[0]+t*direction[0]), sy(origin[1]+t*direction[1])];
        const line = (t1, t2, style) => {
          const [x1,y1] = point(t1);
          const [x2,y2] = point(t2);
          svg('line', {x1,y1,x2,y2,class:style,'data-status':ray.status},layer);
        };
        line(0, hit?.entry ?? 50, hit ? 'rt-beam' : 'rt-beam rt-dash');
        if (hit) {
          line(hit.entry, 50, 'rt-beam rt-tail');
          const [cx,cy] = point(hit.entry);
          svg('circle', {cx,cy,r:4,'data-status':ray.status}, layer);
        }
      }
      const source = mode === 'proxy' ? rays[0].rounded.origin : rays[0].origin;
      svg('circle', {cx:sx(source[0]),cy:sy(source[1]),r:5,class:'rt-origin'},layer);
      if (mode === 'exact') {
        svg('circle', {cx:sx(corner % 2 ? max[0] : min[0]), cy:sy(corner < 2 ? max[1] : min[1]), r:6, class:'rt-point'},layer);
      }
    };

    const render = () => {
      const key = get('box').value;
      const box = settings[key];
      const rays = model.rays(settings, box);
      const corner = number('corner');
      const counts = {hit:0, miss:0, fp:0, fn:0};
      const tbody = this.querySelector('tbody');
      tbody.replaceChildren();
      for (const [i, ray] of rays.entries()) {
        counts[ray.status]++;
        const row = tbody.insertRow();
        const heading = document.createElement('th');
        heading.scope = 'row';
        heading.textContent = i === 2 ? ray.angle + '° (center)' : ray.angle + '°';
        row.append(heading);
        row.insertCell().textContent = ray.exact ? 'Hit' : 'Miss';
        row.insertCell().textContent = ray.proxy ? 'Hit' : 'Miss';
        const status = row.insertCell();
        status.dataset.status = ray.status;
        status.textContent = labels[ray.status];
      }
      this.querySelector('.rt-summary').textContent =
        'Box ' + key.toUpperCase() + ' · ' + counts.hit + ' both hit · ' + counts.miss + ' both miss · ' +
        counts.fp + ' false positive · ' + counts.fn + ' false negative';
      draw('exact', key, box, rays, corner);
      draw('proxy', key, box, rays, corner);
      const {min, max} = model.bounds(box);
      const point = [corner % 2 ? max[0] : min[0], corner < 2 ? max[1] : min[1]];
      const {side, delta} = model.opticalSide(rays[2].origin, rays[2].direction, point);
      this.querySelector('.rt-side').textContent =
        'Corner at (' + point.map(display).join(', ') + ') · ideal signed result ' + display(side) +
        ' (' + reportSign(side) + ') · optical intensity difference ' + display(delta) +
        ' (' + reportSign(delta) + ').';
      for (const output of this.querySelectorAll('output')) output.value = get(output.dataset.value).value;
    };

    const loadBox = () => {
      for (const [name, prop] of Object.entries(boxFields)) get(name).value = settings[get('box').value][prop];
    };
    const load = preset => {
      settings = structuredClone(presets[preset]);
      for (const name of ['x','y','angle','bits']) get(name).value = settings[name];
      get('box').value = 'a';
      get('corner').value = '0';
      loadBox();
      render();
    };
    for (const input of this.querySelectorAll('input')) {
      input.addEventListener('input', () => {
        const property = boxFields[input.name];
        if (property) settings[get('box').value][property] = number(input.name);
        else settings[input.name] = number(input.name);
        render();
      });
    }
    get('box').addEventListener('change', () => { loadBox(); render(); });
    get('corner').addEventListener('change', render);
    for (const button of this.querySelectorAll('[data-preset]')) {
      button.addEventListener('click', () => load(button.dataset.preset));
    }
    load('default');
  }
}
customElements.define('photonic-ray-lab', PhotonicRayLab);
