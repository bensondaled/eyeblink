from analog_reader import AnalogReader
from cameras import default_cam_params, PSEye
from ni845x import NI845x
from settings.constants import *

def dummy_puff():
    import time
    ni = NI845x()
    ni.write_dio(LINE_US, 1)
    time.sleep(0.100)
    ni.write_dio(LINE_US, 0)
    ni.end()
    
def dummy_light(state):
    ni = NI845x()
    ni.write_dio(LINE_CS, state)
    ni.end()