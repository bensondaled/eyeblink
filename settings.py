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
cam_params          =   dict(   idx=(0,1), resolution_mode=(0,0), frame_rate=(30,30), color_mode=(0,0), 
                                cleye_params = ( dict(
                                                    auto_gain = True,
                                                    auto_exposure = True,
                                                    auto_whitebalance = True,
                                                    vflip = True,
                                                    hflip = True,
                                                    rotation = False#-500,
                                                    ),
                                            dict(
                                                    auto_gain = True,
                                                    auto_exposure = True,
                                                    auto_whitebalance = True,
                                                    
                                                    vflip = True,
                                                    hflip = True,
                                                    rotation = False#-500,
                                                    )
                                            ))
