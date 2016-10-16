import numpy as np
from hardware.cameras import default_cam_params
import logging
from settings.constants import *

class ParamHandler(object):
    """
    The ParamHandler class aggregates input from defaults, UI selections, and other sources, to provide a complete set of parameters to supply to a session when initiating.
    When the software is run from the UI, it instantiates a ParamHandler object and passes its params to the session it creates.
    """

    basics = dict(

        name                        = None,

        # hardware parameters
        ar_params                   = dict(ports=['ai0'], portnames=['hall'], runtime_ports=[0]),

        # trial parameters
        trial_duration              = 8.0,
        cs_dur                      = 0.500,
        us_dur                      = 0.030,
        csus_gap                    = 0.250,
        intro                       = 3.0,
        min_iti                     = 1.0,
        cycle                       = 6*[CSUS] + [US] + 6*[CSUS] + [CS] + 3*[CSUS] + [US] + 3*[CSUS],
        display_lag                 = 1., #second
        
        # cam parameters
        cam_params                  = default_cam_params,
        
        # eyelid parameters
        eyelid_buffer_size          = 130,
        eyelid_window               = 10,
        eyelid_thresh               = -1,

        # Experiment parameters
        subj                        = None,
        imaging                     = False,
      )


    def __init__(self, subj, imaging=False):
        self.subj = subj
        self.params = self.basics
        self.params.update(subj=self.subj, imaging=imaging)
