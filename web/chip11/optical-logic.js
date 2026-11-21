import {defaults, energy, gates, inputThresholdMw, spectrum, truthTable} from './optical-logic-model.mjs';

const panel = document.getElementById('optical-logic-chip');
const tab = document.getElementById('panel-photonic-circuit-lab');
const design = document.getElementById('pulse-design');
const byId = id => document.getElementById('ol-' + id);
const graph = byId('diagram');
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const narrow = matchMedia('(max-width: 620px)');
const formatter = new Intl.NumberFormat('en', {maximumSignificantDigits: 4});
const fmt = value => formatter.format(value);
const wavelength = value => value.toFixed(2);
const mw = value => fmt(value) + ' mW';
const fj = value => value >= 1000 ? fmt(value / 1000) + ' pJ' : fmt(value) + ' fJ';
const NS = 'http://www.w3.org/2000/svg';
const controls = {
  radiusUm: ['Ring radius', 'µm', 9.97, 10.03, .001],
  wavelengthNm: ['Probe wavelength', 'nm', 1546, 1554, .01],
  sourceMw: ['Optical power per active laser', 'mW', .005, 1.5, .005],
  gapNm: ['Coupling gap', 'nm', 130, 330, 5],
  intrinsicQ: ['Intrinsic Q', '', 10000, 800000, 5000],
  trimNm: ['Resonance offset', 'nm', -.65, .65, .01],
  voltageV: ['Ring drive for decoded 1', 'V', 0, 5, .05],
  routeLossDb: ['Optical loss per link', 'dB', 0, 6, .1],
  pathPhaseDeg: ['Phase step between output paths', '°', -180, 180, 5],
  thresholdMw: ['Output decision threshold', 'mW', .005, .30, .005],
  rateGhz: ['Operation rate for energy estimate', 'GHz', .1, 25, .1],
  wallPlug: ['Laser wall-plug efficiency', 'fraction', .05, .8, .01],
  receiverFj: ['Energy per receiver per slot', 'fJ', 10, 1000, 10],
  driverFj: ['Driver electronics per channel per slot', 'fJ', 0, 250, 5],
  overheadMw: ['Static stabilization and control', 'mW', 0, 10, .1]
};
const gateHelp = {
  AND: 'Read path 11 directly. Both stages must route the probe to their drop ports.',
  OR: 'Collect paths 01, 10 and 11 at a three-port combiner. Path 00 goes to a dump.',
  XOR: 'Combine paths 01 and 10. Each path drops at exactly one stage.',
  NAND: 'Collect paths 00, 01 and 10. The powered probe supplies a high output even when both data lasers are dark.'
};
const examples = {
  nominal: [{}, [1, 1], 'At nominal bias, switch A and B and compare all four detector readings.'],
  detune: [{trimNm: .32}, [1, 1], 'The resonance moves away from the probe. Adjust the wavelength to recover the drop signal.'],
  dark: [{sourceMw: .015}, [1, 1], 'Both optical data inputs are on, but their received powers are too small to drive the rings.'],
  passive: [{voltageV: 0}, [1, 1], 'Zero drive holds every ring fixed. A and B can no longer route the separate probe. Scan its wavelength to see passive filtering.'],
  loss: [{routeLossDb: 4}, [1, 1], 'Extra link loss can leave a correctly routed probe below the detector threshold.']
};
const fields = new Map();
const state = {...defaults};
let bits = [1, 1];
let frame = 0;
let tracks = [];
let latest;

function svg(parent, tag, attrs, content) {
  const element = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
  if (content) element.textContent = content;
  parent.append(element);
  return element;
}
function el(parent, tag, text) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  parent.append(element);
  return element;
}
function metrics(container, items) {
  container.replaceChildren();
  for (const [name, value] of items) {
    const group = el(container, 'div');
    el(group, 'dt', name);
    el(group, 'dd', value);
  }
}
function diagram(row, gate) {
  graph.replaceChildren();
  tracks = [];
  const mobile = narrow.matches;
  graph.setAttribute('viewBox', mobile ? '0 0 348 674' : '0 0 870 345');
  const coordinates = (x, y) => mobile ? [y, x * .77] : [x, y];
  const point = (x, y) => coordinates(x, y).join(' ');
  const label = (x, y, name, className = '') => {
    const [px, py] = coordinates(x, y);
    svg(graph, 'text', {x: px, y: py, class: className, 'text-anchor': 'middle'}, name);
  };
  const guide = (d, power, delay, color, duration = .7, laps = 1) => {
    const path = svg(graph, 'path', {d, class: 'ol-guide', stroke: color, 'stroke-opacity': .22 + .65 * Math.min(1, Math.sqrt(power / state.sourceMw))});
    if (power < 1e-10) return;
    const length = path.getTotalLength();
    const glow = Array.from({length: 5}, (_, i) => svg(graph, 'circle', {
      r: 3.8 - i * .54, fill: color, visibility: 'hidden'
    }));
    tracks.push({path, length, power, delay, duration, laps, glow});
  };
  const straight = (x, y, xx, yy) => 'M ' + point(x,y) + ' L ' + point(xx,yy);
  const route = (x, y, xx, yy) => 'M ' + point(x,y) + ' C ' + point((x+xx)/2,y) + ' ' +
    point((x+xx)/2,yy) + ' ' + point(xx,yy);
  const wire = (x, y, xx, yy) => svg(graph, 'path', {d: route(x,y,xx,yy), class: 'ol-wire'});
  const colors = ['#8fadff', '#ffbb76'];
  const fold = (x, y, xx, yy) => 'M ' + point(x,y) + ' C ' +
    point(x-32,y) + ' ' + point(x-32,y+38) + ' ' + point(x+9,y+38) +
    ' C ' + point(xx-28,y+38) + ' ' + point(xx-28,yy) + ' ' + point(xx,yy);
  const probe = '#69ead4';

  for (const [i, y] of [58, 287].entries()) {
    const power = row.opticalInputsMw[i];
    guide(straight(64,y,135,y), power, 0, colors[i]);
    label(39,y, 'Laser ' + (i ? 'B' : 'A'));
    label(152,y, 'O/E', 'ol-electrical');
  }
  label(39,171,'Probe');
  guide(straight(64,171,225,171), row.probeAtRingMw, 0, probe);
  const radius = 24 + (state.radiusUm - 10) * 125;
  const gap = 3 + (state.gapNm - 130) * .035;
  // Gap and radius are exaggerated in the drawing. Coupling rates drive all optical brightness.
  const ringGraphic = (x, y, stage, power, delay) => {
    const center = y + radius + gap;
    const [cx,cy] = coordinates(x,center);
    const rx = radius;
    const ry = mobile ? radius * .77 : radius;
    const d = 'M ' + (cx-rx) + ' ' + cy +
      ' a ' + rx + ' ' + ry + ' 0 1 0 ' + (2*rx) + ' 0' +
      ' a ' + rx + ' ' + ry + ' 0 1 0 ' + (-2*rx) + ' 0';
    guide(d, power * stage.buildup, delay, probe, 1.8, 3);
    svg(graph, 'circle', {cx,cy,r:3, class:'ol-electrode'});
    return center + radius + gap;
  };
  wire(169,58,225,171 + radius + gap);
  wire(170,287,458,72 + radius + gap);
  wire(170,287,458,218 + radius + gap);
  const stageOneDropY = ringGraphic(225,171,row.r1,row.probeAtRingMw, .7);
  const link = 10 ** (-state.routeLossDb / 10);
  const branches = [row.r1.throughPower,row.r1.dropPower].map(t => t * row.probeAtRingMw * link);
  const branchY = [72, 218];
  const outputY = [58, 135, 205, 289];
  [171,stageOneDropY].forEach((y, i) => {
    guide((i ? fold : route)(225, y, 385, branchY[i]), branches[i], .82, probe, .62);
    guide(straight(385,branchY[i],458,branchY[i]),branches[i],1.44,probe,.3);
    const lower = ringGraphic(458,branchY[i],row.r2,branches[i],1.74);
    [branchY[i],lower].forEach((yy, j) => {
      const k = 2 * i + j;
      guide((j ? fold : route)(458,yy,623,outputY[k]),row.leafPowersMw[k],1.89,probe,.73);
    });
  });
  label(285,150,'Ring A');
  label(477,40,'Ring B₀');
  label(477,188,'Ring B₁');
  const chosen = gates[gate];
  for (const [i,y] of outputY.entries()) {
    const enabled = chosen.includes(i);
    label(635,y - 12,['00','01','10','11'][i]);
    if (enabled) guide(route(623,y,730,165),row.leafPowersMw[i],2.62,probe,.63);
    else {
      guide(straight(623,y,669,y),row.leafPowersMw[i],2.62,'#92afbe',.63);
      label(693,y,'Dump','ol-faint');
    }
  }
  if (chosen.length > 1) {
    label(738,143,'Combiner');
    guide(route(730,165,780,260),row.combinerOtherMw,3.25,'#92afbe');
    label(806,260,'Dump','ol-faint');
  }
  guide(straight(730,165,818,165),row.outputMw,3.25,probe);
  label(835,165,'PD');
  label(807,199,'Output ' + row.observed,'ol-output');
}
function stop() {
  cancelAnimationFrame(frame);
  frame = 0;
}
function animate() {
  stop();
  if (reduced.matches) {
    byId('animation-status').textContent = 'Reduced motion is on. Waveguide brightness shows the calculated signal.';
    return;
  }
  let start;
  function step(now) {
    start ??= now;
    const t = (now-start)/1000;
    for (const track of tracks) {
      const {path,length,power,delay,duration,laps,glow} = track;
      const elapsed = t-delay;
      const circulating = laps > 1;
      const visible = elapsed >= 0 && elapsed <= duration;
      const buildup = circulating ? 1-Math.exp(-5*Math.max(0, elapsed)/duration) : 1;
      const opacity = buildup * Math.min(1, Math.sqrt(power / state.sourceMw));
      for (const [i,pulse] of glow.entries()) {
        const advance = elapsed / duration * laps - i * .032;
        pulse.setAttribute('visibility', visible && advance >= 0 ? 'visible' : 'hidden');
        if (!visible || advance < 0) continue;
        const position = path.getPointAtLength((circulating ? advance % 1 : Math.min(1, advance)) * length);
        pulse.setAttribute('cx', position.x);
        pulse.setAttribute('cy', position.y);
        pulse.setAttribute('opacity', opacity * (1-i*.17));
      }
    }
    if (t < 4.25) {
      frame = requestAnimationFrame(step);
    } else {
      frame = 0;
      byId('animation-status').textContent = 'Probe reached the output. Replay after changing an input or a parameter.';
    }
  }
  byId('animation-status').textContent = 'Following the optical inputs and probe through the circuit.';
  frame = requestAnimationFrame(step);
}
function drawSpectrum(samples, inspected, laserNm) {
  const plot = byId('spectrum');
  plot.replaceChildren();
  const min = samples[0].wavelengthNm, max = samples.at(-1).wavelengthNm;
  const x = nm => 36 + (nm - min) / (max - min) * 348;
  const y = fraction => 137 - 119 * fraction;
  for (const t of [0,.5,1]) {
    svg(plot,'path',{d:'M 36 ' + y(t) + ' H 384',class:'ol-gridline'});
    svg(plot,'text',{x:5,y:y(t)+4},Math.round(t*100)+'%');
  }
  for (const [key, color] of [['through','#69ead4'],['drop','#8fadff'],['loss','#ffbb76']]) {
    svg(plot,'polyline',{points:samples.map(s=> x(s.wavelengthNm) + ',' + y(s[key])).join(' '),fill:'none',stroke:color,'stroke-width':2.4});
  }
  if (laserNm >= min && laserNm <= max) svg(plot,'path',{d:'M ' + x(laserNm) + ' 10 V 137',class:'ol-wire'});
  svg(plot,'text',{x:36,y:157},wavelength(min)+' nm');
  svg(plot,'text',{x:384,y:157,'text-anchor':'end'},wavelength(max)+' nm');
  byId('probe-marker').textContent = laserNm < min || laserNm > max
    ? 'The probe is outside the displayed resonance window.'
    : 'The dotted line marks the current probe wavelength.';
  plot.setAttribute('aria-label','Port transmission around ' + inspected.resonanceNm.toFixed(3) + ' nanometres');
}
function render(play = false) {
  stop();
  if (panel.hidden) return;
  const gate = byId('gate').value;
  const rows = truthTable(state, gate);
  const row = rows[bits[0]*2 + bits[1]];
  const budget = energy(state, row);
  const inspected = byId('inspect').value === 'A' ? row.r1 : row.r2;
  const samples = spectrum(state, inspected === row.r1 ? row.drives[0] : row.drives[1]);
  latest = {chipNumber:11, modelVersion:'1.0.0', evidence:'educational coupled-mode model',
    physicalMeasurement:false, gate, settings:{...state}, inputs:bits.slice(),
    dataReceiverThresholdMw:inputThresholdMw, sensorPlane:'before ideal output detector',
    truthTable:rows.map(r=>({...r, energy:energy(state,r)})), spectrum:samples,
    spectrumRing:byId('inspect').value};
  for (const [i, id] of ['a','b'].entries()) {
    byId(id).textContent = id.toUpperCase() + ' = ' + bits[i];
    byId(id).setAttribute('aria-pressed', Boolean(bits[i]));
  }
  byId('routing').textContent = gateHelp[gate];
  byId('outputs').textContent = 'Optical output ' + mw(row.outputMw) + ' ' +
    (row.observed ? '≥ ' : '< ') + mw(state.thresholdMw) + ' → detected ' + row.observed +
    '. Expected ' + row.expected + (row.observed === row.expected ? ' · match.' : ' · mismatch.');
  byId('decode').textContent = 'Receiver drives · A ' + fmt(row.drives[0]) + ' V · B ' + fmt(row.drives[1]) + ' V';
  byId('table').replaceChildren();
  for (const candidate of rows) {
    const tr = el(byId('table'),'tr');
    if (candidate === row) tr.className = 'ol-current';
    for (const value of [candidate.a,candidate.b,mw(candidate.outputMw),candidate.observed,candidate.expected]) el(tr,'td',value);
  }
  const high = Math.min(...rows.filter(r=>r.expected).map(r=>r.outputMw));
  const low = Math.max(...rows.filter(r=>!r.expected).map(r=>r.outputMw));
  byId('margin').textContent = 'Worst-case decision margin ' + mw(Math.min(high-state.thresholdMw,state.thresholdMw-low)) +
    '. A negative margin means at least one readout can disagree with the truth table.';
  metrics(byId('ring-metrics'), [
    ['Resonance', inspected.resonanceNm.toFixed(3)+' nm'], ['Probe detuning',fmt(inspected.detuningGhz)+' GHz'],
    ['Loaded linewidth',fmt(inspected.linewidthGhz)+' GHz'], ['Loaded Q',fmt(inspected.loadedQ)],
    ['Energy lifetime',fmt(inspected.lifetimePs)+' ps'], ['Approx. free spectral range',fmt(inspected.fsrGhz)+' GHz'],
    ['Through / drop at probe',fmt(100*inspected.throughPower)+'% / '+fmt(100*inspected.dropPower)+'%'],
    ['Power circulating / launched at ring',fmt(inspected.buildup)+'×']
  ]);
  metrics(byId('optical-budget'), [
    ['Launched power · A + B + probe',mw(budget.opticalInMw)], ['Probe / detector power',mw(state.sourceMw)+' / '+mw(row.outputMw)],
    ['Intrinsic ring / probe link loss',mw(row.ringLossMw)+' / '+mw(row.routeLossMw)],
    ['Unselected probe / combiner dumps',mw(row.unselectedMw)+' / '+mw(row.combinerOtherMw)],
    ['Probe-to-detector attenuation',row.insertionLossDb === null ? 'No signal' : fmt(row.insertionLossDb)+' dB'],
    ['Launched / detected optical energy',fj(budget.opticalInFj)+' / '+fj(budget.opticalOutFj)]
  ]);
  metrics(byId('electrical-budget'), [
    ['Ring switching · single edge',fj(budget.ringEdgeFj)], ['Ring switching · mean per slot',fj(budget.switchingFj)],
    ['Laser electricity per slot',fj(budget.laserFj)], ['Control drivers per slot',fj(budget.driverFj)],
    ['Three receivers per slot',fj(budget.receiversFj)], ['Static circuitry per slot',fj(budget.otherFj)],
    ['Estimated electrical system total',fj(budget.systemFj)]
  ]);
  diagram(row,gate);
  drawSpectrum(samples,inspected,state.wavelengthNm);
  byId('animation-status').textContent = 'Ready to replay. Brightness indicates calculated optical power.';
  if (play) animate();
}
for (const [key,[name,unit,min,max,step]] of Object.entries(controls)) {
  const field = document.createElement('label');
  field.textContent = name;
  const input = el(field,'input');
  input.type='range';
  Object.assign(input,{min,max,step,value:state[key]});
  const value=el(field,'output');
  const update = () => {
    const displayed = key === 'wavelengthNm' ? wavelength(state[key]) : fmt(state[key]);
    value.textContent = displayed + (unit ? ' ' + unit : '');
    input.setAttribute('aria-valuetext',value.textContent);
  };
  fields.set(key,{input,update});
  input.addEventListener('input',()=>{state[key]=Number(input.value);update();render();});
  byId(['rateGhz','wallPlug','receiverFj','driverFj','overheadMw'].includes(key) ? 'energy-controls' : 'controls').append(field);
  update();
}
for (const [i, id] of ['a','b'].entries()) byId(id).onclick=()=>{bits[i]^=1;render(true);};
byId('gate').onchange=()=>render(true);
byId('inspect').onchange=()=>render();
byId('preset').onchange=event=>{
  const [adjust,next,message] = examples[event.target.value];
  Object.assign(state,defaults,adjust);
  bits=next.slice();
  for (const [key,{input,update}] of fields) {input.value=state[key];update();}
  byId('lesson').textContent=message;
  render(true);
};
byId('play').onclick=animate;
document.getElementById('pulse-start').addEventListener('click',()=>{if (!panel.hidden && !tab.hidden) animate();});
narrow.addEventListener('change',()=>render());
reduced.addEventListener('change',()=>render());
function selectChip() {panel.hidden=design.value!=='optical-logic';render();}
design.addEventListener('change',selectChip);
new MutationObserver(()=>{if(tab.hidden)stop();else if(!panel.hidden)render();}).observe(tab,{attributes:true,attributeFilter:['hidden']});
byId('export').onclick=()=>{
  const rows = latest.truthTable.map(r=>[r.a,r.b,r.expected,r.observed,r.outputMw,r.ringLossMw,r.routeLossMw,r.energy.systemFj]);
  const table = ['a,b,expected,observed,output_mW,ring_loss_mW,route_loss_mW,system_estimate_fJ',
    ...rows.map(row=>row.join(','))].join('\n');
  const spectra = ['wavelength_nm,through_fraction,drop_fraction,intrinsic_loss_fraction',
    ...latest.spectrum.map(s=>[s.wavelengthNm,s.through,s.drop,s.loss].join(','))].join('\n');
  const json = JSON.stringify({...latest, exportedUtc:new Date().toISOString()},null,2);
  const type=byId('format').value;
  const stem='OPA-CHIP11-v1.0.0';
  const exportTools=globalThis.PhotonicBenchmarkExport;
  const files={'experiment.json':json,'truth-table.csv':table,'ring-spectrum.csv':spectra};
  const choices={json:'experiment.json',csv:'truth-table.csv',spectrum:'ring-spectrum.csv'};
  const file=choices[type];
  const blob=file ? new Blob([files[file]],{type:type==='json'?'application/json':'text/csv;charset=utf-8'}) : exportTools.zip(files);
  exportTools.download(stem + '-' + (file ?? 'results.zip'),blob);
  byId('export-status').textContent = 'Download requested.';
};
selectChip();
