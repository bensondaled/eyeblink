# Directories
save_dir            =   r'C:\Users\WangLab-Ephys\Desktop\eyeblink_data'

# Constants
CS                  = 0
US                  = 1
CSUS                = 2

# Conditioning
cs_onset            =   1. # seconds, relative to start of trial
cs_us_interval      =   0.2 # seconds
cs_duration         =   0.100 # seconds
us_duration         =   0.050 # seconds
iti                 =   5 # seconds (intertrial interval)   
stim_cycle          =   6*[CSUS] + [US] + 6*[CSUS] + [CS]

# Hardware
daq_cs_settings           =   dict(   ports=['port0/line3'],  port_names=['cs']   )
daq_us_settings           =   dict(   ports=['port0/line5'],  port_names=['us']   )
cam_params          =   dict(   idx=(0,1), resolution_mode=(1,1), frame_rate=(100,100), color_mode=(0,0), 
                                cleye_params = (
                                
                                dict(  auto_gain=False,
                                       auto_exposure=False,
                                       auto_whitebalance=False,
                                       whitebalance_blue=50,
                                       whitebalance_red=50,
                                       whitebalance_green=50,
                                       gain=30,
                                       exposure=90,
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
                                       exposure=90,
                                       vflip=False,
                                       hflip=True,
                                )
                                
                                ))