import numpy as np
from expts.session import Session as S
from hardware.cameras import default_cam_params
from conditions import default_condition
from settings.manipulations import default_manipulation, _manipulations_spec
from settings.durations import default_stim_phase_duration, default_delay_phase_duration
from levels import levels
from ratios import default_ratio
import config, logging

class ParamHandler(object):
    """
    The ParamHandler class aggregates input from defaults, UI selections, and other sources, to provide a complete set of parameters to supply to a session when initiating.
    When the software is run from the UI, it instantiates a ParamHandler object and passes its params to the session it creates.
    """

    basics = dict(

        name                            = None,

        # Trial parameters
        trial_params =  dict(
            rate_sum                    = 5.0,
            stim_duration               = config.stim_dur,
            stim_phase_duration         = default_stim_phase_duration,
            stim_phase_pad              = [0.0, 0.050],
            min_isi                     = 0.070,
            delay_phase_duration        = default_delay_phase_duration,
            n_previous_level            = 20,
            # Anti-biasing parameters
            bias_correction             = 8,
            max_bias_correction         = 0.1,  ),

        # Hardware parameters
        ar_params                   = config.ar_params,
        stimulator_params           = config.stimulator_params,
        spout_params                = config.spout_params,
        light_params                = config.light_params,
        opto_led_params             = config.opto_led_params,

        # Timing parameters
        phase_durations             = {      S.PHASE_INTRO:1.0,\
                                             S.PHASE_STIM:None,\
                                             S.PHASE_DELAY:None,\
                                             S.PHASE_LICK:4.0,\
                                             S.PHASE_REWARD:4.0,\
                                             S.PHASE_ITI:3.5,\
                                             S.PHASE_END:0.0 },
        penalty_iti_frac            = 2.0,
        enforce_stim_phase_duration = True,

        # Rule parameters
        hold_rule                   = True,
        lick_rule_phase             = True,
        lick_rule_side              = True,
        lick_rule_any               = True, 
        use_trials                  = True,
        puffs_on                    = True,
        rewards_on                  = True,
        hint_interval               = 0.200,

        # Movie parameters
        cam_params                  = default_cam_params,

        # Experiment parameters
        subj                        = None,
        condition                   = None,
      )


    def __init__(self, subj, condition=default_condition, manipulation=default_manipulation):
        self.subj = subj
        self.params = self.basics
        self.manip = _manipulations_spec[manipulation]
        self.params.update(subj=self.subj, condition=condition)

        if config.TESTING_MODE:
            self.params['trial_params'].update(stim_phase_duration=[0.5,0.05], delay_phase_duration=[0.5,0.05])
            self.params['phase_durations'] = {   S.PHASE_INTRO:0.1,\
                                                     S.PHASE_STIM:None,\
                                                     S.PHASE_DELAY:None,\
                                                     S.PHASE_LICK:0.1,\
                                                     S.PHASE_REWARD:0.1,\
                                                     S.PHASE_ITI:1.0,\
                                                     S.PHASE_END:0.0 }

        for l in levels:
            if l['manip'] is None:
                l['manip'] = self.manip
        self.params['trial_params'].update(levels=levels)
