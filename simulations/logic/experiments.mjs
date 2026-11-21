import {mkdirSync, writeFileSync} from 'node:fs';
import {defaults, energy, evaluate, gates, inputThresholdMw, pairs, truthTable} from '../../web/chip11/optical-logic-model.mjs';

const evidence = 'steady-state compact-model calculation';
const gateNames = Object.keys(gates);

function gatesExperiment() {
  const scenarios = [
    ['nominal', {}], ['detuned', {trimNm:.32}], ['no_drive', {voltageV:0}],
    ['starved_data', {sourceMw:.015}], ['lossy_links', {routeLossDb:4}],
    ['phase_error', {pathPhaseDeg:90}]
  ];
  const rows = scenarios.flatMap(([scenario, overrides]) => gateNames.flatMap(gate =>
    truthTable({...defaults,...overrides},gate).map(row => ({
      scenario, gate, a:row.a, b:row.b, expected:row.expected, observed:row.observed,
      output_mW:row.outputMw, input_threshold_mW:inputThresholdMw, loss_mW:row.ringLossMw+row.routeLossMw
    }))));
  const screens = {
    nominal_all_four_truth_tables: rows.filter(r=>r.scenario==='nominal').every(r=>r.observed===r.expected),
    adverse_controls_expose_errors: scenarios.slice(1,-1).every(([name]) =>
      rows.some(r=>r.scenario===name && r.observed!==r.expected)),
    phase_perturbation_changes_coherent_combiner: rows.some(r=>r.scenario==='phase_error' && rows.some(n=>
      n.scenario==='nominal' && n.gate===r.gate && n.a===r.a && n.b===r.b &&
      Math.abs(n.output_mW-r.output_mW)>1e-4))
  };
  return {rows,screens,settings:scenarios,scope:'Receiver-assisted routing. Detuning, phase, loss and drive screens use deterministic perturbations.'};
}

function cascadedExperiment() {
  // First optical output is connected to the second stage data receiver before detection,
  // letting the next receiver threshold determine the regenerated drive.
  const lossesDb = [0,3,6,9,12,15,18];
  const rows = lossesDb.flatMap(interstageLoss => pairs.flatMap(([a,b])=>
    [0,1].map(c => {
      const upstream = evaluate(defaults,'AND',a,b);
      const intermediateMw = upstream.outputMw * 10 ** (-interstageLoss/10);
      const stage = evaluate(defaults,'XOR',a*b,c,[intermediateMw,c*defaults.sourceMw]);
      return {loss_dB:interstageLoss,a,b,c,intermediate_launch_mW:intermediateMw,
        intermediate_received_mW:intermediateMw*10**(-defaults.routeLossDb/10),
        regenerated_bit:Number(stage.drives[0]>0), final_mW:stage.outputMw,
        expected:(a*b)^c, observed:stage.observed};
    })));
  const screens = {
    all_eight_nominal_vectors: rows.filter(r=>r.loss_dB===0).every(r=>r.observed===r.expected),
    adverse_loss_causes_failure: rows.some(r=>r.loss_dB===18 && r.observed!==r.expected),
    regenerative_drive_uses_received_power: rows.every(r=>
      r.regenerated_bit===Number(r.intermediate_received_mW>=inputThresholdMw))
  };
  return {rows,screens,settings:{lossesDb},scope:'AND→XOR with one downstream data receiver, electrical regeneration and a fresh optical probe. No autonomous all-optical cascade, fan-out or timing model.'};
}

function energyExperiment() {
  const rates = [1,5,10,20];
  const efficiencies = [.10,.20,.40];
  const rows = rates.flatMap(rateGhz=>efficiencies.flatMap(wallPlug=>
    truthTable({...defaults,rateGhz,wallPlug},'AND').map(row=>{
      const e=energy({...defaults,rateGhz,wallPlug},row);
      return {rate_GHz:rateGhz,wall_plug_efficiency:wallPlug,a:row.a,b:row.b,
        detected:row.observed,optical_input_fJ:e.opticalInFj,optical_output_fJ:e.opticalOutFj,
        laser_fJ:e.laserFj,switching_fJ:e.switchingFj,drivers_fJ:e.driverFj,
        receivers_fJ:e.receiversFj,static_fJ:e.otherFj,system_fJ:e.systemFj};
    })));
  const close = (a,b) => Math.abs(a-b) < 1e-9;
  const screens = {
    laser_supplies_optical_input: rows.every(r=>close(r.laser_fJ*r.wall_plug_efficiency,r.optical_input_fJ)),
    system_sums_electrical_terms: rows.every(r=>close(r.system_fJ,
      r.laser_fJ+r.switching_fJ+r.drivers_fJ+r.receivers_fJ+r.static_fJ)),
    system_exceeds_switching_only: rows.every(r=>r.system_fJ>r.switching_fJ)
  };
  return {rows,screens,settings:{rates,efficiencies},
    scope:'Parameterized energy accounting. Rate changes are assumed and do not predict attainable speed. No measured hardware benchmark.'};
}

const runById = {'opa-logic-002':gatesExperiment,'opa-logic-003':cascadedExperiment,'opa-logic-004':energyExperiment};
export function runExperiment(id) {
  const resultDir = 'results/' + id;
  if (!Object.hasOwn(runById,id)) throw new Error('Select opa-logic-002, opa-logic-003 or opa-logic-004');
  const {rows,screens,scope,settings} = runById[id]();
  mkdirSync(resultDir,{recursive:true});
  const columns = Object.keys(rows[0]);
  const csv = [columns.join(','),...rows.map(row=>columns.map(key=>row[key]).join(','))].join('\n')+'\n';
  const report = {experiment:id.toUpperCase(),model_version:'1.0.0',evidence,physical_measurement:false,
    defaults,settings,scope,screens,rows};
  writeFileSync(resultDir+'/result.json',JSON.stringify(report,null,2)+'\n');
  writeFileSync(resultDir+'/results.csv',csv);
  console.log(id, screens);
  if (!Object.values(screens).every(Boolean)) process.exitCode = 1;
}
