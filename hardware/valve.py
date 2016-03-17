import numpy as np
import logging, threading
from daq import DAQOut, Trigger
from util import now
import time

def calibrate_spout(side, dur, n=25, delay=2.0):
    v = Valve()
    for i in xrange(n):
        v.go(side, dur)
        time.sleep(delay)
    v.end()

class Valve(object):
    # used for puff or water valves under digital control
    OPEN,CLOSE = 0,1
    def __init__(self, ports=['port0/line2','port0/line3'], saver=None, duration=[0.1,0.1], name='valve', force_next=True):
        self.ports = ports
        self.duration = duration
        self.saver = saver
        self.name = name
        self.is_open = [False for _ in ports]
        self.force_next = force_next #if a trigger is sent while open, close it and reopen it
        self.nlnr = [0,0]
        
        if type(self.duration) in [int, float]:
            self.duration = [self.duration for i in self.ports]

        self.daqs = [DAQOut(DAQOut.DIGITAL_OUT, ports=[port]) for port in self.ports]
        self.trig = Trigger([1,1,1,1], dtype=np.uint8)
        self.end_trig = Trigger([0,0,0,0], dtype=np.uint8)
    def get_nlnr(self):
        ret = self.nlnr
        self.nlnr = [0,0]
        return ret
    def _close(self, side):
        self.daqs[side].trigger(self.end_trig, clear=False)
        self.is_open[side] = False
        if self.saver:
            self.saver.write(self.name, dict(side=side, state=self.CLOSE))
    def _open(self, side):
        self.daqs[side].trigger(self.trig, clear=False)
        self.is_open[side] = True
        self.nlnr[side] += 1
        if self.saver:
            self.saver.write(self.name, dict(side=side, state=self.OPEN))

    def go(self, side, dur=None):
        if dur == None:
            dur = self.duration[int(side)]
        threading.Thread(target=self.hold_open, args=(int(side),dur)).start()

    def hold_open(self, side, dur):
        if self.is_open[side]:
            if self.force_next:
                self._close(side)
            elif not self.force_next:
                return
        self._open(side)
        start = now()
        while now()-start < dur:
            pass
        self._close(side)

    def end(self):
        for daq in self.daqs:
            daq.release()
