import numpy as np
import pandas as pd
import time, threading, os, logging, csv, json, multiprocessing
from hardware import AnalogReader, Valve, PSEye, default_cam_params
from trials import TrialHandler
from saver import Saver
from util import now
import config
pjoin = os.path.join

class Session(object):

    PHASE_ITI, PHASE_STIM = 0,1
    DEFAULT_PARAMS = {}

    def __init__(self, session_params):
        self.params = self.DEFAULT_PARAMS

        # incorporate kwargs
        self.params.update(session_params)
        self.__dict__.update(self.params)
        self.verify_params()

        # hardware
        self.cam = PSEye(**self.cam_params)
        self.cs_puffer = Valve(**self.stimulator_params)
        self.us_puffer = Valve(**self.stimulator_params)

        # trials
        self.th = TrialHandler(**self.trial_params)

        # runtime variables
        self.notes = {}
        self.session_on = 0
        self.session_complete = False
        self.session_kill = False
        self.session_runtime = -1
        self.paused = 0

    def verify_params(self):
        if self.name is None:
            self.name = pd.datetime.now()
        self.cam_params.update(dict(save_name=pjoin(self.subj.subj_dir, self.name.strftime('%Y%m%d%H%M%S'))))

    def stimulate(self):
        n = len(self.th.trt)
        t0 = now()
        while self.current_phase == self.PHASE_STIM and self.stim_idx < n:
            dt = now() - t0
            if dt >= self.th.trt['time'][self.stim_idx]:
                #logging.debug(dt-self.th.trt['time'][self.stim_idx])
                self.stimulator.go(self.th.trt['side'][self.stim_idx])
                self.stim_idx += 1
        
    def to_phase(self, ph):
        self.current_phase = ph

        self.current_phase_duration = self.phase_durations[ph] #intended phase duration

        self.phase_start = now()

        # Trial ending logic
        if ph == self.PHASE_END:
            pass

    def run_phase(self):
        ph = self.current_phase
        ph_dur = self.current_phase_duration
        dt_phase = now() - self.phase_start
        self.session_runtime = now() - self.session_on

        # Intro
        if ph == self.PHASE_ITI:
            pass
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_STIM)
                return
            
        # Stim
        elif ph == self.PHASE_STIM:
             
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_DELAY)
                return
            
            if not self.stimulated:
                threading.Thread(target=self.stimulate).start()
                self.stimulated = True

    def next_trial(self):
        
        self.th.next_trial()
       
        # Phase reset
        self.current_phase = self.PHASE_INTRO
        self.current_phase_duration = self.phase_durations[self.PHASE_INTRO]
        self.phase_start = now()
        _=self.ar.licked # to clear any residual signal
        
        # Trial-specific runtime vars
        self.licks = np.zeros((2000,),dtype=[('phase',int),('ts',float),('side',int)])
        self.lick_idx = 0

        # Event trackers
        self.stimulated = False
        self.trial_kill = False

        while self.current_phase != self.PHASE_END:
            self.run_phase()
       
        # Return value indicating whether another trial is appropriate
        if self.session_kill:
            self.paused = False
            return False
        else:
            return True
    
    def run(self):
        try:
            self.session_on = now()
            self.cam.SAVING.value = 1

            cont = True
            while cont:
                cont = self.next_trial()

            self.end()
        except:
            logging.error('Session has encountered an error!')
            raise
   
    def end(self):
        to_end = [self.stimulator, self.light, self.cam1, self.cam2]
        for te in to_end:
            te.end()
            time.sleep(0.100)
        self.session_on = False
