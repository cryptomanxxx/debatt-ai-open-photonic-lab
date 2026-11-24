import {assumptions, defaults, evaluate, presets, presetSettings} from './photonic-memory-model.mjs';

const streamed = {...defaults, residency:'Stream every layer'};
const airllm = presetSettings(presets.find(p => p.id === 'airllm'));
const moe = presetSettings(presets.find(p => p.id === 'moe'));

export const cases = [
  {id:'dense-link-limited', settings:streamed, ingressGBs:200},
  {id:'dense-ingress-limited', settings:streamed, ingressGBs:10},
  {id:'dense-controller-limited', settings:{...streamed,controllerGBs:8}, ingressGBs:200},
  {id:'dense-host-ram-limited', settings:{...streamed,ramGBs:10}, ingressGBs:200},
  {id:'dense-ssd-limited', settings:airllm, ingressGBs:200},
  {id:'dense-vram-resident', settings:{...defaults,vramGB:64,pumpMw:.1}, ingressGBs:10},
  {id:'dense-long-context', settings:{...streamed,context:4096,vramGBs:12}, ingressGBs:200},
  {id:'moe-tiered', settings:moe, ingressGBs:200},
  {id:'moe-dense-control', settings:{...moe,workload:'Dense'}, ingressGBs:200},
  {id:'moe-with-overfetch', settings:{...moe,readAmp:3}, ingressGBs:200},
  {id:'dense-optical-power-failure', settings:{...streamed,pumpMw:.1}, ingressGBs:200},
];

function capIngress(path, result, settings, ingressGBs, optical) {
  if (!path.metrics) return {payloadGBs:path.payloadGBs, blocked:path.blocked, metrics:null};
  const m = path.metrics;
  const ingressSeconds = result.linkGB / ingressGBs;
  const concurrentSeconds = Math.max(...path.stages.map(stage => stage.seconds));
  const addedSeconds = Math.max(0, ingressSeconds - concurrentSeconds);
  const transferSeconds = m.transferSeconds + addedSeconds;
  const tokenSeconds = m.tokenSeconds + addedSeconds;
  const answerSeconds = tokenSeconds * settings.tokens;
  const addedRunSeconds = addedSeconds * settings.tokens;
  const opticalFixedW = optical && result.linkGB > 0 ?
    settings.pumpMw / 1000 / assumptions.laserEfficiency + assumptions.opticalBiasW : 0;
  const energy = {...m.energy,
    link:m.energy.link + opticalFixedW * addedRunSeconds,
    platform:m.energy.platform + assumptions.platformW * addedRunSeconds,
  };
  const bits = result.linkGB * 8e9 * settings.tokens;
  const ingressDominates = addedSeconds > 0 && transferSeconds > Math.max(...path.timing.slice(1).map(stage => stage.seconds));
  return {
    payloadGBs:path.payloadGBs, blocked:path.blocked,
    metrics:{
      ...m, ingressSeconds, transferSeconds, tokenSeconds, answerSeconds,
      effectiveGBs:transferSeconds ? result.linkGB / transferSeconds : null, tokenRate:1 / tokenSeconds,
      linkPj:bits ? energy.link * 1e12 / bits : null,
      bottleneck:ingressDominates ? 'Accelerator ingress' : m.bottleneck,
      energy, totalJ:Object.values(energy).reduce((sum, value) => sum + value, 0),
    },
  };
}

export function compare({settings, ingressGBs}) {
  if (!Number.isFinite(ingressGBs) || ingressGBs <= 0) throw new RangeError('A positive accelerator ingress rate is required');
  const wide = evaluate(settings);
  const matchedSettings = {
    ...settings,
    channelGbps:wide.electronic.payloadGBs * 8 / (settings.channels * assumptions.wdmPayload),
  };
  const matched = evaluate(matchedSettings);
  const electronic = capIngress(wide.electronic,wide,settings,ingressGBs,false);
  const widerWdm = capIngress(wide.photonic,wide,settings,ingressGBs,true);
  const matchedWdm = capIngress(matched.photonic,matched,matchedSettings,ingressGBs,true);
  const baseline = electronic.metrics;
  const bits = wide.linkGB * 8e9 * settings.tokens;
  const dynamicPj = (settings.modulatorPj + settings.detectorPj + settings.eoPj + settings.oePj) / assumptions.wdmPayload;
  function relative(path) {
    const {metrics:m} = path;
    return {
      ...path,
      speedupVsPcie:m && baseline ? baseline.tokenSeconds / m.tokenSeconds : null,
      systemEnergyRatioVsPcie:m && baseline ? m.totalJ / baseline.totalJ : null,
      breakEvenOpticalDynamicPjPerPayloadBit:m && baseline && bits ?
        dynamicPj + (baseline.totalJ - m.totalJ) / (bits * 1e-12) : null,
    };
  }
  return {
    settings, ingressGBs, checkpointGB:wide.totalGB, activeParametersB:wide.activeParametersB,
    activeWeightGB:wide.activeGB, linkGBPerToken:wide.linkGB, ssdGBPerToken:wide.ssdGB,
    hostGBPerToken:wide.linkGB + wide.ssdGB, kvPeakGB:wide.kvPeakGB, kvGBPerToken:wide.kvTrafficGB,
    matchedChannelGbps:matchedSettings.channelGbps, matchedOpticalScreen:matched.optical.problems,
    wideOpticalScreen:wide.optical.problems, electronic,
    matchedWdm:relative(matchedWdm), widerWdm:relative(widerWdm),
  };
}
