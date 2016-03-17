import numpy as np
from util import now
import multiprocessing as mp

class DAQIn(object):
    ANALOG_IN,ANALOG_OUT,DIGITAL_IN,DIGITAL_OUT = 0,0,0,0
    sample_rate = 0
    def __init__(self,*args,**kwargs):
        self.t0 = now()
        self.sample_rate = 40
        self.data_q = mp.Queue()
    def get(self):
        while now()-self.t0 < 1./self.sample_rate:
            pass
        self.t0 = now()
        return now(),(0.1*np.arange(50)).reshape([5,10]).astype(float)+np.random.normal(0,.5,size=[5,10])
    def trigger(self, *args, **kwargs):
        pass
    def release(self):
        pass

class DAQOut(object):
    ANALOG_IN,ANALOG_OUT,DIGITAL_IN,DIGITAL_OUT = 0,0,0,0
    sample_rate = 0
    def __init__(self,*args,**kwargs):
        self.t0 = now()
        self.sample_rate = 40
    def get(self):
        while now()-self.t0 < 1./self.sample_rate:
            pass
        self.t0 = now()
        return now(),(0.1*np.arange(50)).reshape([5,10]).astype(float)+np.random.normal(0,.5,size=[5,10])
    def trigger(self, *args, **kwargs):
        pass
    def release(self):
        pass

class Trigger(object):
    def __init__(*args, **kwargs):
        pass

class PSEye(object):
    cS = None
    SAVING = type('obj', (object,), {'value' : None})
    def __init__(self, *args,**kwargs):
        self.flush = mp.Value('i',0)
    def start(self):
        pass
    def get_current_frame(*args,**kwargs):
        return np.random.random([320,240])
    def save_on(self):
        pass
    def end(self):
        pass

default_cam_params = dict()
