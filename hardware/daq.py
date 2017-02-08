
import PyDAQmx as pydaq
from PyDAQmx.DAQmxCallBack import *
import numpy as np
import multiprocessing as mp
import warnings, threading, logging, copy
from util import now,now2

class Trigger(object):
    def __init__(self, msg=[], duration=None, name='noname', dtype=np.float64):
        self.duration = duration
        self.dtype = dtype
        self._msg = None
        self.msg = msg
        self.name = name

    @property
    def msg(self):
        return self._msg
    @msg.setter
    def msg(self, msg):
        self._msg = np.array(msg).astype(self.dtype)

class DAQOut(pydaq.Task):
    ANALOG_OUT = 0
    DIGITAL_OUT = 1
    def __init__(self, mode, device='Dev1', ports=['port0/line2','port0/line3'], timeout=5.0, analog_minmax=(-10,10)):
        
        # DAQ properties
        pydaq.Task.__init__(self)
        self.mode = mode
        self.device = device
        self.ports = ports
        self.timeout = timeout
        self.ports = ['/'.join([self.device,port]) for port in self.ports]

        # Trigger properties
        self.minn,self.maxx = analog_minmax
        if self.mode == self.ANALOG_OUT:
            self.clear_trig = Trigger(msg=[self.minn for _ in self.ports])
        elif self.mode == self.DIGITAL_OUT:
            self.clear_trig = Trigger(msg=[0,0,0,0], dtype=np.uint8)
        
        # Setup task
        try:
            if self.mode == self.DIGITAL_OUT:
                for port in self.ports:
                    self.CreateDOChan(port, "OutputOnly", pydaq.DAQmx_Val_ChanForAllLines)

            elif self.mode == self.ANALOG_OUT:
                for port in self.ports:
                    self.CreateAOVoltageChan(port, '', self.minn, self.maxx, pydaq.DAQmx_Val_Volts, None)

            self.StartTask()
        except:
            warnings.warn("DAQ task did not successfully initialize")
            raise

    def trigger(self, trig, clear=None):
        if clear == None:
            clear = self.clear_trig
        try:
            if self.mode == self.DIGITAL_OUT:
                self.WriteDigitalLines(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,trig.msg,None,None)
                if clear is not False:
                    self.WriteDigitalLines(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,clear.msg,None,None)

            elif self.mode == self.ANALOG_OUT:
                self.WriteAnalogF64(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,trig.msg,None,None)
                if clear is not False:
                    self.WriteAnalogF64(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,clear.msg,None,None)
        except:
            logging.warning("DAQ task not functional. Attempted to write %s."%str(trig.msg))
            raise

    def release(self):
        try:
            self.StopTask()
            self.ClearTask()
        except:
            pass
                
if __name__ == '__main__':
    pass
