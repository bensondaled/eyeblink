import numpy as np
import pandas as pd
import matplotlib.pyplot as pl
import time, threading, os, logging, json, multiprocessing, cv2
from hardware import PSEye, DAQOut
from saver import Saver
from util import now, now2
from settings.constants import *
pjoin = os.path.join

class Session(object):

    def __init__(self, session_params, ax_interactive=None):
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
        self.ni = DAQOut(**self.daq_params)

        # interactivity
        self.ax_interactive = ax_interactive
        
        # runtime variables
        self.notes = {}
        self.mask_idx = -1 #for reselecting mask
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
        self.deliver_override = False
        self.roi_pts = None
        self.eyelid_buffer = np.zeros(self.eyelid_buffer_size)-1
        self.eyelid_buffer_ts = np.zeros(self.eyelid_buffer_size)-1
        self.past_flag = False
        
        # sync
        self.sync_flag.value = True #trigger all processes to get time
        self.sync_val = now() #get this process's time
        procs = dict(saver=self.saver, cam=self.cam.pseye)
        sync_vals = {o:procs[o].sync_val.value for o in procs} #collect all process times
        sync_vals['session'] = self.sync_val
        self.sync_to_save.put(sync_vals)
        
        # more runtime, anything that must occur after sync
        _,self.im = self.cam.get()
        

    @property
    def session_runtime(self):
        if self.session_on != 0:
            return now()-self.session_on
        else:
            return -1
    @property
    def trial_runtime(self):
        if self.trial_on != False:
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

    def wait(self, dur, t0=None):
        if t0 is None:
            t0 = now()
        while now()-t0 < dur:
            pass

    def next_stim_type(self, inc=True):
        st = self.cycle[self.stim_cycle_idx]
        if inc:
            self.stim_cycle_idx += 1
            if self.stim_cycle_idx == len(self.cycle):
                self.stim_cycle_idx = 0
        return st
        
    @property
    def current_stim_state(self):
        return STIM_TYPES[self.cycle[self.stim_cycle_idx]]
        
    def deliver_trial(self):
        while self.on:
            if self.trial_flag:

                # prepare trial
                self.trial_idx += 1
                self.trial_on = now()
                self.cam.set_flush(False)
                kind = self.next_stim_type()
           
                # deilver trial
                self.wait(self.intro)
                cs_time,us_time = self.send_stim(kind)
                
                # replay
                self.wait(self.display_lag)
                self.past_flag = [cs_time[1], us_time[1]]
                
                # finish trial
                self.wait(self.trial_duration, t0=self.trial_on)
                self.trial_off = now()

                # save trial info
                self.cam.set_flush(True)
                
                trial_dict = dict(\
                start   = self.trial_on,\
                end     = self.trial_off,\
                cs_ts0  = cs_time[0],\
                cs_ts1  = cs_time[1],\
                us_ts0  = us_time[0],\
                us_ts1  = us_time[1],\
                kind    = kind,\
                idx     = self.trial_idx,\
                )
                self.saver.write('trials',trial_dict)
                
                self.trial_flag = False
                self.trial_on = False
    
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
            stim_time = [t,(-1,-1)]

        elif kind == US:
            self.wait(self.cs_dur) # for trial continuity
            t = (now(), now2())
            self.ni.write_i2c('US_ON')
            self.ni.write_dio(LINE_US, 1)
            self.wait(self.us_dur)
            self.ni.write_i2c('US_OFF')
            self.ni.write_dio(LINE_US, 0)
            stim_time = [(-1,-1),t]

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

    def acquire_mask(self):
        x,y = self.cam.resolution[0]
        if self.roi_pts is None:
            self.roi_pts = [[0,0],[x,0],[x,y],[0,y]]
            logging.warning('No ROI found, using default')
        self.mask_idx += 1
        pts_eye = np.array(self.roi_pts, dtype=np.int32)
        mask_eye = np.zeros([y,x], dtype=np.int32)
        cv2.fillConvexPoly(mask_eye, pts_eye, (1,1,1), lineType=cv2.LINE_AA)
        self.mask = mask_eye
        self.mask_flat = self.mask.reshape((1,-1))
        self.saver.write('mask{}'.format(self.mask_idx), self.mask)
        logging.info('New mask set.')
        
    def run(self):
        try:
            self.acquire_mask()
            self.session_on = now()
            self.on = True
            self.ar.begin_saving()
            self.cam.begin_saving()
            self.cam.set_flush(True)
            self.start_acq()
        
            # main loop
            threading.Thread(target=self.deliver_trial).start()
            threading.Thread(target=self.update_eyelid).start()
            while True:

                if self.trial_on or self.paused:
                    continue

                if self.session_kill:
                    break
                
                moving = self.determine_motion()
                eyelid = self.determine_eyelid()
                
                if self.deliver_override or ((now()-self.trial_off>self.min_iti) and (not moving) and (eyelid)):
                    self.trial_flag = True
                    self.deliver_override = False

            self.end()

        except:
            logging.error('Session has encountered an error!')
            raise
    def determine_eyelid(self):
        return np.mean(self.eyelid_buffer[-self.eyelid_window:]) < self.eyelid_thresh
    def update_eyelid(self):
        while self.on:
            imts,im = self.cam.get()
            if im is None:
                continue
            self.im = im
            roi_data = self.extract(self.im)
            self.eyelid_buffer = np.roll(self.eyelid_buffer, -1)
            self.eyelid_buffer_ts = np.roll(self.eyelid_buffer_ts, -1)
            self.eyelid_buffer[-1] = roi_data
            self.eyelid_buffer_ts[-1] = imts
    def extract(self, fr):
        if fr is None:
            return 0
        flat = fr.reshape((1,-1)).T
        dp = (self.mask_flat.dot(flat)).T
        return np.squeeze(dp/self.mask_flat.sum(axis=-1))
    def determine_motion(self):
        return self.ar.moving
   
    def end(self):
        self.on = False
        self.stop_acq()
        to_end = [self.cam, self.ni]
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
