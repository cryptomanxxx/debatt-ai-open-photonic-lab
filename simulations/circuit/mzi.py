"""Circuit-level (transfer-matrix) model of Mach-Zehnder interferometers.

Each optical component acts on the complex field amplitudes in two
waveguides as a 2x2 matrix. Light enters as a column vector [a_top, a_bottom]
and components are applied right to left, in the order light meets them.

Conventions (ideal, lossless, single wavelength):

    coupler(r)  = [[ sqrt(r),      1j*sqrt(1-r)],
                   [ 1j*sqrt(1-r), sqrt(r)     ]]     r = 0.5 is a 50:50 coupler
    phase(p)    = diag(exp(1j*p), 1)                  phase shift on the top arm
    mzi(t, f)   = coupler * phase(t) * coupler * phase(f)

theta (t) is the internal phase between the two couplers and sets the
splitting ratio; phi (f) is the external phase on the top input and sets the
relative phase. For ideal 50:50 couplers:

    mzi(t, f) = 1j*exp(1j*t/2) * [[exp(1j*f)*sin(t/2),  cos(t/2)],
                                  [exp(1j*f)*cos(t/2), -sin(t/2)]]

An MZI followed by an output phase screen diag(exp(1j*a), exp(1j*b)) can
realize any 2x2 unitary matrix. This is the building block of the Reck and
Clements meshes used for optical matrix multiplication.
"""
import numpy as np


def coupler(split=0.5):
    """Directional coupler; split is the fraction of power that stays in its arm."""
    t = np.sqrt(split)
    k = np.sqrt(1.0 - split)
    return np.array([[t, 1j * k], [1j * k, t]], dtype=complex)


def phase(p):
    """Phase shifter on the top waveguide."""
    return np.array([[np.exp(1j * p), 0], [0, 1]], dtype=complex)


def phase_screen(a, b):
    """Independent phase shifters on both outputs."""
    return np.diag([np.exp(1j * a), np.exp(1j * b)])


def mzi(theta, phi, split=0.5):
    """MZI transfer matrix: external phase, coupler, internal phase, coupler."""
    c = coupler(split)
    return c @ phase(theta) @ c @ phase(phi)


def mzi_analytic(theta, phi):
    """Closed form of mzi(theta, phi) for ideal 50:50 couplers."""
    s, c = np.sin(theta / 2), np.cos(theta / 2)
    return 1j * np.exp(1j * theta / 2) * np.array(
        [[np.exp(1j * phi) * s, c], [np.exp(1j * phi) * c, -s]], dtype=complex)


def program_unitary(u):
    """Find (theta, phi, a, b) so that phase_screen(a, b) @ mzi(theta, phi) == u.

    u must be a 2x2 unitary. theta is in [0, pi]. At exactly theta = 0 or pi
    the external phase phi is not uniquely defined (the output phases absorb
    it); it is then set to 0.

    With g the global phase of mzi_analytic, s = sin(theta/2), c = cos(theta/2):
        u00 = e^{i(a+g+phi)} s     u01 = e^{i(a+g)} c
        u10 = e^{i(b+g+phi)} c     u11 = e^{i(b+g)} (-s)
    No step divides by, or takes the phase of, an entry that may be tiny
    unless that entry's own size bounds the resulting error.
    """
    u = np.asarray(u, dtype=complex)
    # arctan2 of both magnitudes stays accurate near the bar (theta = pi) and
    # cross (theta = 0) states, where arcsin or arccos of one magnitude loses
    # the small entry to rounding.
    theta = 2 * np.arctan2(abs(u[0, 0]), abs(u[0, 1]))
    s, c = np.sin(theta / 2), np.cos(theta / 2)
    g = np.angle(1j * np.exp(1j * theta / 2))      # global phase of mzi_analytic
    # Both rows give e^{i phi} * s * c; summing them keeps phi well defined
    # whenever it matters, and an error in phi only scales with min(s, c).
    z = u[0, 0] * np.conj(u[0, 1]) - u[1, 0] * np.conj(u[1, 1])
    phi = np.angle(z) if abs(z) > 0 else 0.0
    # Take each output phase from the larger entry of its row.
    if c >= s:
        a = np.angle(u[0, 1]) - g
        b = np.angle(u[1, 0]) - g - phi
    else:
        a = np.angle(u[0, 0]) - g - phi
        b = np.angle(u[1, 1]) - g - np.pi
    wrap = lambda x: float(np.mod(x, 2 * np.pi))
    return float(theta), wrap(phi), wrap(a), wrap(b)


def programmed_matrix(theta, phi, a, b, split=0.5):
    """Transfer matrix of an MZI with an output phase screen."""
    return phase_screen(a, b) @ mzi(theta, phi, split)


def haar_unitary(n, rng):
    """Haar-random n x n unitary (QR of a complex Gaussian matrix)."""
    z = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) / np.sqrt(2)
    q, r = np.linalg.qr(z)
    d = np.diag(r)
    return q * (d / abs(d))


# --- Non-ideal hardware (OPA-MZI-002) ---------------------------------------
#
# A hardware description is a dict with any of:
#   split1, split2      power fraction that stays in its arm, first/second coupler
#   loss_top_db         extra loss in the top internal arm (e.g. the phase shifter)
#   loss_bottom_db      extra loss in the bottom internal arm

IDEAL_HW = {"split1": 0.5, "split2": 0.5, "loss_top_db": 0.0, "loss_bottom_db": 0.0}


def mzi_hw(theta, phi, hw=None):
    """MZI with unequal couplers and internal-arm loss."""
    hw = {**IDEAL_HW, **(hw or {})}
    arm = np.diag([np.exp(1j * theta) * 10 ** (-hw["loss_top_db"] / 20),
                   10 ** (-hw["loss_bottom_db"] / 20)])
    return coupler(hw["split2"]) @ arm @ coupler(hw["split1"]) @ phase(phi)


def programmed_matrix_hw(params, hw=None):
    """Transfer matrix of a programmed MZI plus output phase screen on given hardware."""
    theta, phi, a, b = params
    return phase_screen(a, b) @ mzi_hw(theta, phi, hw)


def shape_error(m, u):
    """Relative Frobenius error after removing the best common real gain.

    A common gain (uniform loss) only scales every output and is removed by
    detector calibration, so it is reported separately as insertion loss.
    """
    norm = np.vdot(m, m).real
    gain = np.vdot(m, u).real / norm if norm > 0 else 0.0
    return float(np.linalg.norm(gain * m - u) / np.linalg.norm(u))


def reachable_top_power_range(split1, split2):
    """Range of |T00|^2 a lossless MZI with these couplers can reach over theta.

    |T00|^2 = r1 r2 + (1-r1)(1-r2) - 2 sqrt(r1 r2 (1-r1)(1-r2)) cos(theta)
    """
    a = split1 * split2 + (1 - split1) * (1 - split2)
    b = 2 * np.sqrt(split1 * split2 * (1 - split1) * (1 - split2))
    return float(a - b), float(a + b)


def _phases_for(m0, u):
    """Output phases a, b and external phase phi that best map m0 = T(theta, 0) to u."""
    z = (u[0, 0] * np.conj(u[0, 1]) * np.conj(m0[0, 0]) * m0[0, 1]
         + u[1, 0] * np.conj(u[1, 1]) * np.conj(m0[1, 0]) * m0[1, 1])
    phi = np.angle(z) if abs(z) > 0 else 0.0
    if abs(m0[0, 1]) >= abs(m0[0, 0]):
        a = np.angle(u[0, 1]) - np.angle(m0[0, 1])
    else:
        a = np.angle(u[0, 0]) - np.angle(m0[0, 0]) - phi
    if abs(m0[1, 0]) >= abs(m0[1, 1]):
        b = np.angle(u[1, 0]) - np.angle(m0[1, 0]) - phi
    else:
        b = np.angle(u[1, 1]) - np.angle(m0[1, 1])
    return phi, a, b


def program_unitary_hw(u, hw=None, grid=360):
    """Hardware-aware programming: settings that best realize u on known hardware.

    Searches theta on a grid with analytically fitted phases, then refines all
    four settings with least squares on the shape error. On ideal hardware it
    reproduces program_unitary to rounding error. Targets outside the
    hardware's reachable set get the closest achievable matrix.
    """
    from scipy.optimize import least_squares

    u = np.asarray(u, dtype=complex)
    best = None
    for theta in np.linspace(0, 2 * np.pi, grid, endpoint=False):
        m0 = mzi_hw(theta, 0.0, hw)
        phi, a, b = _phases_for(m0, u)
        err = shape_error(programmed_matrix_hw((theta, phi, a, b), hw), u)
        if best is None or err < best[0]:
            best = (err, (theta, phi, a, b))

    def residual(p):
        m = programmed_matrix_hw(p, hw)
        gain = np.vdot(m, u).real / np.vdot(m, m).real
        d = (gain * m - u).ravel()
        return np.concatenate([d.real, d.imag])

    fit = least_squares(residual, np.array(best[1]), xtol=1e-15, ftol=1e-15,
                        gtol=1e-15, method="lm")
    params = fit.x if (shape_error(programmed_matrix_hw(fit.x, hw), u)
                       <= best[0]) else np.array(best[1])
    return tuple(float(np.mod(p, 2 * np.pi)) for p in params)
