# Directories
save_dir            =   '/path/to/save/directory'

# Constants
CS                  = 0
US                  = 1
CSUS                = 2

# Hardware
daq_ports           =   [   'port0/line0', 'port0/line1'   ]
port_names          =   [   'light',       'puff'          ]
lines               =   dict(cs=0, us=1)
cam_params          =   {}

# Conditioning
cs_onset            =   1. # seconds, relative to start of trial
cs_us_interval      =   0.2 # seconds
cs_duration         =   0.100 # seconds
us_duration         =   0.050 # seconds
iti                 =   10 # seconds (intertrial interval)   
stim_cycle          =   6*[CSUS] + [US] + 6*[CSUS] + [CS]
