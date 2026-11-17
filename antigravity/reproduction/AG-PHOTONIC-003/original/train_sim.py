"""
train_sim.py - Seeded neural network training comparing digital FP32 baseline
against photonic-inspired models (4/6/8-bit + circuit noise/drift) across 3 seeds.
Measures forward error, gradient error, training curves, validation accuracy,
and convergence status (including explicit failed-convergence detection).
"""

import time
import numpy as np
from typing import Dict, Any, List, Tuple


def make_dataset(seed: int, n_train: int = 3000, n_val: int = 600, d_in: int = 8, n_classes: int = 6):
    rng = np.random.default_rng(seed)
    # Well-posed nonlinear teacher network (8 -> 16 -> 6)
    W_t1 = rng.normal(0, np.sqrt(2.0 / d_in), size=(d_in, 16))
    W_t2 = rng.normal(0, np.sqrt(2.0 / 16), size=(16, n_classes))

    def sample(n):
        x = rng.normal(0, 1.0, size=(n, d_in))
        h = np.maximum(0.0, x @ W_t1)
        logits_true = h @ W_t2
        y = np.argmax(logits_true + rng.normal(0, 0.01, size=logits_true.shape), axis=1)
        return x.astype(np.float32), y

    x_tr, y_tr = sample(n_train)
    x_va, y_va = sample(n_val)
    return x_tr, y_tr, x_va, y_va


def quantize_tensor(x: np.ndarray, bits: int) -> np.ndarray:
    if bits >= 32:
        return x
    max_abs = np.max(np.abs(x))
    if max_abs < 1e-12:
        return x
    q_levels = (2 ** (bits - 1)) - 1
    scale = max_abs / q_levels
    return np.round(x / scale) * scale


def photonic_matmul(
    A: np.ndarray,
    B: np.ndarray,
    bits: int,
    rel_noise_std: float,
    drift_bias: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Simulate photonic matrix multiply A @ B with finite DAC/ADC precision,
    multiplicative/additive circuit noise, and slow thermal drift bias.
    """
    if bits >= 32 and rel_noise_std == 0.0 and drift_bias == 0.0:
        return A @ B
    Aq = quantize_tensor(A, bits)
    Bq = quantize_tensor(B, bits)
    Y = Aq @ Bq
    if rel_noise_std > 0.0 or drift_bias != 0.0:
        rms = float(np.sqrt(np.mean(Y ** 2))) + 1e-12
        noise = rng.normal(drift_bias * rms, rel_noise_std * rms, size=Y.shape)
        Y = Y + noise
    return quantize_tensor(Y, bits)


def train_one_run(
    seed: int,
    bits: int,
    rel_noise_std: float,
    drift_bias: float,
    photonic_wgrad: bool = False,
    epochs: int = 120,
    batch_size: int = 64,
    lr: float = 0.008,
    target_val_acc: float = 0.90,
) -> Dict[str, Any]:
    x_tr, y_tr, x_va, y_va = make_dataset(seed)
    rng = np.random.default_rng(seed + 999)
    n_train, d_in = x_tr.shape
    d_hid = 128
    n_classes = 6

    # Xavier init
    W1 = (rng.normal(0, np.sqrt(2.0 / d_in), size=(d_in, d_hid))).astype(np.float64)
    b1 = np.zeros(d_hid, dtype=np.float64)
    W2 = (rng.normal(0, np.sqrt(2.0 / d_hid), size=(d_hid, n_classes))).astype(np.float64)
    b2 = np.zeros(n_classes, dtype=np.float64)

    # Adam state
    m = {k: np.zeros_like(v) for k, v in [("W1", W1), ("b1", b1), ("W2", W2), ("b2", b2)]}
    v = {k: np.zeros_like(v) for k, v in [("W1", W1), ("b1", b1), ("W2", W2), ("b2", b2)]}
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    step_idx = 0

    loss_curve = []
    val_acc_curve = []
    fwd_errs = []
    grad_errs = []
    epoch_to_target = None

    for ep in range(1, epochs + 1):
        perm = rng.permutation(n_train)
        ep_loss = 0.0
        n_batches = 0

        for start in range(0, n_train, batch_size):
            idx = perm[start:start + batch_size]
            xb = x_tr[idx]
            yb = y_tr[idx]
            bs = len(idx)

            # Forward (photonic)
            z1_exact = xb @ W1 + b1
            z1 = photonic_matmul(xb, W1, bits, rel_noise_std, drift_bias, rng) + b1
            h1 = np.maximum(0.0, z1)
            logits = photonic_matmul(h1, W2, bits, rel_noise_std, drift_bias, rng) + b2

            if ep in (1, epochs // 2, epochs) and start == 0:
                fwd_errs.append(float(np.linalg.norm(z1 - z1_exact) / (np.linalg.norm(z1_exact) + 1e-12)))

            # Softmax + Cross-entropy
            logits_shift = logits - np.max(logits, axis=1, keepdims=True)
            exp_l = np.exp(np.clip(logits_shift, -30, 30))
            probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
            loss = -np.mean(np.log(np.clip(probs[np.arange(bs), yb], 1e-12, 1.0)))
            ep_loss += float(loss)
            n_batches += 1

            # Backward
            dlogits = probs.copy()
            dlogits[np.arange(bs), yb] -= 1.0
            dlogits /= bs

            # Exact reference gradient for error tracking
            dW1_exact = xb.T @ ((dlogits @ W2.T) * (z1_exact > 0))

            if photonic_wgrad:
                dW2 = photonic_matmul(h1.T, dlogits, bits, rel_noise_std, drift_bias, rng)
                dh1 = photonic_matmul(dlogits, W2.T, bits, rel_noise_std, drift_bias, rng)
                dz1 = dh1 * (z1 > 0)
                dW1 = photonic_matmul(xb.T, dz1, bits, rel_noise_std, drift_bias, rng)
            else:
                # Hybrid: backward activation grad photonic, weight grad electronic FP32
                dh1 = photonic_matmul(dlogits, W2.T, bits, rel_noise_std, drift_bias, rng)
                dz1 = dh1 * (z1 > 0)
                dW2 = h1.T @ dlogits
                dW1 = xb.T @ dz1

            db2 = np.sum(dlogits, axis=0)
            db1 = np.sum(dz1, axis=0)

            if ep in (1, epochs // 2, epochs) and start == 0:
                grad_errs.append(float(np.linalg.norm(dW1 - dW1_exact) / (np.linalg.norm(dW1_exact) + 1e-12)))

            # Adam update
            step_idx += 1
            for name, param, grad in [("W1", W1, dW1), ("b1", b1, db1), ("W2", W2, dW2), ("b2", b2, db2)]:
                m[name] = beta1 * m[name] + (1.0 - beta1) * grad
                v[name] = beta2 * v[name] + (1.0 - beta2) * (grad ** 2)
                m_hat = m[name] / (1.0 - beta1 ** step_idx)
                v_hat = v[name] / (1.0 - beta2 ** step_idx)
                param -= lr * m_hat / (np.sqrt(v_hat) + eps)

        # Validation
        z1_v = photonic_matmul(x_va, W1, bits, rel_noise_std, drift_bias, rng) + b1
        h1_v = np.maximum(0.0, z1_v)
        logits_v = photonic_matmul(h1_v, W2, bits, rel_noise_std, drift_bias, rng) + b2
        val_acc = float(np.mean(np.argmax(logits_v, axis=1) == y_va))

        if epoch_to_target is None and val_acc >= target_val_acc:
            epoch_to_target = ep

        if ep % 20 == 0 or ep == 1 or ep == epochs:
            loss_curve.append({"epoch": ep, "train_loss": round(ep_loss / n_batches, 4), "val_acc": round(val_acc, 4)})
            val_acc_curve.append(val_acc)

    return {
        "seed": seed,
        "final_val_acc": round(val_acc, 4),
        "final_train_loss": round(ep_loss / n_batches, 4),
        "converged": val_acc >= target_val_acc,
        "epoch_to_target": epoch_to_target,
        "mean_fwd_rel_err": round(float(np.mean(fwd_errs)), 4),
        "mean_grad_rel_err": round(float(np.mean(grad_errs)), 4),
        "curve_sampled": loss_curve,
    }


def run_nn_training_suite(seeds: List[int] = [42, 137, 2025]) -> Dict[str, Any]:
    t0 = time.time()
    configs = [
        {"name": "digital_fp32_baseline", "bits": 32, "noise": 0.0, "drift": 0.0, "pwg": False},
        {"name": "photonic_8b_hybrid_wgrad", "bits": 8, "noise": 0.03, "drift": 0.005, "pwg": False},
        {"name": "photonic_6b_hybrid_wgrad", "bits": 6, "noise": 0.05, "drift": 0.01, "pwg": False},
        {"name": "photonic_4b_hybrid_wgrad", "bits": 4, "noise": 0.12, "drift": 0.02, "pwg": False},
        {"name": "photonic_4b_all_photonic", "bits": 4, "noise": 0.12, "drift": 0.02, "pwg": True},
        {"name": "photonic_high_drift_fail", "bits": 6, "noise": 0.45, "drift": 0.15, "pwg": False},
    ]

    results = {}
    for cfg in configs:
        runs = [train_one_run(s, cfg["bits"], cfg["noise"], cfg["drift"], cfg["pwg"]) for s in seeds]
        mean_acc = float(np.mean([r["final_val_acc"] for r in runs]))
        std_acc = float(np.std([r["final_val_acc"] for r in runs]))
        conv_rate = sum(1 for r in runs if r["converged"]) / len(runs)
        epochs_list = [r["epoch_to_target"] for r in runs if r["epoch_to_target"] is not None]
        results[cfg["name"]] = {
            "bits": cfg["bits"],
            "rel_noise_std": cfg["noise"],
            "drift_bias": cfg["drift"],
            "photonic_wgrad": cfg["pwg"],
            "mean_final_val_acc": round(mean_acc, 4),
            "std_final_val_acc": round(std_acc, 4),
            "convergence_rate": conv_rate,
            "converged_all_seeds": conv_rate == 1.0,
            "mean_epochs_to_90pct": round(float(np.mean(epochs_list)), 1) if epochs_list else None,
            "mean_fwd_rel_err": round(float(np.mean([r["mean_fwd_rel_err"] for r in runs])), 4),
            "mean_grad_rel_err": round(float(np.mean([r["mean_grad_rel_err"] for r in runs])), 4),
            "per_seed": runs,
        }

    return {
        "runtime_s": round(time.time() - t0, 3),
        "seeds": seeds,
        "target_val_acc": 0.90,
        "models": results,
    }


if __name__ == "__main__":
    import json
    out = run_nn_training_suite()
    for name, m in out["models"].items():
        print(f"{name:26s}: acc={m['mean_final_val_acc']:.4f}+/-{m['std_final_val_acc']:.4f}, conv={m['converged_all_seeds']}, ep90={m['mean_epochs_to_90pct']}, fwd_err={m['mean_fwd_rel_err']}, grad_err={m['mean_grad_rel_err']}")
