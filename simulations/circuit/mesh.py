"""Rectangular (Clements) MZI meshes and SVD layers for optical matrix multiplication.

A mesh is a list of MZIs in the order light meets them. Each entry is
(m, theta, phi): an MZI acting on waveguides m and m+1, with the same
convention as mzi.mzi (external phase phi on waveguide m). After the last MZI
an output phase screen applies exp(1j*out_phases[k]) to waveguide k.

clements_decompose follows W. R. Clements et al., "Optimal design for
universal multiport interferometers", Optica 3, 1460 (2016): N(N-1)/2 MZIs in
N columns, so every path through the mesh crosses the same number of MZIs.

A general (non-unitary) weight matrix W is realized with its singular value
decomposition W = U diag(s) V^dagger: one mesh for V^dagger, a column of
attenuators for s / max(s), and one mesh for U. The overall scale max(s) is
applied electronically after detection.
"""
import numpy as np

from mzi import mzi, mzi_hw, program_unitary


def embed(block, m, n):
    """N x N identity with a 2x2 block on waveguides m, m+1."""
    full = np.eye(n, dtype=complex)
    full[m:m + 2, m:m + 2] = block
    return full


def _null_right(u, row, col):
    """MZI on columns (col, col+1) whose inverse, applied on the right, zeroes u[row, col]."""
    x0, x1 = u[row, col], u[row, col + 1]
    norm = np.hypot(abs(x0), abs(x1))
    if norm == 0:
        return 0.0, 0.0
    v = np.array([[x1, np.conj(x0)], [-x0, np.conj(x1)]]) / norm   # (x v)[0] = 0
    theta, phi, _, _ = program_unitary(v.conj().T)                  # v^dagger = D * mzi
    return theta, phi


def _null_left(u, row, col):
    """MZI on rows (row-1, row), applied on the left, that zeroes u[row, col]."""
    y0, y1 = u[row - 1, col], u[row, col]
    norm = np.hypot(abs(y0), abs(y1))
    if norm == 0:
        return 0.0, 0.0
    w = np.array([[np.conj(y0), np.conj(y1)], [y1, -y0]]) / norm    # (w y)[1] = 0
    theta, phi, _, _ = program_unitary(w)                           # w = D * mzi
    return theta, phi


def clements_decompose(u):
    """Decompose an N x N unitary into a rectangular mesh and output phases.

    Returns (ops, out_phases) with ops in light order, such that
    mesh_matrix(ops, out_phases) == u.
    """
    u = np.array(u, dtype=complex)
    n = u.shape[0]
    right, left = [], []          # right: T^-1 applied on the right; left: T on the left
    for i in range(n - 1):
        if i % 2 == 0:
            for j in range(i + 1):
                row, col = n - 1 - j, i - j
                theta, phi = _null_right(u, row, col)
                u = u @ embed(mzi(theta, phi), col, n).conj().T
                right.append((col, theta, phi))
        else:
            for j in range(1, i + 2):
                row, col = n + j - i - 2, j - 1
                theta, phi = _null_left(u, row, col)
                u = embed(mzi(theta, phi), row - 1, n) @ u
                left.append((row - 1, theta, phi))
    # Now L u R = D with L = T_k...T_1 (left), R = T_1^-1...T_j^-1 (right).
    # u_original = L^-1 D R^-1. Move D through L^-1 = T_1^-1 ... T_k^-1 from the
    # right: T^-1 D = D' T' on each 2x2 block, using program_unitary.
    d = np.diag(u).copy()
    moved = []
    for m, theta, phi in reversed(left):
        block = mzi(theta, phi).conj().T @ np.diag(d[m:m + 2])
        t2, p2, a, b = program_unitary(block)
        d[m], d[m + 1] = np.exp(1j * a), np.exp(1j * b)
        moved.append((m, t2, p2))
    # u_original = D_final * T'_1 ... T'_k * R^-1 with R^-1 = T_j ... T_1. The
    # rightmost factor acts first, so light meets the right-nulling MZIs in the
    # order they were created, then T'_k, ..., T'_1, which is the order in
    # which they were appended to `moved`.
    ops = right + moved
    return ops, np.angle(d)


def mesh_matrix(ops, out_phases, n=None, hw=None):
    """Transfer matrix of a mesh; hw is an optional list of per-MZI hardware dicts."""
    n = n or len(out_phases)
    total = np.eye(n, dtype=complex)
    for k, (m, theta, phi) in enumerate(ops):
        block = mzi(theta, phi) if hw is None else mzi_hw(theta, phi, hw[k])
        total = embed(block, m, n) @ total
    return np.diag(np.exp(1j * np.asarray(out_phases))) @ total


def mesh_columns(ops, n):
    """Assign each MZI to the earliest column where its waveguides are free."""
    free = [0] * n
    columns = []
    for m, _, _ in ops:
        c = max(free[m], free[m + 1])
        columns.append(c)
        free[m] = free[m + 1] = c + 1
    return columns


def flatten(ops, out_phases):
    """All phase settings as one vector: theta, phi per MZI, then output phases."""
    return np.concatenate([np.array([[t, p] for _, t, p in ops]).ravel(),
                           np.asarray(out_phases, dtype=float)])


def unflatten(x, ops):
    k = len(ops)
    pairs = np.asarray(x[:2 * k]).reshape(k, 2)
    return [(m, float(t), float(p)) for (m, _, _), (t, p) in zip(ops, pairs)], np.asarray(x[2 * k:])


def calibrate_mesh(target, ops, out_phases, hw):
    """Global calibration: re-optimize every phase of a mesh on known hardware.

    Starts from the ideal settings and minimizes the shape error (common gain
    removed) with least squares over all 2*K + N phases.
    """
    from scipy.optimize import least_squares

    target = np.asarray(target, dtype=complex)

    def residual(x):
        o, ph = unflatten(x, ops)
        m = mesh_matrix(o, ph, hw=hw)
        gain = np.vdot(m, target).real / np.vdot(m, m).real
        d = (gain * m - target).ravel()
        return np.concatenate([d.real, d.imag])

    fit = least_squares(residual, flatten(ops, out_phases), method="lm",
                        xtol=1e-14, ftol=1e-14, gtol=1e-14)
    return unflatten(fit.x, ops)


def svd_layer(w):
    """Program a real or complex N x N weight matrix as mesh - attenuators - mesh.

    Returns a dict with both meshes, the attenuator amplitudes (0..1) and the
    electronic scale, such that layer_matrix(layer) == w.
    """
    u, s, vh = np.linalg.svd(np.asarray(w, dtype=complex))
    scale = float(s.max())
    return {
        "in_mesh": clements_decompose(vh),
        "attenuation": s / scale,
        "out_mesh": clements_decompose(u),
        "scale": scale,
    }


def layer_matrix(layer, hw_in=None, hw_out=None):
    """Transfer matrix of an SVD layer including the electronic scale."""
    n = len(layer["attenuation"])
    v = mesh_matrix(*layer["in_mesh"], n=n, hw=hw_in)
    u = mesh_matrix(*layer["out_mesh"], n=n, hw=hw_out)
    return layer["scale"] * u @ np.diag(layer["attenuation"]) @ v
