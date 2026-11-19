"""Single-frequency, power-normalized complex scattering network.

b = S a; connected ports exchange outgoing waves with incoming waves.
Port order is explicit. No implicit phase, loss, or cross-process conversion.
"""
import numpy as np


def reciprocal_transmission(t):
    """Reflectionless reciprocal block; reverse transmission is transpose."""
    t = np.asarray(t, dtype=complex)
    if t.ndim != 2 or not t.size or not np.isfinite(t).all():
        raise ValueError("invalid transmission matrix")
    m, n = t.shape
    s = np.zeros((n+m, n+m), complex)
    s[n:, :n] = t
    s[:n, n:] = t.T
    return s


def assemble(blocks, links, external):
    """Return full external S; blocks map names to (ordered ports, S).

    Each port must be linked exactly once or exposed exactly once.
    Links are ideal zero-length connections; use a block for propagation.
    No conjugation when exchanging waves. Reject ill-conditioned feedback.
    """
    names, matrices = [], []
    for name, (ports, matrix) in blocks.items():
        ports = tuple(ports)
        s = np.asarray(matrix, dtype=complex)
        if not ports or len(set(ports)) != len(ports) or s.shape != (len(ports),)*2 or not np.isfinite(s).all():
            raise ValueError("invalid block: "+name)
        names.extend((name, p) for p in ports)
        matrices.append(s)
    index = {p:i for i,p in enumerate(names)}
    if not names or not external:
        raise ValueError("empty network or boundary")
    try:
        e = [index[p] for p in external]
        pairs = [(index[p], index[q]) for p,q in links]
    except KeyError as exc:
        raise ValueError("unknown port") from exc
    internal = [p for pair in pairs for p in pair]
    used = e+internal
    if len(used) != len(names) or len(set(used)) != len(names):
        raise ValueError("ports must be connected or exposed exactly once")
    s = np.zeros((len(names),)*2, complex)
    offset = 0
    for matrix in matrices:
        n = len(matrix)
        s[offset:offset+n,offset:offset+n] = matrix
        offset += n
    see = s[np.ix_(e,e)]
    if not internal:
        return see
    # Internal ordering is consecutive pairs, so P swaps each adjacent pair.
    p = np.eye(len(internal))[np.arange(len(internal)) ^ 1]
    sii = s[np.ix_(internal,internal)]
    sie = s[np.ix_(internal,e)]
    sei = s[np.ix_(e,internal)]
    a = np.eye(len(internal))-p@sii
    if not np.isfinite(a).all() or np.linalg.cond(a) > 1e12:
        raise ValueError("singular or ill-conditioned internal network")
    result = see + sei @ np.linalg.solve(a,p@sie)
    if not np.isfinite(result).all():
        raise ValueError("nonfinite network result")
    return result
