"""
Levels are the abstraction that holds advancing steps of training and the criteria required to advance through them.

A level consists of only params that must be considered on a trial-by-trial basis when generating trials. Specifically:
    -Criteria to advance to it
        -number of trials done in this level
        -window (number of CONTIGUOUS [i.e. no level-changes between them] trials) over which to assess following criteria
        -% correct in this level (of n=win valid trials)
        -% bias in this level (of n=win valid trials)
        -% valid in this level (of n=win trials of any kind)
    -Gamma
    -Rule
    -Manipulation
    -Durations

Levels are supplied to TrialHandler as a list, where each element is a subsequent level.
A given level is defined in a dict, with keys:
    "criteria" : a dict containing "n", "win", "perc", "valid", and "bias" keys, indicating the necessary values in this level to be considered "competent"
    "rule" : a rule value from the class constants
    "ratio" : either a value or a list of values (which will be randomly sampled).
    "manip" : either a value or a list of values (which will be randomly sampled). If None, will be filled in by ParamHandler using UI input
    "stim_phase_dur" : mean +- std
    "delay_phase_dur" : mean +- std
    
IMPORTANT NOTE:
    Do not edit the levels variable arbitrarily. The position of each level within the list is stored in every trial when saved, and this information is used to determine how an animal should be trained each session.
"""
from settings.rules import *
from settings.durations import stim_phase_durs, delay_phase_durs
from manipulations import default_manipulation
from ratios import final_ratios, default_ratio

levels = [
            dict( #0
                    criteria = dict(    n=80,
                                        win=45,
                                        perc=0.0,
                                        bias=1.0,
                                        valid=0.6,
                                    ),

                    rule = RULE_PASSIVE,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            
            dict( #1
                    criteria = dict(    n=40,
                                        win=40,
                                        perc=0.1,
                                        bias=1.0,
                                        valid=0.5,
                                    ),

                    rule = RULE_PHASE,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = stim_phase_durs[0],
                    delay_phase_dur = delay_phase_durs[0],
                 ),
            dict( #2
                    criteria = dict(    n=40,
                                        win=40,
                                        perc=0.1,
                                        bias=1.0,
                                        valid=0.6,
                                    ),

                    rule = RULE_PHASE,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = stim_phase_durs[1],
                    delay_phase_dur = delay_phase_durs[1],
                 ),
            dict( #3
                    criteria = dict(    n=40,
                                        win=40,
                                        perc=0.1,
                                        bias=1.0,
                                        valid=0.6,
                                    ),

                    rule = RULE_PHASE,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = stim_phase_durs[2],
                    delay_phase_dur = delay_phase_durs[2],
                 ),
            dict( #4
                    criteria = dict(    n=120,
                                        win=40,
                                        perc=0.3,
                                        bias=0.7,
                                        valid=0.7,
                                    ),

                    rule = RULE_PHASE,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            
            dict( #5
                    criteria = dict(    n=120,
                                        win=40,
                                        perc=0.7,
                                        bias=0.6,
                                        valid=0.6,
                                    ),

                    rule = RULE_FAULT,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            dict( #6
                    criteria = dict(    n=120,
                                        win=40,
                                        perc=0.8,
                                        bias=0.6,
                                        valid=0.65,
                                    ),

                    rule = RULE_HINT,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            dict( #7
                    criteria = dict(    n=12000,
                                        win=40,
                                        perc=0.8,
                                        bias=0.6,
                                        valid=0.65,
                                    ),

                    rule = RULE_FULL,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = delay_phase_durs[-1],
                 ),
            dict( #8
                    criteria = dict(    n=120,
                                        win=40,
                                        perc=0.8,
                                        bias=0.6,
                                        valid=0.65,
                                    ),

                    rule = RULE_FULL,
                    ratio = default_ratio, 
                    manip = default_manipulation,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            
            dict( #9
                    criteria = dict(    n=500,
                                        win=500,
                                        perc=0.9,
                                        bias=0.5,
                                        valid=0.9,
                                    ),

                    rule = RULE_FULL,
                    ratio = final_ratios,
                    manip = None,
                    stim_phase_dur = None,
                    delay_phase_dur = None,
                 ),
            ]
