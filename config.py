import os

# global vars
TESTING_MODE = False
datafile = os.path.join('data','data.h5')

# rig params
reward_dur = [0.106,0.108]
stim_dur = 0.015
ar_params                   = dict(lick_thresh=5.0, ports=['ai2','ai3','ai4','ai5','ai6'], portnames=['lickl','lickr','puffl','puffr','optoled'], runtime_ports=[0,1])
stimulator_params           = dict(ports=['port0/line0','port0/line1'], duration=stim_dur)
spout_params                = dict(ports=['port0/line2','port0/line3'], duration=reward_dur)
light_params                = dict(port='ao0', val=-5.0)
opto_led_params             = dict(port='port0/line4')
