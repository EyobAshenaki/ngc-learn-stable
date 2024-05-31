from jax import numpy as jnp, random, jit, nn
from functools import partial
import time, sys
from ngclearn import resolver, Component, Compartment
from ngclearn.utils import tensorstats
from ngclearn.utils.model_utils import softmax

@jit
def update_times(t, s, tols):
    """
    Updates time-of-last-spike (tols) variable.

    Args:
        t: current time (a scalar/int value)

        s: binary spike vector

        tols: current time-of-last-spike variable

    Returns:
        updated tols variable
    """
    _tols = (1. - s) * tols + (s * t)
    return _tols

#@partial(jit, static_argnums=[7,8,9,10,11])
def run_cell(dt, j, v, rfr, v_thr, tau_m, R_m, thr_gain=0.002, refract_T=0.):
    """
    Runs leaky integrator neuronal dynamics

    Args:
        dt: integration time constant (milliseconds, or ms)

        j: electrical current value

        v: membrane potential (voltage, in milliVolts or mV) value (at t)

        rfr: refractory variable vector (one per neuronal cell)

        v_thr: base voltage threshold value (in mV)

        tau_m: cell membrane time constant

        R_m: cell membrane resistance

        thr_gain: increment to be applied to threshold upon spike occurrence

        refract_T: (relative) refractory time period (in ms; Default
            value is 1 ms)

    Returns:
        voltage(t+dt), spikes, updated voltage thresholds, updated refactory variables
    """
    mask = (rfr >= refract_T).astype(jnp.float32) ## check refractory period
    v = (j * R_m) * mask
    vp = softmax(v) # convert to Categorical (spike) probabilities
    #s = nn.one_hot(jnp.argmax(vp, axis=1), j.shape[1]) ## hard-max spike
    s = (vp > v_thr).astype(jnp.float32) ## calculate action potential
    q = 1. ## Note: thr_gain ==> "rho_b"
    dthr = jnp.sum(s, axis=1, keepdims=True) - q
    v_thr = jnp.maximum(v_thr + dthr * thr_gain, 0.025) ## calc new threshold
    rfr = (rfr + dt) * (1. - s) + s * dt # set refract to dt
    return v, s, v_thr, rfr

class WTASCell(Component): ## winner-take-all spiking cell
    """
    A spiking cell based on winner-take-all neuronal dynamics ("WTAS" stands
    for "winner-take-all-spiking").

    The differential equation for adjusting this specific cell
    (for adjusting v, given current j, over time) is:

    | tau_m * dv/dt = j * R  ;  v_p = softmax(v)
    | where R is membrane resistance and v_p is a voltage probability vector

    Args:
        name: the string name of this cell

        n_units: number of cellular entities (neural population size)

        tau_m: membrane time constant

        R_m: membrane resistance value (Default: 1)

        thr_base: base value for adaptive thresholds that govern short-term
            plasticity (in milliVolts, or mV)

        thr_gain: increment to be applied to threshold in presence of spike

        refract_T: relative refractory period time (ms; Default: 1 ms)

        thr_jitter: scale of uniform jitter to add to initialization of thresholds

        key: PRNG key to control determinism of any underlying random values
            associated with this cell

        directory: string indicating directory on disk to save LIF parameter
            values to (i.e., initial threshold values and any persistent adaptive
            threshold values)
    """

    # Define Functions
    def __init__(self, name, n_units, tau_m, R_m=1., thr_base=0.4, thr_gain=0.002,
                 refract_T=0., thr_jitter=0.05, key=None, directory=None, **kwargs):
        super().__init__(name, **kwargs)

        ## membrane parameter setup (affects ODE integration)
        self.tau_m = tau_m ## membrane time constant
        self.R_m = R_m ## resistance value
        self.thr_gain = thr_gain
        self.thr_base = thr_base # mV ## base value for threshold
        self.refract_T = refract_T

        ##Layer Size Setup
        self.batch_size = 1
        self.n_units = n_units

        key, subkey = random.split(key)
        self.threshold0 = thr_base + random.uniform(subkey, (1, n_units),
                                                   minval=-thr_jitter, maxval=thr_jitter,
                                                   dtype=jnp.float32)

        ## Compartment setup
        restVals = jnp.zeros((self.batch_size, self.n_units))
        self.j = Compartment(restVals)
        self.v = Compartment(restVals)
        self.s = Compartment(restVals)
        self.thr = Compartment(self.threshold0)
        self.rfr = Compartment(restVals + self.refract_T)
        self.tols = Compartment(restVals) ## time-of-last-spike
        #self.reset()

    @staticmethod
    def _advance_state(t, dt, tau_m, R_m, thr_gain, refract_T, j, v, s, thr, rfr, tols):
        v, s, thr, rfr = run_cell(dt, j, v, rfr, thr, tau_m, R_m, thr_gain, refract_T)
        tols = update_times(t, s, tols) ## update tols
        return v, s, thr, rfr, tols

    @resolver(_advance_state)
    def advance_state(self, v, s, thr, rfr, tols):
        self.v.set(v)
        self.s.set(s)
        self.thr.set(thr)
        self.rfr.set(rfr)
        self.tols.set(tols)

    @staticmethod
    def _reset(batch_size, n_units, refract_T):
        restVals = jnp.zeros((batch_size, n_units))
        j = restVals #+ 0
        v = restVals #+ 0
        s = restVals #+ 0
        rfr = restVals + refract_T
        tols = restVals #+ 0
        return j, v, s, rfr, tols

    @resolver(_reset)
    def reset(self, j, v, s, rfr, tols):
        self.j.set(j)
        self.v.set(v)
        self.s.set(s)
        self.rfr.set(rfr)
        self.tols.set(tols)

    def save(self, directory, **kwargs):
        file_name = directory + "/" + self.name + ".npz"
        jnp.savez(file_name, threshold=self.thr.value)

    def load(self, directory, seeded=False, **kwargs):
        file_name = directory + "/" + self.name + ".npz"
        data = jnp.load(file_name)
        self.thr.set( data['threshold'] )

    def __repr__(self):
        comps = [varname for varname in dir(self) if Compartment.is_compartment(getattr(self, varname))]
        maxlen = max(len(c) for c in comps) + 5
        lines = f"[{self.__class__.__name__}] PATH: {self.name}\n"
        for c in comps:
            stats = tensorstats(getattr(self, c).value)
            if stats is not None:
                line = [f"{k}: {v}" for k, v in stats.items()]
                line = ", ".join(line)
            else:
                line = "None"
            lines += f"  {f'({c})'.ljust(maxlen)}{line}\n"
        return lines

if __name__ == '__main__':
    from ngcsimlib.context import Context
    with Context("Bar") as bar:
        X = WTASCell("X", 1, 1.)
    print(X)
