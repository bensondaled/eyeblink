import numpy as np
import pandas as pd
import time, threading, os, logging, json, multiprocessing
from hardware import AnalogReader, PSEye, NI845x
from saver import Saver
from util import now, now2
from settings.constants import *
pjoin = os.path.join

class Session(object):

    def __init__(self, session_params):
        # incorporate kwargs
        self.params = session_params
        self.__dict__.update(self.params)
        self.verify_params()

        # sync
        self.sync_flag = multiprocessing.Value('b', False)
        self.sync_to_save = multiprocessing.Queue()

        # saver
        self.saver = Saver(self.subj, self.name, self, sync_flag=self.sync_flag)

        # hardware
        self.cam = PSEye(sync_flag=self.sync_flag, **self.cam_params)
        self.ar = AnalogReader(saver_obj_buffer=self.saver.buf, sync_flag=self.sync_flag, **self.ar_params)

        # communication
        self.ni = NI845x()

        # runtime variables
        self.notes = {}
        self.session_on = 0
        self.on = False
        self.session_complete = False
        self.session_kill = False
        self.trial_flag = False
        self.trial_on = 0
        self.trial_off = 0
        self.trial_idx = -1
        self.stim_cycle_idx = 0
        self.paused = False
        
        # sync
        self.sync_flag.value = True #trigger all processes to get time
        self.sync_val = now() #get this process's time
        procs = dict(saver=self.saver, cam=self.cam.pseye, ar=self.ar)
        sync_vals = {o:procs[o].sync_val.value for o in procs} #collect all process times
        sync_vals['session'] = self.sync_val
        self.sync_to_save.put(sync_vals)

    @property
    def session_runtime(self):
        if self.session_on != 0:
            return now()-self.session_on
        else:
            return -1
    @property
    def trial_runtime(self):
        if self.trial_on != 0:
            return now()-self.trial_on
        else:
            return -1
    def name_as_str(self):
        return self.name.strftime('%Y%m%d%H%M%S')

    def verify_params(self):
        if self.name is None:
            self.name = pd.datetime.now()
        self.cam_params.update(dict(save_name=pjoin(self.subj.subj_dir, self.name_as_str()+'_cams.h5')))

    def pause(self, val):
        self.paused = val

    def update_licked(self):
        l = self.ar.licked

    def start_acq(self):
        if self.imaging:
            self.ni.write_dio(LINE_SI_ON, 1)
            self.ni.write_dio(LINE_SI_ON, 0)
    def stop_acq(self):
        if self.imaging:
            self.ni.write_dio(LINE_SI_OFF, 1)
            self.ni.write_dio(LINE_SI_OFF, 0)

    def wait(self, dur, t0=now()):
        while now()-t0 < dur:
            pass

    def next_stim_type(self):
        st = self.cycle[self.stim_cycle_idx]
        self.stim_cycle_idx += 1
        if self.stim_cycle_idx == len(self.cycle):
            self.stim_cycle_idx = 0
        return st
                
    def deliver_trial(self):
        while self.on:
            if self.trial_flag:

                # prepare trial
                self.trial_idx += 1
                self.trial_flag = False
                self.trial_on = now()
                self.cam.set_flush(False)
                kind = self.next_stim_type()
           
                # deilver trial
                self.wait(self.intro)
                stim_time = self.send_stim(kind)
                self.wait(self.trial_duration, t0=self.trial_on)
                self.trial_off = now()

                # save trial info
                self.cam.set_flush(True)
                self.dataset_trials.resize(len(self.dataset_trials)+1, axis=0)
                cs_time,us_time = self.last_stim_time
                self.dataset_trials[-1,:] = np.array([self.last_start, self.trial_off, cs_time, us_time, kind])
    
    def dummy_puff(self):
        self.ni.write_dio(LINE_US, 1)
        self.wait(self.us_dur)
        self.ni.write_dio(LINE_US, 0)
    def dummy_light(self, state):
        self.ni.write_dio(LINE_CS, state)
    def send_stim(self, kind):
        if kind == CS:
            t = (now(), now2())
            self.ni.write_i2c('CS_ON')
            self.ni.write_dio(LINE_CS, 1)
            self.wait(self.cs_dur)
            self.ni.write_i2c('CS_OFF')
            self.ni.write_dio(LINE_CS, 0)
            stim_time = [t,-1]

        elif kind == US:
            self.wait(self.cs_dur) # for trial continuity
            t = (now(), now2())
            self.ni.write_i2c('US_ON')
            self.ni.write_dio(LINE_US, 1)
            self.wait(self.us_dur)
            self.ni.write_i2c('US_OFF')
            self.ni.write_dio(LINE_US, 0)
            stim_time = [-1,t]

        elif kind == CSUS:
            t_cs = (now(), now2())
            self.ni.write_i2c('CS_ON')
            self.ni.write_dio(LINE_CS, 1)
            self.wait(self.csus_gap)
            t_us = (now(), now2())
            self.ni.write_i2c('US_ON')
            self.ni.write_dio(LINE_US, 1)
            self.wait(self.us_dur) # assumes US ends before CS does
            self.ni.write_i2c('US_OFF')
            self.ni.write_dio(LINE_US, 0)
            self.wait(self.cs_dur, t0=t_cs[0])
            self.ni.write_i2c('CS_OFF')
            self.ni.write_dio(LINE_CS, 0)
            stim_time = [t_cs,t_us]

        return stim_time

    def run(self):
        try:

            self.session_on = now()
            self.on = True
            self.ar.begin_saving()
            self.cam.begin_saving()
            self.cam.set_flush(True)
            self.start_acq()
        
            # main loop
            threading.Thread(target=self.deliver_trial).start()
            while True:

                if self.trial_on:
                    continue

                if self.session_kill:
                    break
                
                moving = self.determine_motion()
                eyelid = self.determine_eyelid()

                if (now()-self.trial_off>self.min_iti) and (not moving) and (eyelid):
                    self.trial_flag = True

            self.end()

        except:
            logging.error('Session has encountered an error!')
            raise

    def determine_eyelid(self):
        pass
        #TODO: get camera input from eye camera, compute eyelid
    def determine_motion(self):
        pass #TODO
   
    def end(self):
        self.on = False
        self.stop_acq()
        to_end = [self.ar, self.cam]
        if self.imaging:
            to_end.append(self.ni)
        for te in to_end:
            te.end()
            time.sleep(0.100)
        self.saver.end(notes=self.notes)
        self.session_on = False
            
    def get_code(self):
        py_files = [pjoin(d,f) for d,_,fs in os.walk(os.getcwd()) for f in fs if f.endswith('.py') and not f.startswith('__')]
        code = {}
        for pf in py_files:
            with open(pf, 'r') as f:
                code[pf] = f.read()
        return json.dumps(code)
