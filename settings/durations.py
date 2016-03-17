# Specifies the different preset durations for stimulus and delay phases
# Implements logic to discretely sample from gaussian for these params

import numpy as np
from scipy.stats.distributions import norm as normdist

delay_phase_duration_n      = 10
stim_phase_duration_n       = 10

def _sample_duration(params, n):
    dist = normdist(*params)
    options = np.linspace(*dist.ppf([0.01,0.99]),num=n)
    cdfs = dist.cdf(options)
    cdfs[cdfs>0.5] = 1-cdfs[cdfs>0.5]
    return [ options.tolist(), (cdfs/np.sum(cdfs)).tolist() ]

default_stim_phase_duration = _sample_duration([1.5, 0.4], stim_phase_duration_n)
default_delay_phase_duration = _sample_duration([1.5, 0.4], delay_phase_duration_n)

stim_phase_durs = [_sample_duration(i, n=stim_phase_duration_n) for i in [[0.5,0.1],[0.7,0.13],[1.0,0.2]]]
delay_phase_durs = [_sample_duration(i, n=delay_phase_duration_n) for i in [[0.2,0.1],[0.4,0.13],[0.7,0.2]]]

