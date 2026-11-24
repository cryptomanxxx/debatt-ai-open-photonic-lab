import {mkdirSync, writeFileSync} from 'node:fs';
import {assumptions, defaults, evaluate, presets, presetSettings} from './photonic-memory-model.mjs';

const wdm = presets.find(preset => preset.id === 'wdm');
const cases = [
  ...presets.map(preset => [preset.id, presetSettings(preset)]),
  ...[1,8,16,32,64].map(channels => ['wdm-' + channels, {...presetSettings(wdm),channels}]),
  ['weak-optical-pump', {...defaults,pumpMw:.1}],
  ['vram-resident', {...defaults,vramGB:64}],
];
const rows = cases.flatMap(([scenario, settings]) => {
  const result = evaluate(settings);
  return ['electronic','photonic'].map(architecture => {
    const path = result[architecture];
    return {
      scenario, architecture, checkpoint_GB:result.totalGB, active_weights_GB:result.activeGB,
      ssd_GB_per_token:result.ssdGB, link_GB_per_token:result.linkGB,
      raw_link_GB_s:path.rawGBs, payload_link_GB_s:path.payloadGBs,
      end_to_end_GB_s:path.metrics?.effectiveGBs ?? null, answer_s:path.metrics?.answerSeconds ?? null,
      tokens_s:path.metrics?.tokenRate ?? null, link_pJ_bit:path.metrics?.linkPj ?? null,
      answer_J:path.metrics?.totalJ ?? null, limiter:path.metrics?.bottleneck ?? 'Blocked',
    };
  });
});
const report = {
  experiment:'OPA-MEM-001', model_version:'1.0.0', evidence:'analytical teaching model',
  physical_measurement:false, assumptions, settings:Object.fromEntries(cases), rows,
};
const dir = 'results/opa-mem-001';
mkdirSync(dir,{recursive:true});
writeFileSync(dir + '/result.json',JSON.stringify(report,null,2) + '\n');
writeFileSync(dir + '/results.csv',[Object.keys(rows[0]).join(','),...rows.map(row => Object.values(row).join(','))].join('\n') + '\n');
