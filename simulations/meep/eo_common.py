"""Shared solvers for the electro-optic experiments (OPA-EO-002 onwards).

The functions are the ones that OPA-EO-001 (eo_vs_thermal_v001.py) defines
inline, generalised to other gaps and film materials. eo_vs_thermal_v001.py is
left as it was run.

    axis, fv_solve, cell_gradient, lookup    2D finite-volume solver for
                                             div(c grad u) + s = 0
    Mode, film_mode                          MPB TE mode of a rib in a thin film
    electrostatics, eo_dneff_per_volt        electrode field and Pockels d n_eff
    sv_te_mode                               semi-vectorial (E_y) finite-difference
                                             mode solver with complex permittivity,
                                             for the absorption of the electrodes
"""
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import meep as mp
from meep import mpb

WL = 1.55                       # um
EPS0 = 8.8541878128e-12         # F/m
N_SIO2 = 1.444
EPS_DC = {"air": 1.0, "sio2": 3.9, "si": 11.7}

# Film geometry of OPA-EO-001 (um); z = 0 at the bottom of the film
FILM, ETCH, RIB_W = 0.60, 0.30, 1.20
SLAB = FILM - ETCH
ELECTRODE_W, ELECTRODE_T = 10.0, 0.80
BOX = 4.7


class Film:
    """Electro-optic film: optical indices (o, e along y), DC permittivity, r."""

    def __init__(self, name, n_o, n_e, eps_dc_y, eps_dc_z, r):
        self.name, self.n_o, self.n_e = name, n_o, n_e
        self.eps_dc_y, self.eps_dc_z, self.r = eps_dc_y, eps_dc_z, r


LN = Film("X-cut LiNbO3", 2.2111, 2.1376, 28.0, 44.0, 30.9e-12)


# ----------------------------------------------------------------------------
# 2D finite-volume solver
# ----------------------------------------------------------------------------
def axis(breaks, fine_lo, fine_hi, h_fine, growth=1.2, h_max=None):
    """Grid nodes that contain every breakpoint: spacing h_fine inside
    [fine_lo, fine_hi], growing in proportion to the distance outside it."""
    breaks = sorted(set(round(b, 9) for b in breaks))
    nodes = [breaks[0]]
    for a, b in zip(breaks, breaks[1:]):
        x = a
        while x < b:
            dist = max(fine_lo - x, x - fine_hi, 0.0)
            h = h_fine + dist * (growth - 1)
            if h_max:
                h = min(h, h_max)
            x = b if x + 1.3 * h >= b else x + h
            nodes.append(x)
    return np.array(nodes)


def fv_solve(y, z, cy, cz, fixed, values, source=None):
    """Solve on nodes (y, z). cy, cz, source: per cell, shape (ny-1, nz-1).
    fixed, values: per node (Dirichlet). Other boundaries are Neumann."""
    ny, nz = len(y), len(z)
    dy, dz = np.diff(y), np.diff(z)
    idx = np.arange(ny * nz).reshape(ny, nz)
    rows, cols, vals = [], [], []
    rhs = np.zeros(ny * nz)
    cyp = np.pad(cy, ((0, 0), (1, 1)))
    dzp = np.pad(dz, 1)
    gy = (cyp[:, :-1] * dzp[None, :-1] / 2 + cyp[:, 1:] * dzp[None, 1:] / 2) / dy[:, None]
    czp = np.pad(cz, ((1, 1), (0, 0)))
    dyp = np.pad(dy, 1)
    gz = (czp[:-1, :] * dyp[:-1, None] / 2 + czp[1:, :] * dyp[1:, None] / 2) / dz[None, :]

    def couple(a, b, g):
        a, b, g = a.ravel(), b.ravel(), g.ravel()
        rows.extend([a, b, a, b])
        cols.extend([a, b, b, a])
        vals.extend([g, g, -g, -g])

    couple(idx[:-1, :], idx[1:, :], gy)
    couple(idx[:, :-1], idx[:, 1:], gz)
    if source is not None:
        q = source * dy[:, None] * dz[None, :] / 4
        for di in (0, 1):
            for dj in (0, 1):
                np.add.at(rhs, idx[di:ny - 1 + di, dj:nz - 1 + dj].ravel(), q.ravel())
    a = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(ny * nz, ny * nz))
    fixed = fixed.ravel()
    free = ~fixed
    u = np.zeros(ny * nz)
    u[fixed] = values.ravel()[fixed]
    rhs = rhs - a @ u
    u[free] = spla.spsolve(a[free][:, free].tocsc(), rhs[free])
    return u.reshape(ny, nz)


def cell_gradient(y, z, u):
    """-grad u at cell centres."""
    dy, dz = np.diff(y), np.diff(z)
    ey = -((u[1:, :-1] - u[:-1, :-1]) + (u[1:, 1:] - u[:-1, 1:])) / (2 * dy[:, None])
    ez = -((u[:-1, 1:] - u[:-1, :-1]) + (u[1:, 1:] - u[1:, :-1])) / (2 * dz[None, :])
    return ey, ez


def cell_centres(y, z):
    return (y[:-1] + y[1:]) / 2, (z[:-1] + z[1:]) / 2


def lookup(y, z, field, py, pz):
    """Piecewise-constant value of a per-cell field at points (py, pz)."""
    i = np.clip(np.searchsorted(y, py) - 1, 0, len(y) - 2)
    j = np.clip(np.searchsorted(z, pz) - 1, 0, len(z) - 2)
    return field[i, j]


# ----------------------------------------------------------------------------
# MPB TE mode of the rib
# ----------------------------------------------------------------------------
class Mode:
    def __init__(self, geometry, default, size, centre, res):
        self.size, self.centre, self.res = size, centre, res
        self.ms = mpb.ModeSolver(geometry_lattice=mp.Lattice(size=mp.Vector3(0, *size)),
                                 geometry=geometry, default_material=default,
                                 resolution=res, num_bands=1)
        self.ms.verbose = False

    def solve(self):
        ms, f = self.ms, 1 / WL
        k = ms.find_k(mp.ODD_Y, f, 1, 1, mp.Vector3(1), 1e-10, f * 2.0, f * 1.0, f * 4.0)[0]
        ms.k_points = [mp.Vector3(k)]
        ms.run_parity(mp.ODD_Y, True)
        e = np.asarray(ms.get_efield(1, bloch_phase=False))
        vg = ms.compute_group_velocity_component(mp.Vector3(1))[0]
        self.neff, self.ng = k / f, 1 / vg
        ny, nz = round(self.size[0] * self.res), round(self.size[1] * self.res)
        self.e = e.reshape(ny, nz, 3)
        # MPB grid: point i at -size/2 + i * size / n (origin at the cell centre)
        self.py = (np.arange(ny) / ny - 0.5) * self.size[0] + self.centre[0]
        self.pz = (np.arange(nz) / nz - 0.5) * self.size[1] + self.centre[1]
        self.eps_mpb = np.asarray(ms.get_epsilon()).reshape(ny, nz)
        return self

    def te_fraction(self):
        p = np.abs(self.e) ** 2
        return float(p[..., 1].sum() / p.sum())

    def dneff(self, deps_diag, eps_diag):
        """First-order d n_eff for a diagonal permittivity change (x, y, z)."""
        p = np.abs(self.e) ** 2
        num = sum(np.sum(deps_diag[c] * p[..., c]) for c in range(3))
        den = sum(np.sum(eps_diag[c] * p[..., c]) for c in range(3))
        return self.ng * 0.5 * num / den


def film_masks(py, pz):
    Y, Z = np.meshgrid(py, pz, indexing="ij")
    film = ((Z >= 0) & (Z < SLAB)) | ((Z >= SLAB) & (Z < FILM) & (np.abs(Y) < RIB_W / 2))
    return film, Z < 0


def film_mode(film, res, eps_y=None):
    """TE mode of the rib in `film` (optical axis e along y), SiO2 below, air above."""
    size, centre = (10.0, 4.5), (0.0, 0.25)
    off = mp.Vector3(0, -centre[0], -centre[1])
    eps_y = film.n_e ** 2 if eps_y is None else eps_y
    mat = mp.Medium(epsilon_diag=mp.Vector3(film.n_o ** 2, eps_y, film.n_o ** 2))
    z_bottom = centre[1] - size[1] / 2
    geometry = [
        mp.Block(center=mp.Vector3(0, 0, z_bottom / 2) + off,
                 size=mp.Vector3(mp.inf, mp.inf, -z_bottom), material=mp.Medium(index=N_SIO2)),
        mp.Block(center=mp.Vector3(0, 0, SLAB / 2) + off, size=mp.Vector3(mp.inf, mp.inf, SLAB),
                 material=mat),
        mp.Block(center=mp.Vector3(0, 0, SLAB + ETCH / 2) + off,
                 size=mp.Vector3(mp.inf, RIB_W, ETCH), material=mat),
    ]
    mode = Mode(geometry, mp.Medium(index=1.0), size, centre, res).solve()
    fm, ox = film_masks(mode.py, mode.pz)
    bg = np.where(ox, N_SIO2 ** 2, 1.0)
    mode.eps_diag = [np.where(fm, film.n_o ** 2, bg), np.where(fm, film.n_e ** 2, bg),
                     np.where(fm, film.n_o ** 2, bg)]
    mode.film, mode.agreement = fm, float(np.mean((mode.eps_mpb > 3.5) == fm))
    return mode


# ----------------------------------------------------------------------------
# Electrostatics and the Pockels change of n_eff
# ----------------------------------------------------------------------------
def electrostatics(film, gap, h_fine):
    e_in, e_out = gap / 2, gap / 2 + ELECTRODE_W
    ybreaks = [-40, -e_out, -e_in, -RIB_W / 2, 0, RIB_W / 2, e_in, e_out, 40]
    zbreaks = [-BOX - 20, -BOX, 0, SLAB, FILM, SLAB + ELECTRODE_T, 25]
    y = axis(ybreaks, -e_in - 0.5, e_in + 0.5, h_fine, h_max=2.0)
    z = axis(zbreaks, -0.5, SLAB + ELECTRODE_T + 0.3, h_fine, h_max=2.0)
    yc, zc = cell_centres(y, z)
    Y, Z = np.meshgrid(yc, zc, indexing="ij")
    fm = ((Z > 0) & (Z < SLAB)) | ((Z > SLAB) & (Z < FILM) & (np.abs(Y) < RIB_W / 2))
    box, sub = (Z < 0) & (Z > -BOX), Z < -BOX
    bg = np.where(box, EPS_DC["sio2"], np.where(sub, EPS_DC["si"], 1.0))
    ey_c, ez_c = np.where(fm, film.eps_dc_y, bg), np.where(fm, film.eps_dc_z, bg)
    YN, ZN = np.meshgrid(y, z, indexing="ij")
    in_z = (ZN >= SLAB - 1e-9) & (ZN <= SLAB + ELECTRODE_T + 1e-9)
    left = in_z & (YN <= -e_in + 1e-9) & (YN >= -e_out - 1e-9)
    right = in_z & (YN >= e_in - 1e-9) & (YN <= e_out + 1e-9)
    u = fv_solve(y, z, ey_c, ez_c, left | right, np.where(right, 1.0, 0.0))
    ey, ez = cell_gradient(y, z, u)
    ey, ez = ey * 1e6, ez * 1e6                                   # V/m for 1 V
    inside = (Z > SLAB) & (Z < SLAB + ELECTRODE_T) & (np.abs(Y) > e_in) & (np.abs(Y) < e_out)
    ey[inside] = ez[inside] = 0.0
    area = np.diff(y)[:, None] * np.diff(z)[None, :] * 1e-12
    cap = EPS0 * np.sum((ey_c * ey ** 2 + ez_c * ez ** 2) * area)  # F/m
    return {"y": y, "z": z, "ey": ey, "cap": cap, "nodes": len(y) * len(z)}


def eo_dneff_per_volt(mode, es, film):
    ey = lookup(es["y"], es["z"], es["ey"], *np.meshgrid(mode.py, mode.pz, indexing="ij"))
    deps_y = np.where(mode.film, -film.n_e ** 4 * film.r * ey, 0.0)
    zero = np.zeros_like(deps_y)
    return abs(mode.dneff([zero, deps_y, zero], mode.eps_diag))


# ----------------------------------------------------------------------------
# Semi-vectorial E_y mode solver with complex permittivity
# ----------------------------------------------------------------------------
def sv_te_mode(eps, h, n_guess, wl=WL, k=4, select=None):
    """Quasi-TE (E_y) modes of eps (complex, nodes on a uniform grid of step h).

        d/dy[(1/eps) d(eps E)/dy] + d2E/dz2 + k0^2 eps E = beta^2 E

    with eps at half nodes taken as the mean of its neighbours and E = 0
    outside the grid. Returns (n_eff, field) of the eigenvector, among the k
    closest to n_guess, that `select(field)` scores highest (default: first).
    """
    ny, nz = eps.shape
    k0 = 2 * math.pi / wl
    idx = np.arange(ny * nz).reshape(ny, nz)
    rows, cols, vals = [], [], []
    diag = k0 ** 2 * eps.astype(complex) - 2 / h ** 2       # z part of the centre term
    e_half = (eps[1:, :] + eps[:-1, :]) / 2                  # between i and i+1
    centre = np.zeros_like(diag)
    centre[:-1, :] -= eps[:-1, :] / e_half / h ** 2
    centre[1:, :] -= eps[1:, :] / e_half / h ** 2
    diag = diag + centre
    rows.append(idx.ravel()); cols.append(idx.ravel()); vals.append(diag.ravel())
    # y neighbours
    rows.append(idx[:-1, :].ravel()); cols.append(idx[1:, :].ravel())
    vals.append((eps[1:, :] / e_half / h ** 2).ravel())
    rows.append(idx[1:, :].ravel()); cols.append(idx[:-1, :].ravel())
    vals.append((eps[:-1, :] / e_half / h ** 2).ravel())
    # z neighbours
    for a, b in ((idx[:, :-1], idx[:, 1:]), (idx[:, 1:], idx[:, :-1])):
        rows.append(a.ravel()); cols.append(b.ravel())
        vals.append(np.full(a.size, 1 / h ** 2, complex))
    a = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(ny * nz, ny * nz))
    w, v = spla.eigs(a, k=k, sigma=(k0 * n_guess) ** 2)
    best, score = None, -1
    for i in range(len(w)):
        field = v[:, i].reshape(ny, nz)
        s = select(field) if select else -i
        if s > score:
            best, score = i, s
    return np.sqrt(w[best]) / k0, v[:, best].reshape(ny, nz)


def loss_db_per_cm(neff, wl=WL):
    """Power loss from Im(n_eff): 10 log10(e) * 2 k0 Im(n)."""
    return 10 / math.log(10) * 2 * (2 * math.pi / (wl * 1e-4)) * abs(neff.imag)
