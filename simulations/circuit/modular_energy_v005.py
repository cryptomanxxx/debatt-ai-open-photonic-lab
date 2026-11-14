"""OPA-MOD-005: conditional receiver-noise and system energy sensitivity.

Analytical budget, not hardware measurement. One signed real MVM per sample.
"""
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
from modular_power_budget_v002 import N, SIZES, SEED, workload, transmission

OUT = Path("results/opa-mod-005")
H = 6.62607015e-34
C = 299792458.
WAVELENGTH = 1550e-9
PHOTON_J = H*C/WAVELENGTH
TARGETS = (0.01, 0.03)
CASES = ("random_signed", "orthogonal", "rank_one", "ill_conditioned")


def prepare(w, x, b):
    k = N//b
    norm2 = k*np.sum(x*x, axis=0)
    scales = []
    for i in range(0, N, b):
        for j in range(0, N, b):
            scales.append(float(np.linalg.svd(w[i:i+b,j:j+b],
                                              compute_uv=False)[0]))
    # Independent real receiver noise on each tile output, amplified by
    # the tile's SVD scale and common input normalization.
    # Expected squared output error summed over all output coordinates.
    gain2 = b*sum(s*s for s in scales)*norm2
    ref2 = np.sum((w@x)**2, axis=0)
    if np.any(ref2 <= 0):
        raise ValueError("relative error target requires nonzero reference")
    return gain2/ref2


def counts(b):
    k = N//b
    tiles = k*k
    return dict(tiles=tiles, input_dac=N, output_adc=N*k,
                receiver_channels=N*k, link_values=N*(k-1),
                additions=N*(k-1), gain_multiplies=N*k,
                phase_controls=tiles*2*(b*(b-1)+b),
                attenuators=tiles*b)


def evaluate(b, factors, s, target):
    k = N//b
    q = counts(b)
    db = (2*b*s["column_db"] + math.log2(k)*s["splitter_db"]
          + s["interface_db"] + s["attenuator_db"]
          + (s["link_db"] if k>1 else 0))
    t = transmission(db)
    # Normalized real-field variance = photon_factor / launched photons
    # before scalar loss compensation. ADC noise is referred to the same
    # normalized input field; full-scale is fixed at +/-1.
    # Ideal uniform rounding approximation, not an ENOB measurement.
    adc_var = (2/(2**s["adc_bits"]-1))**2/12
    coeff = factors/t
    floor = float(np.max(coeff*adc_var))
    # Worst per-vector relative RMS target, not aggregate detected power.
    # Noise contributions add in variance; no deterministic hardware error.
    common = dict(tile_size=b, target_relative_rms=target,
                  loss_db=db, adc_error_floor_rms=math.sqrt(floor), **q)
    if floor >= target**2:
        return dict(**common, feasible=False, energy_j=None,
                    launched_photons=None, worst_relative_rms=None,
                    components_j=None)
    photons = float(np.max(s["photon_factor"]*coeff /
                           (target**2-coeff*adc_var)))
    worst = math.sqrt(float(np.max(coeff*(adc_var+s["photon_factor"]/photons))))
    rate = s["rate_hz"]*s["utilization"]
    # Fixed-rate, fully spatial deployment. Static power amortized over
    # completed vectors, with no free idle-state power gating.
    # Calibration/setup energy per control amortized over weight reuse.
    components = {
        "signal_laser": photons*PHOTON_J/s["laser_efficiency"],
        "local_oscillator": q["receiver_channels"]*s["lo_j"],
        "dac_and_modulation": q["input_dac"]*s["dac_j"],
        "adc_and_receiver": q["output_adc"]*s["adc_j"],
        "intermodule_transport": q["link_values"]*s["link_j"],
        "electronic_accumulation": (q["additions"]+q["gain_multiplies"])*s["arithmetic_j"],
        "static_control": (q["phase_controls"]+q["attenuators"])*s["control_w"]/rate,
        "setup_and_calibration": (q["phase_controls"]+q["attenuators"])*s["setup_j"]/s["reuse"],
        "fixed_system": s["fixed_w"]/rate,
    }
    total = sum(components.values())
    return dict(**common, feasible=True, energy_j=total,
                energy_per_mac_j=total/(N*N), launched_photons=photons,
                worst_relative_rms=worst, components_j=components)


def main():
    cases, x = workload()
    factors = {(name,b):prepare(cases[name],x,b) for name in CASES for b in SIZES}
    scenarios = []
    for col, link, bits, overhead, hold, reuse in itertools.product(
            (0.025,0.095,0.175), (0.,2.,6.,12.), (8,12,16),
            (0.1,10.), (1e-9,1e-3), (100,1000000)):
        scenarios.append(dict(column_db=col, link_db=link, adc_bits=bits,
            splitter_db=0.2, interface_db=2., attenuator_db=0.5,
            photon_factor=0.5, laser_efficiency=0.2,
            lo_j=overhead*1e-12, dac_j=overhead*1e-12,
            adc_j=overhead*1e-12*2**(bits-8),
            link_j=overhead*1e-12, arithmetic_j=0.1e-12,
            control_w=hold, setup_j=1e-9, reuse=reuse,
            rate_hz=1e9, utilization=0.5, fixed_w=0.01))
    rows = []
    for sid,s in enumerate(scenarios):
        for name in CASES:
            for target in TARGETS:
                group = [evaluate(b,factors[name,b],s,target) for b in SIZES]
                base = group[0]["energy_j"]
                for row in group:
                    e = row["energy_j"]
                    row.update(scenario=sid, case=name,
                               ratio_to_monolithic=e/base if e is not None and base is not None else None)
                rows.extend(group)
    # Independent small algebra and limiting-case tests.
    identity = prepare(np.eye(N), np.ones((N,1)), N)
    s = dict(scenarios[0], column_db=0., link_db=0., splitter_db=0.,
             interface_db=0., attenuator_db=0., adc_bits=16)
    a = evaluate(N,identity,s,0.03)
    more_loss = evaluate(N,identity,dict(s,column_db=0.01),0.03)
    bad = evaluate(N,identity,dict(s,adc_bits=2),0.001)
    checks = {
        "row_count": len(rows)==len(scenarios)*len(CASES)*len(TARGETS)*len(SIZES),
        "monolithic_counts": counts(N)["link_values"]==0 and counts(N)["output_adc"]==N,
        "tiled_counts": counts(32)["output_adc"]==512 and counts(32)["additions"]==384,
        "identity_noise_gain": bool(np.allclose(identity,N)),
        "loss_increases_photons": more_loss["launched_photons"]>a["launched_photons"],
        "adc_floor_rejection": not bad["feasible"],
        "target_met": all(r["worst_relative_rms"]<=r["target_relative_rms"]*(1+1e-10)
                          for r in rows if r["feasible"]),
        "energy_accounting": all(math.isclose(r["energy_j"],sum(r["components_j"].values()))
                                 and r["energy_j"]>0 for r in rows if r["feasible"]),
        "baseline_ratio": all(r["ratio_to_monolithic"]==1 for r in rows
                              if r["tile_size"]==N and r["feasible"]),
    }
    summary = []
    for b in SIZES:
        comparable = [r["ratio_to_monolithic"] for r in rows if r["tile_size"]==b
                      and r["ratio_to_monolithic"] is not None]
        summary.append(dict(tile_size=b, comparable=len(comparable),
                            feasible=sum(r["feasible"] for r in rows if r["tile_size"]==b),
                            lower_energy=sum(v<1 for v in comparable),
                            higher_energy=sum(v>1 for v in comparable),
                            min_ratio=min(comparable,default=None),
                            max_ratio=max(comparable,default=None)))
    report = dict(experiment="OPA-MOD-005", seed=SEED, n=N,
                  numpy_version=np.__version__, python_version=sys.version.split()[0],
                  checks=checks, failures=[k for k,v in checks.items() if not v],
                  scenarios=scenarios, summary=summary, results=rows,
                  limitations=[
                      "All energy, loss and receiver coefficients are hypothetical sensitivity inputs, not measured or literature-calibrated values.",
                      "Equal worst-vector expected relative RMS from independent receiver noise only; excludes static fabrication error, calibration residual, DAC quantization, clipping, drift and correlated noise. Not equal task accuracy.",
                      "Shot-noise coefficient and fixed LO cost are independent illustrative inputs; no physical receiver sensitivity or bandwidth validation. ADC rounding approximated as independent uniform noise.",
                      "Passive input fanout, spatially parallel SVD tiles, electronic gain and accumulation; intermodule transport counts partial output values only, no duplicate charging for passive optical fanout.",
                      "Control counts assume two phase controls per MZI plus output phase screens, one attenuator per channel; hypothetical setup cost includes programming and calibration, not a metrology protocol.",
                      "No external host, weight memory traffic, cooling model, scheduling or training. Fixed system power is a placeholder; no measured total system efficiency or GPU comparison.",
                  ])
    OUT.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(report,indent=2,allow_nan=False)+"\n"
    (OUT/"result.json").write_text(payload,encoding="utf-8")
    print(json.dumps(dict(checks=checks,summary=summary),indent=2))
    if report["failures"]:
        raise SystemExit("OPA-MOD-005 failed: "+", ".join(report["failures"]))


if __name__=="__main__":
    main()
