"""
params.py - Device, architecture, system, and baseline parameters for AG-PHOTONIC-003.
Every parameter includes explicit units, nominal value, uncertainty range (low, high),
and provenance (verifiable literature or explicit engineering assumption).
No invented citations.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Any

@dataclass(frozen=True)
class Param:
    val: float
    low: float
    high: float
    unit: str
    provenance: str

# Fundamental physical constants
H_PLANCK = 6.62607015e-34  # J*s
C_LIGHT = 2.99792458e8     # m/s
Q_E = 1.602176634e-19      # C
K_B = 1.380649e-23         # J/K
T_TEMP = 300.0             # K (nominal chip/ambient reference)
LAMBDA_0 = 1550e-9         # m (C-band center)
NU_0 = C_LIGHT / LAMBDA_0  # Hz (~193.4 THz)

# Optical & Comb Parameters
OPTICAL_PARAMS: Dict[str, Param] = {
    "laser_wpe": Param(0.20, 0.12, 0.30, "fraction", "Assumption grounded in typical InP DFB/pump laser WPE (12-30%)"),
    "laser_rin_db_hz": Param(-145.0, -135.0, -155.0, "dB/Hz", "Typical DFB/ECDL RIN (-135 to -155 dB/Hz)"),
    "laser_max_power_mw": Param(500.0, 200.0, 1000.0, "mW", "Max single-pump CW optical output (high-power InP/EDFA-pumped source)"),
    "comb_threshold_mw": Param(20.0, 10.0, 40.0, "mW", "Si3N4 microcomb parametric oscillation threshold (typical 10-40 mW)"),
    "comb_eff": Param(0.10, 0.04, 0.25, "fraction", "DKS / microcomb pump-to-usable-lines conversion efficiency"),
    "comb_bw_thz": Param(4.0, 2.5, 6.0, "THz", "Usable 3-dB/6-dB soliton comb optical bandwidth"),
    "comb_channel_spacing_ghz": Param(50.0, 25.0, 100.0, "GHz", "WDM grid spacing (50-100 GHz DWDM)"),
    "comb_nonunif_db_per_64": Param(6.0, 3.0, 10.0, "dB", "Spectral roll-off across 64 lines (sech^2 envelope)"),
    "pump_reject_il_db": Param(1.0, 0.5, 2.0, "dB", "Notch filter / bus drop loss for residual pump rejection"),
    "splitter_excess_db": Param(0.3, 0.1, 0.6, "dB/stage", "Excess loss per 1x2 MMI/Y-branch stage"),
    "coupler_il_db": Param(1.5, 0.8, 3.0, "dB", "Fiber/laser-to-chip coupling loss (edge/grating)"),
    "mux_demux_il_db": Param(2.0, 1.0, 3.5, "dB", "AWG / MRR WDM mux+demux insertion loss"),
    "wg_loss_db_cm": Param(0.5, 0.1, 1.5, "dB/cm", "SiN/Si waveguide propagation loss"),
    "mzi_il_db": Param(0.15, 0.05, 0.35, "dB/MZI", "Insertion loss per 2x2 MZI (2 couplers + phase shifter)"),
    "mrr_thru_il_db": Param(0.05, 0.02, 0.12, "dB/ring", "Through-port loss per off-resonance MRR"),
    "mrr_drop_il_db": Param(1.0, 0.5, 2.0, "dB/ring", "Drop/weight-port insertion loss for MRR"),
    "mod_il_db": Param(2.5, 1.5, 4.0, "dB", "High-speed input modulator insertion loss"),
    "pd_responsivity": Param(0.9, 0.7, 1.1, "A/W", "Ge/InGaAs waveguide photodiode responsivity at 1550 nm"),
    "tia_noise_pa_rt_hz": Param(15.0, 8.0, 30.0, "pA/sqrt(Hz)", "TIA input-referred current noise density"),
    "xtalk_penalty_db": Param(0.5, 0.2, 1.5, "dB", "Effective SNR penalty from WDM/thermal crosstalk"),
    "amp_wpe": Param(0.10, 0.05, 0.20, "fraction", "EDFA/SOA electrical-to-optical wall-plug efficiency"),
    "amp_nf_db": Param(6.0, 4.5, 8.0, "dB", "Optical amplifier noise figure"),
    "amp_max_gain_db": Param(25.0, 15.0, 30.0, "dB", "Max usable single-stage booster optical gain"),
    "amp_psat_mw": Param(250.0, 50.0, 500.0, "mW", "Optical amplifier saturation output power (24 dBm EDFA; 17 dBm SOA)"),
}

# Phase Shifter Technologies
# Keys: static_mw, sw_energy_pj, v_pi_v, il_db, settling_ns, area_um2, endurance_cycles, xtalk_factor, integ_feasibility
PHASE_TECHS: Dict[str, Dict[str, Any]] = {
    "thermo_optic": {
        "static_mw": Param(2.5, 0.8, 8.0, "mW", "TiN/doped-Si heater static power for pi shift"),
        "sw_energy_pj": Param(50000.0, 10000.0, 200000.0, "pJ", "Thermal time constant * static power (~20 us * 2.5 mW)"),
        "v_pi_v": Param(3.0, 1.5, 5.0, "V", "Typical heater drive voltage"),
        "il_db": Param(0.02, 0.01, 0.05, "dB", "Negligible optical loss for TO heater"),
        "settling_ns": Param(20000.0, 5000.0, 50000.0, "ns", "Thermal settling time (5-50 us)"),
        "area_um2": Param(5000.0, 2000.0, 15000.0, "um^2", "Heater + thermal isolation trench footprint"),
        "endurance_cycles": 1e15,
        "xtalk_factor": 0.15,
        "integ_feasibility": "high_cmos_foundry",
        "can_fast_modulate": False,
    },
    "carrier_depletion": {
        "static_mw": Param(0.01, 0.001, 0.05, "mW", "Reverse-biased PN junction leakage"),
        "sw_energy_pj": Param(2.0, 0.5, 5.0, "pJ", "CV^2 capacitive switching energy (~100-500 fF at 2-4V)"),
        "v_pi_v": Param(4.0, 2.0, 6.0, "V", "Reverse-bias V_pi"),
        "il_db": Param(0.6, 0.3, 1.2, "dB", "Free-carrier absorption loss (phase-dependent)"),
        "settling_ns": Param(0.05, 0.02, 0.2, "ns", "RC-limited GHz switching"),
        "area_um2": Param(40000.0, 15000.0, 80000.0, "um^2", "Long PN phase shifter (~1 mm x 40 um)"),
        "endurance_cycles": 1e15,
        "xtalk_factor": 0.02,
        "integ_feasibility": "high_si_photonics",
        "can_fast_modulate": True,
    },
    "pockels_tfln": {
        "static_mw": Param(0.001, 0.0001, 0.01, "mW", "Near-zero capacitive leakage"),
        "sw_energy_pj": Param(0.5, 0.1, 2.0, "pJ", "Low-capacitance Pockels electrode switching"),
        "v_pi_v": Param(2.5, 1.4, 5.0, "V", "TFLN / BTO V_pi"),
        "il_db": Param(0.05, 0.02, 0.15, "dB", "Low optical propagation loss in TFLN"),
        "settling_ns": Param(0.02, 0.01, 0.05, "ns", "Electro-optic >20 GHz response"),
        "area_um2": Param(60000.0, 20000.0, 150000.0, "um^2", "Traveling-wave / lumped Pockels length (1-3 mm)"),
        "endurance_cycles": 1e15,
        "xtalk_factor": 0.01,
        "integ_feasibility": "medium_heterogeneous",
        "can_fast_modulate": True,
    },
    "nonvolatile_pcm": {
        "static_mw": Param(0.0, 0.0, 0.001, "mW", "Zero static hold power (nonvolatile GSST/GST)"),
        "sw_energy_pj": Param(500.0, 100.0, 2000.0, "pJ", "Amorphization/crystallization pulse energy"),
        "v_pi_v": Param(3.0, 1.5, 5.0, "V", "Microheater/PIN programming pulse"),
        "il_db": Param(0.35, 0.15, 0.8, "dB", "State-dependent absorption loss (GSST)"),
        "settling_ns": Param(500.0, 100.0, 2000.0, "ns", "Crystallization pulse/settling time"),
        "area_um2": Param(1000.0, 400.0, 3000.0, "um^2", "Compact PCM cell"),
        "endurance_cycles": 1e7, # Critical training bottleneck!
        "xtalk_factor": 0.03,
        "integ_feasibility": "low_to_medium_specialty",
        "can_fast_modulate": False,
    },
    "hybrid_pcm_pockels": {
        "static_mw": Param(0.002, 0.0005, 0.01, "mW", "PCM bias + Pockels trim/fast update"),
        "sw_energy_pj": Param(1.0, 0.3, 3.0, "pJ", "Fast Pockels delta updates; PCM rare coarse set"),
        "v_pi_v": Param(2.5, 1.5, 4.5, "V", "Pockels fine + PCM coarse"),
        "il_db": Param(0.20, 0.08, 0.45, "dB", "Combined PCM + Pockels loss"),
        "settling_ns": Param(0.05, 0.02, 0.2, "ns", "Fast Pockels response for fine updates"),
        "area_um2": Param(65000.0, 25000.0, 155000.0, "um^2", "Pockels + PCM cell footprint"),
        "endurance_cycles": 1e14, # Pockels handles frequent updates
        "xtalk_factor": 0.02,
        "integ_feasibility": "low_research_stage",
        "can_fast_modulate": True,
    }
}

# Electronic & System Parameters
SYSTEM_PARAMS: Dict[str, Param] = {
    "f_mod_ghz": Param(10.0, 5.0, 25.0, "GHz", "Optical data modulation / symbol rate"),
    "dac_pj_per_conv_8b": Param(1.5, 0.5, 4.0, "pJ", "High-speed DAC energy at 8-bit, 10 GS/s (scales ~2^(B-8) or B*2^(B/4))"),
    "adc_pj_per_conv_8b": Param(2.5, 1.0, 6.0, "pJ", "High-speed ADC energy at 8-bit, 10 GS/s"),
    "tia_mw_per_ch": Param(5.0, 2.0, 12.0, "mW", "TIA + limiting/linear front-end power per detector channel"),
    "mod_driver_pj_per_sym": Param(1.0, 0.4, 3.0, "pJ", "High-speed modulator driver energy per symbol"),
    "sram_pj_per_byte": Param(0.5, 0.2, 1.0, "pJ/byte", "On-chip SRAM access energy"),
    "hbm_pj_per_byte": Param(4.0, 2.5, 8.0, "pJ/byte", "Off-chip HBM/DRAM access energy"),
    "elec_mac_pj": Param(0.30, 0.15, 0.60, "pJ/MAC", "Digital 5nm/4nm systolic MAC energy (8-bit/BF16 mixed)"),
    "calib_mw_per_ring_or_mzi": Param(0.05, 0.01, 0.15, "mW", "Dithering/lock-in thermal stabilization & control overhead"),
    "comb_stabilization_mw": Param(100.0, 30.0, 250.0, "mW", "TEC + RF lock-in + heater stabilization per microcomb"),
    "pue_cooling_factor": Param(1.15, 1.08, 1.30, "multiplier", "System cooling / PSU / PUE overhead multiplier"),
    "reticle_limit_mm2": Param(858.0, 858.0, 858.0, "mm^2", "Standard EUV/DUV reticle area limit per die"),
    "electronic_baseline_topsw": Param(3.5, 2.0, 6.0, "TOPS/W", "Matched-boundary modern GPU/TPU-class training system efficiency (2 OPs/MAC, incl. HBM+cooling)"),
    "electronic_baseline_tops": Param(1000.0, 500.0, 2000.0, "TOPS", "Reference electronic accelerator sustained training TOPS"),
}

# Standard Training Workload Definition
WORKLOAD = {
    "name": "Transformer/MLP_Block_1024x1024",
    "layer_dim": 1024,
    "batch_size": 128,
    "num_layers": 12,
    "training_steps": 10000,
    "min_throughput_tops": 10.0,      # Explicit minimum sustained throughput constraint
    "max_step_latency_ms": 50.0,      # Explicit max step latency constraint
    "target_val_acc": 0.90,           # Common validation target for NN convergence check
}
