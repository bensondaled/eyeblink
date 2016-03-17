# manipulations refers to any perturbation condition that is specified for this particular behavioural training session, and is intended to be implemented by the software
# for example: optogenetic stimulation, imaging patterns, etc.
# the "manipulations" variable is just a dummy enumerator for a set of true manipluation value constants
# these constants, held in _manipulations_spec, specify the true manipulations conditions

manipulations = dict(   none = 0,
                        opto = 1,
                    )
_manipulations_spec = { 0 : 0,
                        1 : [0,1,2,3,4,5],
                      }

MANIP_NONE, MANIP_PAN, MANIP_ACC, MANIP_INTROACC, MANIP_DELAY, MANIP_REW = 0,1,2,3,4,5 #_manipulations_spec constants for readability
"""
Meanings of _manipulations_spec values (not keys!)
-----------------------------------
0 : no manipulation
1 : optogenetic LED, whole trial
2 : optogenetic LED, cue phase
3 : optogenetic LED, intro+cue phase
4 : optogenetic LED, delay phase
5 : optogenetic LED, reward phase
"""

default_manipulation = manipulations['none']
