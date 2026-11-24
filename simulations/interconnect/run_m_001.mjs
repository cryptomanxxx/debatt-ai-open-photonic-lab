import {mkdirSync, writeFileSync} from 'node:fs';
import {assumptions} from './photonic-memory-model.mjs';
import {cases, compare} from './memory-bottlenecks.mjs';

const scenarios = cases.map(({id,...inputs}) => ({id,...compare(inputs)}));
const report = {
  experiment:'OPA-M-001', version:'1.0.0', evidence:'analytical sensitivity study',
  physical_measurement:false, base_model:'OPA-MEM-001, single-request warm/streaming decode after prefill',
  assumptions, scenarios,
};
const rows = scenarios.flatMap(s => ['electronic','matchedWdm','widerWdm'].map(architecture => {
  const path = s[architecture], m = path.metrics;
  return {
    scenario:s.id, architecture, checkpoint_GB:s.checkpointGB, active_GB:s.activeWeightGB,
    ssd_GB_token:s.ssdGBPerToken, link_GB_token:s.linkGBPerToken, kv_GB_token:s.kvGBPerToken,
    ingress_GB_s:s.ingressGBs, payload_GB_s:path.payloadGBs,
    effective_GB_s:m?.effectiveGBs, decode_s_token:m?.tokenSeconds,
    tokens_s:m?.tokenRate, energy_J_answer:m?.totalJ, energy_J_token:m ? m.totalJ / s.settings.tokens : null,
    link_pJ_payload_bit:m?.linkPj, speedup_vs_pcie:path.speedupVsPcie,
    energy_ratio_vs_pcie:path.systemEnergyRatioVsPcie, limiting_stage:m?.bottleneck ?? 'Blocked',
    break_even_optical_dynamic_pJ_payload_bit:path.breakEvenOpticalDynamicPjPerPayloadBit,
  };
}));
const dir = 'results/opa-m-001';
mkdirSync(dir,{recursive:true});
writeFileSync(dir + '/result.json',JSON.stringify(report,null,2) + '\n');
writeFileSync(dir + '/results.csv',[Object.keys(rows[0]).join(','),...rows.map(row => Object.values(row).join(','))].join('\n') + '\n');
console.log(`${rows.length} analytical comparisons written to ${dir}`);
