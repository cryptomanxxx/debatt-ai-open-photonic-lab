const C = 299792458;
const GB = 1e9;
const bitsPerWeight = {FP32: 32, FP16: 16, FP8: 8, '4-bit': 4};
const pcieRates = [0, 2.5, 5, 8, 16, 32, 64];

export const assumptions = Object.freeze({
  ssdPayload: .85, ramPayload: .8, pciePayload: .85, wdmPayload: .85,
  computeUtilization: .5, localPayload: .8, ramReserveGB: 1, vramReserveGB: .75,
  kvHeadDim: 128, kvBytes: 2, centerNm: 1550, nrzGuard: 1.25, groupIndex: 4,
  combEfficiency: .25, laserEfficiency: .25, opticalBiasW: .5,
  pciPj: 12, ssdPj: 50, ramPj: 15, localPj: 4, platformW: 35, computeW: 120,
  otherSeconds: .0002,
});

export const defaults = Object.freeze({
  parametersB: 70, precision: '4-bit', workload: 'Dense', layers: 80,
  kvHeads: 8, context: 512, tokens: 32, activePercent: 12, readAmp: 1.15,
  vramGB: 8, ramGB: 64, residency: 'Warm cache', ssdGBs: 7,
  ramGBs: 150, controllerGBs: 240, vramGBs: 600, pcieGen: 4, lanes: 8,
  channels: 16, channelGbps: 50, spacingGHz: 100, combSpanTHz: 8,
  pumpMw: 100, lengthCm: 5, lossDbCm: .2, insertionDb: 4, sensitivityUw: 20,
  modulatorPj: .3, detectorPj: .2, eoPj: 1, oePj: 1, computeTops: 100,
});

export const presets = [
  {id:'airllm', title:'Run a 405B Model on an 8 GB GPU', overrides:{parametersB:405, precision:'FP16', layers:126, context:256, tokens:24, ramGB:32, residency:'Stream every layer'}, lesson:'Follow one layer from SSD to GPU, then repeat for the next token. The full checkpoint is much larger than VRAM. Compare disk time with GPU compute time.'},
  {id:'ram', title:'SSD vs RAM', overrides:{ramGB:16, residency:'Stream every layer'}, lesson:'Raise host RAM from 16 to 64 GB. Compare SSD weight reads and time per token before and after the full checkpoint fits.'},
  {id:'pcie', title:'The PCIe Bottleneck', overrides:{pcieGen:3, lanes:4, computeTops:400, residency:'Stream every layer'}, lesson:'Raise GPU throughput, then raise PCIe lanes or generation. Which change makes the electronic path faster?'},
  {id:'photonic', title:'Photonic Memory Interconnect', overrides:{residency:'Stream every layer'}, lesson:'Compare the two paths with the weights in host RAM. Increase wavelength count and then reduce memory-controller throughput to see the bottleneck move.'},
  {id:'wdm', title:'Scaling with WDM', overrides:{channels:1, pumpMw:300, residency:'Stream every layer'}, lesson:'Sweep 1, 8, 16, 32 and 64 wavelengths. Compare raw and effective bandwidth, receiver margin and joules. Optical power is shared across all enabled channels.'},
  {id:'ssd', title:'When Photonics Is Not Enough', overrides:{ramGB:8, ssdGBs:1, channels:64, pumpMw:300, residency:'Stream every layer'}, lesson:'The optical link can move bits faster than the SSD supplies them. Increase SSD throughput or RAM first. Then lower DRAM bandwidth and watch the limiting stage change.'},
  {id:'moe', title:'Dense vs Mixture of Experts', overrides:{parametersB:235, layers:80, workload:'Mixture of Experts', activePercent:10, readAmp:1.2}, lesson:'Toggle Dense and Mixture of Experts at the same checkpoint size. Compare active weights with the bytes crossing the link and read from SSD. Change overfetch to model less selective expert loading.'},
  {id:'custom', title:'Build Your Own Photonic AI System', overrides:{}, lesson:'Choose a workload and a target token rate. Reduce energy while maintaining a positive receiver margin. Compare the settings that achieve both goals.'},
];

export function presetSettings(preset) {
  return {...defaults, ...preset.overrides};
}

export function opticalLink(s) {
  const a = assumptions;
  const lossDb = s.insertionDb + s.lengthCm * s.lossDbCm;
  const receivedUw = 1000 * s.pumpMw * a.combEfficiency / s.channels * 10 ** (-lossDb / 10);
  const marginDb = 10 * Math.log10(receivedUw / s.sensitivityUw);
  const occupiedTHz = ((s.channels - 1) * s.spacingGHz + s.channelGbps * a.nrzGuard) / 1000;
  const rawGBs = s.channels * s.channelGbps / 8;
  const problems = [];
  if (s.channels > 1 && s.spacingGHz < s.channelGbps * a.nrzGuard) problems.push('Channel spacing is too tight for the assumed NRZ signal.');
  if (occupiedTHz > s.combSpanTHz) problems.push('The requested spectrum exceeds the usable comb span.');
  if (marginDb < 0) problems.push('Received power per wavelength is below the assumed receiver sensitivity.');
  return {
    lossDb, receivedUw, marginDb, occupiedTHz, rawGBs, problems,
    payloadGBs: problems.length ? 0 : rawGBs * a.wdmPayload,
    flightSeconds: s.lengthCm / 100 * a.groupIndex / C,
    wavelengthNm: Array.from({length:s.channels}, (_, i) =>
      C / (C / (a.centerNm * 1e-9) + (i - (s.channels - 1) / 2) * s.spacingGHz * 1e9) * 1e9),
  };
}

export function evaluate(s) {
  const a = assumptions;
  const optical = opticalLink(s);
  const lineEncoding = s.pcieGen <= 2 ? .8 : s.pcieGen <= 5 ? 128 / 130 : 1;
  const pcieRawGBs = pcieRates[s.pcieGen] * s.lanes / 8;
  const pciePayloadGBs = pcieRawGBs * lineEncoding * a.pciePayload;
  const totalGB = s.parametersB * bitsPerWeight[s.precision] / 8;
  const moe = s.workload === 'Mixture of Experts';
  const activeFraction = moe ? s.activePercent / 100 : 1;
  const activeGB = totalGB * activeFraction;
  const kvStepGB = 2 * s.layers * s.kvHeads * a.kvHeadDim * a.kvBytes / GB;
  const kvPeakGB = kvStepGB * (s.context + s.tokens);
  const kvTrafficGB = kvStepGB * (s.context + (s.tokens - 1) / 2 + 1);
  const vramAvailable = s.vramGB - a.vramReserveGB - kvPeakGB;
  // The single staging buffer is sized for an average full layer for dense
  // weights, or an average overfetched active layer for a sparse checkpoint.
  const stagingGB = Math.min(totalGB, activeGB * (moe ? s.readAmp : 1)) / s.layers;
  const warm = s.residency === 'Warm cache';
  const gpuResidentGB = warm && vramAvailable >= totalGB ? totalGB :
    warm ? Math.max(0, vramAvailable - stagingGB) : 0;
  const hostAvailable = Math.max(0, s.ramGB - a.ramReserveGB);
  const hostResidentGB = gpuResidentGB === totalGB ? 0 :
    hostAvailable >= totalGB - gpuResidentGB ? totalGB - gpuResidentGB :
      warm ? Math.max(0, hostAvailable - stagingGB) : 0;
  // Uniform activity across the full checkpoint approximates cache hits.
  // The overfetch multiplier applies only to misses and never exceeds the uncached inventory.
  const linkInventory = totalGB - gpuResidentGB;
  const ssdInventory = Math.max(0, linkInventory - hostResidentGB);
  const readFraction = Math.min(1, activeFraction * (moe ? s.readAmp : 1));
  const linkGB = linkInventory * readFraction;
  const ssdGB = ssdInventory * readFraction;
  const hostTrafficGB = linkGB + ssdGB;
  const issues = [];
  if (gpuResidentGB < totalGB && vramAvailable < stagingGB) issues.push('VRAM cannot hold one modeled layer buffer, peak KV cache and workspace.');
  if (ssdGB > 0 && hostAvailable < stagingGB) issues.push('RAM cannot hold one modeled layer buffer and the host reserve.');

  const kvSeconds = kvTrafficGB / (s.vramGBs * a.localPayload);
  const localWeightSeconds = activeGB / (s.vramGBs * a.localPayload);
  const weightFlopsB = 2 * s.parametersB * activeFraction;
  const attentionFlopsB = 4 * s.layers * (4 * s.kvHeads) * a.kvHeadDim * (s.context + (s.tokens - 1) / 2) / GB;
  const computeSeconds = (weightFlopsB + attentionFlopsB) / (1000 * s.computeTops * a.computeUtilization);

  function path(isOptical) {
    const rawGBs = isOptical ? optical.rawGBs : pcieRawGBs;
    const payloadGBs = isOptical ? optical.payloadGBs : pciePayloadGBs;
    const blocked = [...issues, ...(isOptical && linkGB > 0 ? optical.problems : [])];
    const stages = [
      {name:'SSD', seconds:ssdGB / (s.ssdGBs * a.ssdPayload)},
      {name:'Host RAM', seconds:hostTrafficGB / (s.ramGBs * a.ramPayload)},
      {name:'Memory controller', seconds:linkGB / s.controllerGBs},
      {name:isOptical ? 'Optical I/O' : 'PCIe', seconds:linkGB && payloadGBs ? linkGB / payloadGBs : 0},
    ];
    const slowest = stages.reduce((best, stage) => stage.seconds > best.seconds ? stage : best);
    const flightSeconds = isOptical && linkGB > 0 ? optical.flightSeconds * s.layers : 0;
    const transferSeconds = slowest.seconds + flightSeconds;
    const timing = [
      {name:slowest.name, seconds:transferSeconds}, {name:'Local weight reads', seconds:localWeightSeconds},
      {name:'KV-cache traffic', seconds:kvSeconds}, {name:'Accelerator compute', seconds:computeSeconds},
      {name:'Other decode costs', seconds:a.otherSeconds},
    ];
    const tokenSeconds = timing.reduce((sum, stage) => sum + stage.seconds, 0);
    const answerSeconds = tokenSeconds * s.tokens;
    const bottleneck = timing.reduce((best, stage) => stage.seconds > best.seconds ? stage : best).name;
    const linkBits = linkGB * 8 * GB * s.tokens;
    const opticalFixedJ = isOptical && linkBits ? (s.pumpMw / 1000 / a.laserEfficiency + a.opticalBiasW) * answerSeconds : 0;
    const dynamicPj = isOptical ? (s.modulatorPj + s.detectorPj + s.eoPj + s.oePj) / a.wdmPayload : a.pciPj;
    const linkJ = dynamicPj * linkBits * 1e-12 + opticalFixedJ;
    const energy = {
      storage: a.ssdPj * ssdGB * 8 * GB * s.tokens * 1e-12,
      hostMemory: a.ramPj * hostTrafficGB * 8 * GB * s.tokens * 1e-12,
      link: linkJ,
      localMemory: a.localPj * (kvTrafficGB + activeGB) * 8 * GB * s.tokens * 1e-12,
      compute: a.computeW * computeSeconds * s.tokens,
      platform: a.platformW * answerSeconds,
    };
    const metrics = blocked.length ? null : {
      tokenSeconds, answerSeconds, tokenRate:1 / tokenSeconds, transferSeconds,
      effectiveGBs:transferSeconds ? linkGB / transferSeconds : null, bottleneck,
      linkPj:linkBits ? linkJ / linkBits * 1e12 : null, energy,
      totalJ:Object.values(energy).reduce((sum, value) => sum + value, 0),
    };
    return {rawGBs, payloadGBs, stages, timing, blocked, metrics};
  }
  return {
    totalGB, activeGB, activeParametersB:s.parametersB * activeFraction, stagingGB,
    vramAvailable, gpuResidentGB, hostResidentGB, kvPeakGB, kvTrafficGB, linkGB, ssdGB,
    optical, electronic:path(false), photonic:path(true),
  };
}
