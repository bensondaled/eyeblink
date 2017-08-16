# Directories
save_dir            =   r'C:\Users\WangLab-Ephys\Desktop\eyeblink_data'

# Constants
CS                  = 0
US                  = 1
CSUS                = 2

# Conditioning
cs_onset            =   1. # seconds, relative to start of trial
iti                 =   5 # seconds (intertrial interval)   
stim_cycle          =   6*[CSUS] + [US] + 6*[CSUS] + [CS]

# DO NOT EDIT WITHOUT CHANGING MASTER8 ALSO:
cs_duration         =   0.280 # seconds -- controlled by master8 (duration of channel 1)
us_duration         =   0.030 # seconds -- controlled by master8 (duration of channel 2)
cs_us_interval      =   0.250 # seconds -- controlled by master8 (delay of channel 2)
ttl_gap             =   .050 # arbitrary, for ttl duration

# Hardware
daq_cs_settings           =   dict(   ports=['port0/line3'],  port_names=['cs']   )
daq_us_settings           =   dict(   ports=['port0/line5'],  port_names=['us']   )
cam_params          =   dict(   idx=(0,1), resolution_mode=(0,0), frame_rate=(125,125), color_mode=(0,0), 
                                cleye_params = (
                                
                                dict(  auto_gain=False,
                                       auto_exposure=False,
                                       auto_whitebalance=False,
                                       whitebalance_blue=50,
                                       whitebalance_red=50,
                                       whitebalance_green=50,
                                       gain=30,
                                       exposure=17,
                                       vflip=False,
                                       hflip=True,
                                ), 
                                
                                dict(  auto_gain=False,
                                       auto_exposure=False,
                                       auto_whitebalance=False,
                                       whitebalance_blue=50,
                                       whitebalance_red=50,
                                       whitebalance_green=50,
                                       gain=30,
                                       exposure=50,
                                       vflip=False,
                                       hflip=True,
                                )
                                
                                ))