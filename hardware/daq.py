import PyDAQmx as pydaq
from PyDAQmx.DAQmxCallBack import *
import numpy as np
import warnings, logging, threading
import time
from util import now,now2

class Trigger(object):
    def __init__(self, msg=[], duration=None, name='noname', dtype=np.uint8):
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
    DIGITAL_OUT = 1
    def __init__(self, device='Dev1', ports=[], port_names=[], timeout=5.0, saver=None):
        
        # DAQ properties
        pydaq.Task.__init__(self)
        self.device = device
        self.ports = ports
        self.timeout = timeout
        self.ports = ['/'.join([self.device,port]) for port in self.ports]
        self.port_dict = {pn:idx for idx,pn in enumerate(port_names)}
        
        # Setup task
        try:
            for port in self.ports:
                self.CreateDOChan(port, "OutputOnly", pydaq.DAQmx_Val_ChanForAllLines)
            self.StartTask()
        except:
            warnings.warn("DAQ task did not successfully initialize")
            raise

    def go(self, port_name, duration):
        threading.Thread(target=self._go, args=(port_name, duration)).start()
    
    def _go(self, port_name, duration):
        trig = Trigger(msg=[0 for i in self.ports])
        
        # ON
        trig.msg[self.port_dict[port_name]] = 1
        try:
            self.WriteDigitalLines(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,trig.msg,None,None)
        except:
            logging.warning("DAQ task not functional. Attempted to write %s."%str(trig.msg))
            raise
        time.sleep(duration)
        # OFF
        trig.msg[self.port_dict[port_name]] = 0
        try:
            self.WriteDigitalLines(1,1,self.timeout,pydaq.DAQmx_Val_GroupByChannel,trig.msg,None,None)
        except:
            logging.warning("DAQ task not functional. Attempted to write %s."%str(trig.msg))
            raise

            
    def end(self):
        try:
            self.StopTask()
            self.ClearTask()
        except:
            pass
                
if __name__ == '__main__':
    pass
