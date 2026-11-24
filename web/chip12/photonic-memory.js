import {assumptions, evaluate, presets, presetSettings} from './photonic-memory-model.mjs';

const panel = document.getElementById('photonic-memory-chip');
const lab = document.getElementById('panel-photonic-circuit-lab');
const design = document.getElementById('pulse-design');
const motion = matchMedia('(prefers-reduced-motion: reduce)');
const byId = id => document.getElementById('pm-' + id);
const num = new Intl.NumberFormat('en-US', {maximumSignificantDigits:4});
const format = (value, unit = '') => value == null ? '—' : num.format(value) + (unit ? ' ' + unit : '');
const duration = value => value == null ? '—' : value > 3600 ? format(value / 3600, 'h') :
  value >= 60 ? format(value / 60, 'min') : value >= 1 ? format(value, 's') : format(value * 1000, 'ms');

const sources = [
  ['AirLLM and its layer-wise and expert-wise loading', 'https://github.com/lyogavin/airllm'],
  ['AirLLM release notes and author-reported K3 test', 'https://github.com/lyogavin/airllm/releases'],
  ['Deltafin and on-demand expert fetches', 'https://github.com/gavamedia/deltafin'],
  ['Colibri and storage, RAM and GPU expert tiers', 'https://github.com/JustVugg/colibri'],
  ['llama.cpp, quantization and heterogeneous backends', 'https://github.com/ggml-org/llama.cpp'],
  ['AirLLM video background', 'https://youtu.be/BhhEhfJ4ao0'],
  ['FlexGen, ICML 2023', 'https://proceedings.mlr.press/v202/sheng23a.html'],
  ['PagedAttention and KV-cache management, SOSP 2023', 'https://arxiv.org/abs/2309.06180'],
  ['Switch Transformers, JMLR 2022', 'https://www.jmlr.org/papers/v23/21-0998.html'],
  ['Microcomb WDM transmission, Nature Photonics 2022', 'https://doi.org/10.1038/s41566-022-01082-z'],
  ['Silicon photonic memory disaggregation, OFC 2018', 'https://doi.org/10.1364/OFC.2018.Tu3F.3'],
  ['Photonic Fabric for Memory and Compute Disaggregation, OFC 2025', 'https://opg.optica.org/abstract.cfm?uri=OFC-2025-W3D.1'],
  ['Co-packaged optical I/O demonstration, Intel OFC 2024', 'https://www.intel.com/content/www/us/en/newsroom/news/intel-unveils-first-integrated-optical-io-chiplet.html'],
  ['Silicon photonic and CMOS optical link, IEEE JSSC 2026', 'https://ieeexplore.ieee.org/document/11404735/'],
  ['PCIe line-rate specifications, PCI-SIG', 'https://pcisig.com/pci-express-6.0-specification'],
  ['Chip 12 equations and evidence boundaries', 'https://github.com/cryptomanxxx/debatt-ai-open-photonic-lab/blob/main/research/OPA-MEM.md'],
];

panel.innerHTML = `
  <section class="card pm-card" aria-labelledby="pm-title">
    <h2 id="pm-title">Chip 12 · Photonic Memory Interconnect</h2>
    <p>Follow the weights a model needs to generate a token. Compare a PCIe connection with an optical link that carries several data streams through one waveguide. Watch how storage, memory and compute can still set the pace.</p>
    <p class="muted">Conceptual, single-request decode model. Figures are estimates from the selected inputs. The animation runs in slow motion and samples layers.</p>
    <h3>Learn by experimenting</h3>
    <div class="pm-toolbar">
      <label>Experiment <select id="pm-preset" aria-label="Experiment"></select></label>
      <button type="button" class="btn" id="pm-reset">Reset experiment</button>
    </div>
    <p id="pm-lesson"></p>
    <div class="pm-toolbar">
      <button type="button" class="btn primary" id="pm-play" aria-pressed="false">Play weight flow</button>
      <button type="button" class="btn" id="pm-step">Step</button>
    </div>
    <p id="pm-progress" aria-live="polite"></p>
    <div id="pm-layers" class="pm-layer-strip" aria-hidden="true"></div>
    <div class="pm-paths" id="pm-paths"></div>
    <p class="muted">An amber underline marks the largest time cost on each path. Dashed blocks are bypassed in the current run or belong to the separate optical carrier source.</p>
  </section>
  <section class="card pm-card" aria-labelledby="pm-results-title">
    <h2 id="pm-results-title">Bandwidth, latency and energy</h2>
    <p id="pm-inventory"></p>
    <p id="pm-traffic"></p>
    <table class="pm-table" aria-labelledby="pm-results-title">
      <thead><tr><th scope="col">Metric</th><th scope="col">Electronic</th><th scope="col">Photonic</th></tr></thead>
      <tbody id="pm-results"></tbody>
    </table>
    <div class="pm-chart" id="pm-chart" aria-hidden="true"></div>
    <details id="pm-sweep" class="pm-reference" hidden open>
      <summary>Wavelength scaling at the current pump power</summary>
      <table class="pm-table" aria-label="WDM wavelength sweep">
        <thead><tr><th scope="col">Channels</th><th scope="col">Payload GB/s</th><th scope="col">Margin dB</th><th scope="col">Answer J</th></tr></thead>
        <tbody id="pm-sweep-rows"></tbody>
      </table>
    </details>
    <p class="muted">Link energy covers the PCIe or optical connection. Total energy also includes storage, host and accelerator memory, compute and platform power during generation. The answer time covers decode after prompt processing.</p>
    <details class="pm-reference">
      <summary>Time by stage and energy budget</summary>
      <table class="pm-table" aria-label="Time and energy breakdown">
        <thead><tr><th scope="col">Stage</th><th scope="col">Electronic</th><th scope="col">Photonic</th></tr></thead>
        <tbody id="pm-budget"></tbody>
      </table>
      <p class="muted">The SSD, RAM, controller and link service times overlap in the model. The longest of those times sets the transfer cost. Local weight reads, KV-cache traffic, compute and other decode time are added separately.</p>
    </details>
    <div class="pm-toolbar">
      <label>Export format <select id="pm-format" aria-label="Export format"><option>JSON</option><option>CSV</option></select></label>
      <button type="button" class="btn" id="pm-export">Export results</button>
    </div>
    <p id="pm-export-status" class="muted" role="status"></p>
  </section>
  <section class="card pm-card" aria-labelledby="pm-controls-title">
    <h2 id="pm-controls-title">Configure the system</h2>
    <p class="muted">Changes update both paths immediately. Capacities and rates use decimal GB. Edit the memory and link ceilings independently to isolate a bottleneck.</p>
    <div id="pm-controls"></div>
  </section>
  <section class="card pm-card" aria-labelledby="pm-method-title">
    <h2 id="pm-method-title">Model, sources and OPA</h2>
    <details class="pm-reference">
      <summary>How the estimates work</summary>
      <ul class="pm-math">
        <li>Checkpoint size is parameter count × storage bits ÷ 8. Dense weights are all active. Mixture of Experts uses an active fraction and a read amplification factor for extra bytes fetched. Warm cache assigns weights to VRAM and RAM, with uniform access assumed across the checkpoint. Streaming reserves one representative layer buffer. Quantization metadata, uneven layer sizes and cold startup are outside this approximation.</li>
        <li>KV-cache capacity uses 2 × layers × KV heads × 128 elements × 2 bytes × peak sequence length. Each decode step reads the existing cache and writes one new entry. It stays in accelerator memory for this experiment. Weight precision does not change KV precision.</li>
        <li>Transfer time is the maximum service time of SSD, host memory, the controller and the interconnect, plus an optical propagation term when applicable. Host RAM charges a write for SSD staging and a read for delivery. Decode adds local reads, approximate FLOPs at 50% compute utilization and 0.2 ms per token for other work. The model assumes a single request after prefill.</li>
        <li>PCIe uses one-direction line rate, encoding where applicable and a payload factor. Raw WDM bandwidth is channels × line rate ÷ 8. Its payload factor is 85%. The optical path requires enough comb spectrum, channel spacing and received power for the assumed NRZ signals.</li>
        <li>Received power per channel is pump power × 25% comb efficiency ÷ channels × 10<sup>−loss/10</sup>. Total loss is fixed insertion loss plus length × loss per cm. The laser is 25% wall-plug efficient. The optical budget adds modulator, detector, E/O and O/E electronics plus the pump and a fixed bias while decode traffic uses that path.</li>
      </ul>
    </details>
    <details class="pm-reference">
      <summary>Measurements in the literature and what they cover</summary>
      <p>AirLLM lists approximately 8 GB of GPU memory for its 405B example. Its authors report 3.72 GB peak GPU memory and 292 s/token for a separate disk-bound Kimi K3 run on an RTX 6000 Ada. These are project-reported results from specific configurations.</p>
      <p>The Jørgensen et al. microcomb experiment measured 1.84 Pbit/s across 223 wavelengths and 37 fiber cores. Anderson et al. demonstrated optically connected memory with 10 Gb/s data streams. Intel demonstrated a co-packaged optical I/O link rated up to 4 Tbit/s bidirectionally. These results cover different link boundaries and hardware. The controls above use illustrative assumptions.</p>
      <ul id="pm-sources"></ul>
    </details>
    <p><a href="#photonic-circuit-lab/microring">Chip 10</a> explains where the carrier wavelengths come from. <a href="#photonic-circuit-lab/optical-logic">Chip 11</a> shows how receivers detect light and how conversion changes the energy budget. Chip 12 uses those ideas to move digital weights into an electronic accelerator.</p>
    <p class="muted">An OPA research hypothesis is that a WDM memory link can improve decode latency or energy when transport is limiting. Test it with matched payload and workload, measured receiver margin and bit error rate, and an electrical power budget that includes both endpoints and the memory controller.</p>
  </section>
`;

function el(parent, tag, text = '') {
  const node = document.createElement(tag);
  node.textContent = text;
  parent.append(node);
  return node;
}

const groups = [
  ['Model and generation', [
    ['parametersB','Total model parameters (billions)',.1,5000,.1],
    ['precision','Weight precision',['FP32','FP16','FP8','4-bit']],
    ['workload','Model type',['Dense','Mixture of Experts']],
    ['activePercent','Active parameters in MoE (%)',1,100,1],
    ['readAmp','MoE extra fetch factor (×)',1,5,.05],
    ['layers','Model layers',1,256,1],
    ['kvHeads','KV heads per layer',1,32,1],
    ['context','Existing context (tokens)',1,131072,1],
    ['tokens','Tokens to generate',1,2048,1],
    ['computeTops','Accelerator peak compute (TFLOP/s equivalent)',.1,10000,.1],
  ]],
  ['Storage, memory and PCIe', [
    ['residency','Weight placement',['Warm cache','Stream every layer']],
    ['ramGB','Host RAM capacity (GB)',1,8192,1],
    ['vramGB','Accelerator VRAM capacity (GB)',1,8192,1],
    ['ssdGBs','SSD sequential read ceiling (GB/s)',.1,100,.1],
    ['ramGBs','Host memory ceiling (GB/s)',1,5000,1],
    ['controllerGBs','Memory controller payload ceiling (GB/s)',1,5000,1],
    ['vramGBs','Accelerator memory ceiling (GB/s)',1,12000,1],
    ['pcieGen','PCIe generation',[1,2,3,4,5,6]],
    ['lanes','PCIe lanes',[1,2,4,8,16]],
  ]],
  ['Optical link and energy per bit', [
    ['channels','WDM wavelength channels',1,64,1],
    ['channelGbps','Line rate per channel (Gb/s)',1,200,1],
    ['spacingGHz','Frequency spacing (GHz)',10,400,1],
    ['combSpanTHz','Usable comb spectrum (THz)',.1,32,.1],
    ['pumpMw','Total optical pump power (mW)',.1,1000,.1],
    ['lengthCm','Waveguide length (cm)',.01,100,.01],
    ['lossDbCm','Waveguide propagation loss (dB/cm)',0,10,.01],
    ['insertionDb','Combined insertion loss (dB)',0,40,.1],
    ['sensitivityUw','Receiver sensitivity per channel (µW)',.1,1000,.1],
    ['modulatorPj','Modulator switching (pJ/line bit)',0,200,.01],
    ['detectorPj','Detector (pJ/line bit)',0,200,.01],
    ['eoPj','E/O driver and serializer (pJ/line bit)',0,200,.01],
    ['oePj','O/E receiver and deserializer (pJ/line bit)',0,200,.01],
  ]],
];

const paths = [
  {key:'electronic', name:'Electronic reference', link:'PCIe', before:['SSD','Host RAM','Memory controller'], after:['VRAM','GPU','KV-cache']},
  {key:'photonic', name:'Photonic alternative', link:'Optical I/O', before:['SSD','Host RAM','Memory controller','E/O driver','Modulators','MUX','Optical I/O','DEMUX','Photodetectors','O/E receiver'], after:['VRAM','AI accelerator','KV-cache']},
];
const metrics = [
  ['Raw one-direction link ceiling', p => format(p.rawGBs,'GB/s')],
  ['Link payload ceiling', p => format(p.payloadGBs,'GB/s')],
  ['Effective host-to-accelerator transfer', p => format(p.metrics?.effectiveGBs,'GB/s')],
  ['Host weight transfer per token', p => duration(p.metrics?.transferSeconds)],
  ['Decode time per token', p => duration(p.metrics?.tokenSeconds)],
  ['Estimated decode rate', p => format(p.metrics?.tokenRate,'tokens/s')],
  ['Estimated answer time', p => duration(p.metrics?.answerSeconds)],
  ['Link energy per payload bit', p => format(p.metrics?.linkPj,'pJ/bit')],
  ['Total energy for this answer', p => format(p.metrics?.totalJ,'J')],
  ['Largest time cost', p => p.metrics?.bottleneck ?? 'Blocked'],
];
const energyNames = {storage:'SSD',hostMemory:'Host memory',link:'Link',localMemory:'Accelerator memory',compute:'Compute',platform:'Platform'};

for (const [label, url] of sources) el(el(byId('sources'),'li'),'a',label).href = url;
presets.forEach((preset, i) => { el(byId('preset'),'option',i + 1 + ' · ' + preset.title).value = preset.id; });

let settings;
let result;
let selected;
let timer = 0;
let frame = 0;
let finalFrame = 0;
const fields = new Map();
const exportTools = globalThis.PhotonicExperimentExport;
const exporter = exportTools.bind({button:byId('export'), format:byId('format'), status:byId('export-status')});
for (const [section, definitions] of groups) {
  const details = el(byId('controls'),'details');
  details.className = 'pm-controls';
  details.open = section === groups[0][0];
  el(details,'summary',section);
  const grid = el(details,'div');
  grid.className = 'pm-grid';
  for (const [key, title, values, max, step] of definitions) {
    const label = el(grid,'label',title);
    const control = el(label,Array.isArray(values) ? 'select' : 'input');
    control.id = 'pm-input-' + key;
    control.setAttribute('aria-label',title);
    if (Array.isArray(values)) {
      values.forEach(value => { el(control,'option',String(value)).value = value; });
    } else {
      Object.assign(control,{type:'number', min:values, max, step});
    }
    const read = () => typeof settings[key] === 'string' ? control.value : Number(control.value);
    control.addEventListener('input', () => {
      if (control.value === '' || !control.validity.valid) return;
      settings[key] = read();
      refresh();
    });
    control.addEventListener('change', () => { control.value = settings[key]; });
    fields.set(key,control);
  }
}

for (const path of paths) {
  const card = el(byId('paths'),'section');
  card.className = 'pm-path' + (path.key === 'photonic' ? ' optical' : '');
  el(card,'h3',path.name);
  if (path.key === 'photonic') {
    const light = el(card,'ul');
    light.className = 'pm-source';
    el(light,'li','Pump laser(s)');
    path.comb = el(light,'li','Microring frequency comb');
    el(light,'li','Carrier separator');
    el(card,'p','The comb supplies carriers to the modulators. Each modulator adds data to one carrier.').className = 'muted';
  }
  const list = el(card,'ol');
  list.className = 'pm-flow';
  path.nodes = new Map([...path.before, ...(path.key === 'electronic' ? ['PCIe'] : []), ...path.after].map(name =>
    [name, el(list,'li',name === 'Optical I/O' ? 'WDM waveguide' : name)]));
  path.guide = el(card,'div');
  path.guide.className = 'pm-guide' + (path.key === 'electronic' ? ' electric' : '');
  path.guide.setAttribute('aria-hidden','true');
  path.status = el(card,'p');
  path.status.className = 'muted';
  if (path.key === 'photonic') {
    const details = el(card,'details');
    el(details,'summary','Inspect carrier wavelengths');
    path.wavelengths = el(details,'div');
    path.wavelengths.className = 'pm-spectrum';
    path.wavelengths.tabIndex = 0;
  }
}

function row(table, label, left, right) {
  const tr = el(table,'tr');
  el(tr,'th',label).scope = 'row';
  el(tr,'td',left);
  el(tr,'td',right);
}

function paintWaves(path, wavelengths) {
  path.guide.replaceChildren();
  path.guide.style.setProperty('--pm-tracks',wavelengths.length);
  path.wavelengths?.replaceChildren();
  wavelengths.forEach((wave,i) => {
    const color = path.wavelengths ? 'hsl(' + (180 + i * 137.508) % 360 + ' 88% 71%)' : 'var(--pm-electric)';
    const lane = el(path.guide,'span');
    lane.className = 'pm-lane';
    lane.style.setProperty('--wave',color);
    if (path.wavelengths) el(path.wavelengths,'span','λ' + (i+1) + ' · ' + wave.toFixed(2) + ' nm').style.setProperty('--wave',color);
  });
}

function renderResults() {
  const {electronic:e, photonic:p, optical:o} = result;
  byId('inventory').textContent = 'Checkpoint ' + format(result.totalGB,'GB') + ' · ' +
    format(result.activeParametersB,'billion active parameters') + ' (' + format(result.activeGB,'GB') +
    ') · Peak KV cache ' + format(result.kvPeakGB,'GB') + ' · Layer buffer ' + format(result.stagingGB,'GB');
  byId('traffic').textContent = 'Per token · ' + format(result.ssdGB,'GB') + ' read from SSD · ' +
    format(result.linkGB,'GB') + ' sent across the link · ' + format(result.kvTrafficGB,'GB') + ' of local KV-cache traffic. ' +
    'Resident weights · ' + format(result.hostResidentGB,'GB') + ' in RAM · ' + format(result.gpuResidentGB,'GB') + ' in VRAM.';
  byId('results').replaceChildren();
  metrics.forEach(([label, value]) => row(byId('results'),label,value(e),value(p)));
  byId('budget').replaceChildren();
  for (const [i, stage] of e.stages.entries()) {
    row(byId('budget'), i === 3 ? 'Interconnect service per token' : stage.name + ' service per token',
      e.blocked.length ? '—' : duration(stage.seconds), p.blocked.length ? '—' : duration(p.stages[i].seconds));
  }
  for (const [i, stage] of e.timing.entries()) {
    if (i) row(byId('budget'),stage.name + ' per token',
      e.blocked.length ? '—' : duration(stage.seconds),p.blocked.length ? '—' : duration(p.timing[i].seconds));
  }
  Object.entries(energyNames).forEach(([key, name]) =>
    row(byId('budget'),name + ' energy',format(e.metrics?.energy[key],'J'),format(p.metrics?.energy[key],'J')));
  byId('chart').replaceChildren();
  for (const [name, prop, unit] of [['Decode rate','tokenRate','tokens/s'],['Answer energy','totalJ','J']]) {
    const values = [e.metrics?.[prop],p.metrics?.[prop]];
    const max = Math.max(...values.map(value => value ?? 0));
    if (!max) continue;
    el(byId('chart'),'div',name + ' · Electronic ' + format(values[0],unit) + ' · Photonic ' + format(values[1],unit)).className = 'pm-chart-item';
    const bars = el(byId('chart'),'div');
    bars.className = 'pm-bars';
    values.forEach(value => {
      const track = el(bars,'div');
      track.className = 'pm-bar';
      el(track,'span').style.width = (value == null ? 0 : 100 * value / max) + '%';
    });
  }
  byId('sweep').hidden = selected.id !== 'wdm';
  if (selected.id === 'wdm') {
    const body = byId('sweep-rows');
    body.replaceChildren();
    for (const channels of [1,8,16,32,64]) {
      const {optical, photonic} = evaluate({...settings,channels});
      const tr = el(body,'tr');
      el(tr,'th',String(channels)).scope = 'row';
      el(tr,'td',format(optical.payloadGBs));
      el(tr,'td',format(optical.marginDb));
      el(tr,'td',format(photonic.metrics?.totalJ));
    }
  }
  paths[0].status.textContent = e.blocked.join(' ') || format(e.payloadGBs,'GB/s') + ' of modeled PCIe payload.';
  paths[1].status.textContent = format(o.receivedUw,'µW') + ' per channel · ' + format(o.marginDb,'dB') +
    ' receiver margin · ' + format(o.lossDb,'dB') + ' loss · ' + format(o.occupiedTHz,'THz') + ' occupied. ' +
    (p.blocked.join(' ') || (result.linkGB ? '' : 'Resident weights bypass this link.'));
  for (const path of paths) path.status.classList.toggle('pm-warning',result[path.key].blocked.length > 0);
  if (!paths[0].guide.childElementCount) paintWaves(paths[0],[0]);
  paintWaves(paths[1],o.wavelengthNm);
}

function stages(path) {
  const active = path.before.filter(name => name === 'SSD' ? result.ssdGB > 0 : result.linkGB > 0);
  if (path.key === 'electronic' && result.linkGB) active.push('PCIe');
  return [...active,...path.after];
}

function renderFrame() {
  const shownLayers = [...new Set([1,2,Math.ceil(settings.layers / 2),settings.layers].filter(value => value <= settings.layers))];
  const tokens = Math.min(settings.tokens,2);
  const sequence = paths.map(stages);
  const width = Math.max(...sequence.map(list => list.length));
  const count = width * shownLayers.length * tokens;
  const current = Math.max(0,Math.min(frame - 1,count - 1));
  const layerIndex = Math.floor(current / width) % shownLayers.length;
  const token = 1 + Math.floor(current / (width * shownLayers.length));
  byId('layers').replaceChildren();
  for (const [i, layer] of shownLayers.entries()) {
    el(byId('layers'),'span','Layer ' + layer).toggleAttribute('data-active',frame > 0 && frame <= count && i === layerIndex);
  }
  const messages = [];
  for (const [i, path] of paths.entries()) {
    const data = result[path.key];
    const active = frame > 0 && frame <= count && !data.blocked.length ? sequence[i][current % width] : undefined;
    const limit = {'Local weight reads':'VRAM','KV-cache traffic':'KV-cache','Accelerator compute':path.after[1]}[data.metrics?.bottleneck] ?? data.metrics?.bottleneck;
    path.nodes.forEach((node,name) => {
      node.toggleAttribute('data-inactive',!sequence[i].includes(name));
      node.toggleAttribute('data-active',name === active);
      node.toggleAttribute('data-limit',name === limit);
    });
    const lit = active === path.link;
    path.guide.toggleAttribute('data-lit',lit);
    path.comb?.toggleAttribute('data-active',lit);
    if (active) messages.push(path.name + ' at ' + (lit && path.comb ? 'WDM waveguide' : active));
  }
  byId('progress').textContent = frame === 0 ? 'Ready to trace sampled layers for up to two tokens.' : frame > count ?
    'Weight-flow preview complete. The results use all ' + settings.layers + ' layers and ' + settings.tokens + ' requested tokens.' :
    'Token ' + token + ' · Layer ' + shownLayers[layerIndex] + ' of ' + settings.layers +
    (messages.length ? ' · ' + messages.join(' · ') : '');
  return count + 1;
}

function pause() {
  clearInterval(timer);
  timer = 0;
  byId('play').textContent = motion.matches ? 'Play weight flow (reduced motion)' : 'Play weight flow';
  byId('play').setAttribute('aria-pressed','false');
}
function advance() {
  frame = frame >= finalFrame ? 1 : frame + 1;
  finalFrame = renderFrame();
  if (frame >= finalFrame) pause();
}
function play() {
  if (timer) { pause(); return; }
  if (motion.matches) { advance(); return; }
  advance();
  if (frame >= finalFrame) return;
  timer = setInterval(advance,360);
  byId('play').textContent = 'Pause weight flow';
  byId('play').setAttribute('aria-pressed','true');
}

function refresh() {
  pause();
  frame = 0;
  result = evaluate(settings);
  const isMoe = settings.workload === 'Mixture of Experts';
  for (const key of ['activePercent','readAmp']) fields.get(key).disabled = !isMoe;
  renderResults();
  finalFrame = renderFrame();
  exporter.reset();
  const run = exportTools.begin(12);
  exporter.ready(() => ({
    ...run, simulatorVersion:'1.0.0', resultType:'analytical estimate', physicalMeasurement:false,
    preset:selected.id, settings, assumptions, ...result,
    units:{capacity:'decimal GB', times:'s', bandwidth:'decimal GB/s unless stated', linkEnergy:'pJ/payload bit', energy:'J'},
  }),run);
}
function loadPreset(id) {
  selected = presets.find(preset => preset.id === id);
  settings = presetSettings(selected);
  byId('preset').value = selected.id;
  byId('lesson').textContent = selected.lesson;
  for (const [key, control] of fields) control.value = settings[key];
  refresh();
}
byId('preset').addEventListener('change',event => loadPreset(event.target.value));
byId('reset').addEventListener('click',() => loadPreset(selected.id));
byId('step').addEventListener('click',() => { pause(); advance(); });
byId('play').addEventListener('click',play);
function sync() {
  panel.hidden = design.value !== 'photonic-memory';
  if (panel.hidden || lab.hidden) pause();
}
design.addEventListener('change',sync);
motion.addEventListener('change',pause);
new MutationObserver(sync).observe(lab,{attributes:true,attributeFilter:['hidden']});
document.getElementById('pulse-start').addEventListener('click',() => { if (!lab.hidden && !panel.hidden) play(); });
loadPreset('airllm');
sync();
