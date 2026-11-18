"""Causal balanced receiver primitives for NL010 (SI electrical units).

The second stochastic state is the mean current over one step, not charge.
All random innovations are supplied by the caller.
"""
import numpy as np
from nonlinear_activation_v003 import Q, R, TIA, RIN, CMRR
from nonlinear_activation_v009 import rhs, COUP, LOSS

# Gauss-Legendre integrates smooth exact OU kernels without subtractive
# cancellation for very short steps. The independent closed form is tested.
_NODES, _WEIGHTS = np.polynomial.legendre.leggauss(16)
_U=(_NODES+1)/2
_W=_WEIGHTS/2

def hybrid(field, lo_mw, loss_db=3., phase_deg=15.):
    e=np.asarray(field)*np.sqrt(1e-3*10**(-loss_db/10))*np.exp(1j*np.deg2rad(phase_deg))
    pl=lo_mw*1e-3
    ps=abs(e)**2
    pp=abs(e+np.sqrt(pl))**2/2
    pm=abs(e-np.sqrt(pl))**2/2
    return R*(pp-pm),ps,pp,pm

def psd(ps,lo_mw):
    pl=lo_mw*1e-3
    return 2*Q*R*(ps+pl)+TIA**2+(R*pl)**2*RIN*10**(-CMRR/10)

def coefficients(fc_ghz,dt_ps):
    if fc_ghz<=0 or dt_ps<=0:
        raise ValueError("positive cutoff and time required")
    lam=2*np.pi*fc_ghz*1e9
    dt=dt_ps*1e-12
    x=lam*dt
    a=np.exp(-x)
    m=-np.expm1(-x)/x
    # Unit one-sided input PSD. Kernels for state and step mean.
    k=lam*np.exp(-x*_U)
    j=-np.expm1(-x*_U)/dt
    if x<=.1:
        cov=dt/2*np.array([[np.dot(_W,k*k),np.dot(_W,k*j)],
                           [np.dot(_W,k*j),np.dot(_W,j*j)]])
    else:
        one=-np.expm1(-x); two=-np.expm1(-2*x)
        v=lam*two/4
        cross=one**2/(4*dt)
        avg=(dt-2*one/lam+two/(2*lam))/(2*dt**2)
        cov=np.array([[v,cross],[cross,avg]])
    return a,m,cov

def deterministic(state,current,a,m):
    return a*state+(1-a)*current, m*state+(1-m)*current

def noisy_step(state,current,spectrum,a,m,factor,g0,g1):
    """factor=Cholesky of unit-PSD joint covariance; g0/g1 iid normals."""
    end,mean=deterministic(state,current,a,m)
    scale=np.sqrt(spectrum)
    return end+scale*factor[0,0]*g0, mean+scale*(factor[1,0]*g0+factor[1,1]*g1)

def rk4_wave_step(a,q,s,b,d,h,tr,dt):
    """Stage-matched energy plus independent half-step midpoint waveform."""
    def step(a,q,dt):
        k1,j1,*p1=rhs(a,q,s,b,d,h,tr)
        k2,j2,*p2=rhs(a+dt*k1/2,q+dt*j1/2,s,b,d,h,tr)
        k3,j3,*p3=rhs(a+dt*k2/2,q+dt*j2/2,s,b,d,h,tr)
        k4,j4,*p4=rhs(a+dt*k3,q+dt*j3,s,b,d,h,tr)
        return (a+dt*(k1+2*k2+2*k3+k4)/6,q+dt*(j1+2*j2+2*j3+j4)/6,
                dt*(np.asarray(p1)+2*np.asarray(p2)+2*np.asarray(p3)+np.asarray(p4))/6)
    mid,_,_=step(a,q,dt/2)
    end,qn,energy=step(a,q,dt)
    return end,qn,COUP*mid*np.sqrt(LOSS),energy

def waveform(z,w2,case,tr,on,gap,dt):
    """Yield one symbol at a time; state carries across slots.

    z: (channel, parallel stream, symbol); w2: (1,channel).
    Yield midpoint classifier samples (step,stream), exact on-end classifier,
    max normalized slot balance and max passive second-MVM excess.
    """
    n_on=round(on/dt); n_gap=round(gap/dt)
    if n_on<=0 or not np.isclose(n_on*dt,on) or not np.isclose(n_gap*dt,gap):
        raise ValueError("grid does not divide slot")
    a=np.zeros(z.shape[:-1],complex); q=np.zeros(z.shape[:-1])
    for sym in range(z.shape[-1]):
        initial=abs(a)**2
        s=z[...,sym]; e=np.zeros((3,)+a.shape)
        fields=[]; excess=-np.inf
        for k in range(n_on+n_gap):
            inc=s if k<n_on else np.zeros_like(s)
            a,q,mid,energy=rk4_wave_step(a,q,inc,*case,tr,dt)
            e+=energy
            f=(w2@mid).ravel()
            excess=max(excess,float(np.max(abs(f)**2-np.sum(abs(mid)**2,axis=0))))
            fields.append(f)
            if k==n_on-1:
                endpoint=(w2@(COUP*a*np.sqrt(LOSS))).ravel()
        incident=abs(s)**2*on
        balance=np.max(abs(incident+initial-e.sum(axis=0)-abs(a)**2)/(1+incident+initial))
        yield np.stack(fields),endpoint,float(balance),excess
