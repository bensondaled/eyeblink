import numpy as np
import logging
from daq import DAQOut, Trigger

class Light(object):
    OFF,ON = 0,1
    def __init__(self, port='ao0', saver=None, val=5.0):
        self.port = port
        self.saver = saver
        self.daq = DAQOut(DAQOut.ANALOG_OUT, ports=[self.port])
        self.trig = Trigger(val, dtype=np.float64)
        self.end_trig = Trigger(0.0, dtype=np.float64)

        self.is_on = False
    def on(self):
        if self.is_on:
            return
        
        self.daq.trigger(self.trig, clear=False)
        if self.saver:
            self.saver.write('light', dict(state=self.ON))
        self.is_on = True
    def off(self):
        if not self.is_on:
            return

        self.daq.trigger(self.end_trig, clear=False)
        if self.saver:
            self.saver.write('light', dict(state=self.OFF))
        self.is_on = False
    def end(self):
        self.daq.release()
