import numpy as np
import logging, threading
from daq import DAQOut, Trigger
from util import now
import time

class LED(object):
    # used for digital control of an opto LED (contrast with Light class, used for analog control of 5mm LED)
    OFF,ON = 0,1
    def __init__(self, port='port0/line4', saver=None, name='led'):
        self.port = port
        self.saver = saver
        self.name = name

        self.daq = DAQOut(DAQOut.DIGITAL_OUT, ports=[self.port])
        self.trig = Trigger([1,1,1,1], dtype=np.uint8)
        self.end_trig = Trigger([0,0,0,0], dtype=np.uint8)
        self.trigs = {self.ON:self.trig, self.OFF:self.end_trig}

        self.state = self.OFF

    def _switch(self, state):
        if self.state == state:
            return
        self.daq.trigger(self.trigs[state], clear=False)
        self.state = state
        if self.saver:
            self.saver.write(self.name, dict(state=self.state))

    def on(self):
        self._switch(self.ON)
    def off(self):
        self._switch(self.OFF)
    
    def end(self):
        self.daq.release()
