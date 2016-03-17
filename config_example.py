"""
This is an example configuration file.
config.py is not copied to the repository because each rig has different parameters.
To make a usable version, copy this file into config.py and adjust as desired.
"""

import os

# global vars
TESTING_MODE = False
datafile = os.path.join('data','data.h5')

# rig params
reward_dur = [0.101,0.107]
stim_dur = 0.015
ar_params                   = dict(lick_thresh=5.0, ports=['ai2','ai3','ai4','ai5','ai6'], portnames=['lickl','lickr','puffl','puffr','optoled'], runtime_ports=[0,1])
stimulator_params           = dict(ports=['port0/line0','port0/line1'], duration=stim_dur)
spout_params                = dict(ports=['port0/line2','port0/line3'], duration=reward_dur)
light_params                = dict(port='ao0')
opto_led_params             = dict(port='port0/line4')
