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

TOL_DEGENERATE = 1e-12


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

    u must be a 2x2 unitary. theta is in [0, pi]. When theta is 0 or pi the
    external phase phi is not uniquely defined; it is then set to 0 and the
    output phases absorb the difference.
    """
    u = np.asarray(u, dtype=complex)
    s = np.clip(abs(u[0, 0]), 0.0, 1.0)
    theta = 2 * np.arcsin(s)
    s, c = np.sin(theta / 2), np.cos(theta / 2)
    g = np.angle(1j * np.exp(1j * theta / 2))      # global phase of mzi_analytic
    if c > TOL_DEGENERATE and s > TOL_DEGENERATE:
        phi = np.angle(u[0, 0]) - np.angle(u[0, 1])
        a = np.angle(u[0, 1]) - g
        b = np.angle(u[1, 1]) - (g + np.pi)          # u11 = e^{ib} * (-s) * e^{ig}
    elif s <= TOL_DEGENERATE:                       # theta = 0: cross state
        phi = 0.0
        a = np.angle(u[0, 1]) - g
        b = np.angle(u[1, 0]) - g
    else:                                           # theta = pi: bar state
        phi = 0.0
        a = np.angle(u[0, 0]) - g
        b = np.angle(u[1, 1]) - (g + np.pi)
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
