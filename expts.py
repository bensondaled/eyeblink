import numpy as np
import pylab as pl
pl.ion()
import time, os
import cv2, json, h5py, threading
import multiprocessing as mp
from cameras import PSEye as Camera
from cameras import default_cam_params
now = time.clock
from ni845x import NI845x

STIM_ON = True

class Experiment():
    EYE, WHEEL = 0,1
    CS,US,CSUS = 0,1,2
    LINE_SI_ON, LINE_SI_OFF, LINE_CS, LINE_US = 3,4,0,1
    def __init__(self, name, animal, save_path=r'C:\Users\deverett\Desktop\dummydata'):

        self.name = name
        self.animal = animal
        self.base_path = save_path
        self.path = os.path.join(self.base_path, self.animal, self.name)
        self.data_filename = self.path + '_data.h5'
        
        # hardware
        sync_flag = mp.Value('b', False)
        cp1 = default_cam_params.copy()
        cp1.update(idx=1,frame_rate=60,query_rate=5,save_name=self.path+'_cam1', sync_flag=sync_flag, rotation=0)
        cp2 = default_cam_params.copy()
        cp2.update(idx=0,frame_rate=60,query_rate=12,save_name=self.path+'_cam2', sync_flag=sync_flag, rotation=0)
        self.cam1 = Camera(**cp1)
        time.sleep(1)
        self.cam2 = Camera(**cp2)
        self.cam1.set_save(False)
        self.cam2.set_save(False)
        self.set_flush(False)
        self.ni = NI845x()
        
        time.sleep(4.0)
        sync_flag.value = True
        self.sync_val = now()

        # trial params
        self.trial_duration = 9.0
        self.cs_dur = 0.500
        self.us_dur = 0.030
        self.csus_gap = 0.250
        self.intro = 4.0
        
        # params
        self.min_iti = 1.0
        self.plot_n = 100.
        self.window_motion = 10.
        self.window_eye = 10.
        self.thresh_wheel = 4
        self.thresh_eye = 2

    def run(self):

        self.data_file = h5py.File(self.data_filename)
        self.dataset_sync = self.data_file.create_dataset('sync', data=[self.sync_val, self.cam1.pseye.sync_val.value, self.cam2.pseye.sync_val.value])
        self.dataset_sync.attrs['keys'] = ['main','cam1','cam2']
        self.dataset_trials = self.data_file.create_dataset('trials', [0,5], maxshape=[None,5], dtype=np.float64)
        self.dataset_trials.attrs['trial_types'] = ['CS','US','CSUS']
        self.dataset_trials.attrs['keys'] = ['start','end','cs','us','type']
        
        mask = self.acquire_masks()
        self.dataset_roi = self.data_file.create_dataset('roi', data=mask)
        self.setup_panels()
        
        # runtime vars
        self.on = True
        self.done = False
        saving = False
        self.trial_on = False
        self.last_start = now()
        self.trial_flag = False
        self.last_end = now()
        self.last_stim_time = None
        self.data_eye = np.zeros(self.plot_n)-1
        self.data_rawwheel = np.zeros(self.plot_n)-1
        self.data_wheel = np.zeros(self.plot_n)-1
        q = 0
        self.stim_cycle = 6*[self.CSUS] + [self.US] + 6*[self.CSUS] + [self.CS] + 3*[self.CSUS] + [self.US] + 3*[self.CSUS]
        self.stim_cycle_idx = 0
        threading.Thread(target=self.deliver_trial).start()
        
        # main loop
        while q!=ord('q'):
            
            dt = now() - self.last_end
            moving = self.determine_motion()
            eyelid = self.determine_eyelid()

            if (not self.trial_on) and (dt>self.min_iti) and (not moving) and (eyelid):
                self.trial_flag = True
                
            self.update()
            q = cv2.waitKey(1)

        self.on = False
        self.end()
    
    def next_stim_type(self):
        st = self.stim_cycle[self.stim_cycle_idx]
        self.stim_cycle_idx += 1
        if self.stim_cycle_idx == len(self.stim_cycle):
            self.stim_cycle_idx = 0
        return st
    def play_store(self):
        s = None
        while s is None:
            s,t,tidx = self.cam2.get_store()
        #print s.shape
        #print t
        traces = np.array([self.extract(f) for f in s])
        self.ax2.clear()
        self.ax2.plot(t,traces[:,0])
        self.ax2.vlines(self.cstime_glob, 0, 255, linestyles='dashed')
        self.ax2.vlines(self.ustime_glob, 0, 255, linestyles='dashed')
        self.ax2.set_title('trial {} : {}'.format(tidx,['CS','US','CSUS'][self.last_kind]))
        self.ax2.set_xlim([self.cstime_glob-1.0, self.ustime_glob+2.0])
        self.ax2.set_ylim([traces[:,0].min(),traces[:,0].max()])
        #self.ax2.axis('tight')
        self.fig.canvas.draw()
        #for fr in s[::3]:
        #    cv2.imshow('Last trial', fr)
        #    cv2.waitKey(1)
        cv2.imshow('Last trial', s[::3].mean(axis=0))
        cv2.waitKey(1)
        self.trial_on = False
    def set_store(self, val):
        self.cam2.set_store(val)
    def set_flush(self,val):
        self.cam1.set_flush(val)
        self.cam2.set_flush(val)
    def next_file(self):
        self.cam1.next_file()
        self.cam2.next_file()
    def set_save(self,val):
        self.cam1.set_save(val)
        self.cam2.set_save(val)
    def determine_motion(self):
        return self.data_wheel[-1] > self.thresh_wheel
    def determine_eyelid(self):
        return np.mean(self.data_eye[-self.window_eye:]) < self.thresh_eye
    def deliver_trial(self):
        while self.on:
            if self.trial_flag:
                self.trial_flag = False
                self.trial_on = True
                #self.set_flush(False)
                self.last_start = now()
                kind = self.next_stim_type()
                stim = kind
            
                self.ni.write_dio(self.LINE_SI_ON, 1)
                self.ni.write_dio(self.LINE_SI_ON, 0)
                self.set_save(True)
                self.set_store(True)
                self.t0 = now()
                while now()-self.t0 < self.intro:
                    pass
                
                if stim == self.CS:
                    stim_time = self.send_cs()
                    stim_time = [stim_time,-1]
                elif stim==self.US:
                    stim_time = self.send_us()
                    stim_time = [-1,stim_time]
                elif stim==self.CSUS:
                    stim_time = self.send_csus()
                    
                while now()-self.t0 < self.trial_duration:
                    pass
                self.set_save(False)
                self.t0 = None
                self.ni.write_dio(self.LINE_SI_OFF, 1)
                self.ni.write_dio(self.LINE_SI_OFF, 0)
                self.last_stim_time = stim_time
                
                self.last_end = now()
                self.dataset_trials.resize(len(self.dataset_trials)+1, axis=0)
                cs_time,us_time = self.last_stim_time
                self.dataset_trials[-1,:] = np.array([self.last_start, self.last_end, cs_time, us_time, kind])
                self.last_kind = kind
                #self.set_flush(True)
                self.set_store(False)
                self.next_file()
                threading.Thread(target=self.play_store).start()
                #self.trial_on = False #if you start the play_store thread, comment this out
        self.done = True
    def send_cs(self):
        if STIM_ON:
            self.ni.write_i2c('CS_ON')
            self.ni.write_dio(self.LINE_CS, 1)
        self.cstime_glob = time.time()
        self.ustime_glob = time.time()
        t0 = now()
        while now()-t0 < self.cs_dur:
            pass
        if STIM_ON:
            self.ni.write_i2c('CS_OFF')
            self.ni.write_dio(self.LINE_CS, 0)
        return t0
    def send_us(self):
        if STIM_ON:
            self.ni.write_i2c('US_ON')
            self.ni.write_dio(self.LINE_US, 1)
        self.ustime_glob = time.time()
        self.cstime_glob = time.time()
        t0 = now()
        while now()-t0 < self.us_dur:
            pass
        if STIM_ON:
            self.ni.write_i2c('US_OFF')
            self.ni.write_dio(self.LINE_US, 0)
        return t0
    def send_csus(self):
        if STIM_ON:
            self.ni.write_i2c('CS_ON')
            self.ni.write_dio(self.LINE_CS, 1)
        self.cstime_glob = time.time()
        t0 = now()
        while now()-t0 < self.csus_gap:
            pass
        if STIM_ON:
            self.ni.write_i2c('US_ON')
            self.ni.write_dio(self.LINE_US, 1)
        self.ustime_glob = time.time()
        t1 = now()
        while now()-t1 < self.us_dur: ## NOTE! This assumes US finishes before CS. if not, change this
            pass
        if STIM_ON:
            self.ni.write_i2c('US_OFF')
            self.ni.write_dio(self.LINE_US, 0)
        while now()-t0 < self.cs_dur:
            pass
        if STIM_ON:
            self.ni.write_i2c('CS_OFF')
            self.ni.write_dio(self.LINE_CS, 0)

        return [t0,t1]
    def save_trial(self, dic):
        self.data_file.write('{}\n'.format(json.dumps(dic)))
    def update(self):
        if self.trial_on:
            return
            
        #fr1 = self.cam1.get()
        fr2 = None
        while fr2 is None:
            fr2 = self.cam2.get()
        
        if fr2 is not None:
            #fr2x = cv2.cvtColor(fr2, cv2.COLOR_GRAY2RGBA)
            #fr2x[self.mask.sum(axis=0).astype(bool),0] += 10
            #cv2.imshow('Camera2', fr2x)
            roi_data = self.extract(fr2)
            self.data_eye = np.roll(self.data_eye, -1)
            self.data_rawwheel = np.roll(self.data_rawwheel, -1)
            self.data_wheel = np.roll(self.data_wheel, -1)
            self.data_eye[-1] = roi_data[self.EYE]
            self.data_rawwheel[-1] = roi_data[self.WHEEL]
            self.data_wheel[-1] = 10*np.std(self.data_rawwheel[-self.window_motion:])
            self.plot_line_eye.set_ydata(self.data_eye)
            self.plot_line_wheel.set_ydata(self.data_wheel)
            self.fig.canvas.draw()
        #if fr1 is not None:
        #    cv2.imshow('Camera1', fr1)
            
            self.line_eyethresh.set_ydata(self.thresh_eye)
            self.line_wheelthresh.set_ydata(self.thresh_wheel)
        
    def extract(self, fr):
        flat = fr.reshape((1,-1)).T
        dp = (self.mask_flat.dot(flat)).T
        return np.squeeze(dp/self.mask_flat.sum(axis=-1))
    def acquire_masks(self):
        im1 = self.cam2.get()
        pl.imshow(im1, cmap='gray')
        pl.title('Select Eye')
        pts_eye = pl.ginput(n=0, timeout=0)
        pts_eye = np.array(pts_eye, dtype=np.int32)
        mask_eye = np.zeros(im1.shape, dtype=np.int32)
        cv2.fillConvexPoly(mask_eye, pts_eye, (1,1,1), lineType=cv2.LINE_AA)

        pl.clf()
        
        im2 = self.cam2.get()
        pl.imshow(im2, cmap='gray')
        pl.title('Select Wheel')
        pl.gcf().canvas.draw()
        pts_wheel = pl.ginput(n=0, timeout=0)
        pts_wheel = np.array(pts_wheel, dtype=np.int32)
        mask_wheel = np.zeros(im2.shape, dtype=np.int32)
        cv2.fillConvexPoly(mask_wheel, pts_wheel, (1,1,1), lineType=cv2.LINE_AA)

        pl.close()

        self.mask = np.array([mask_eye, mask_wheel])
        self.mask_flat = self.mask.reshape((2,-1))
        return self.mask
    def setup_panels(self):
        self.fig = pl.figure()
        self.ax = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.plot_line_eye, = self.ax.plot(np.zeros(self.plot_n), color='b')
        self.plot_line_wheel, = self.ax.plot(np.zeros(self.plot_n), color='g')
        self.line_eyethresh, = self.ax.plot([0, self.plot_n], [10,10], 'b--')
        self.line_wheelthresh, = self.ax.plot([0, self.plot_n], [10,10], 'g--')
        self.ax.set_ylim([-1,256])
        
        #self.win1 = cv2.namedWindow('Camera1')
        #self.win2 = cv2.namedWindow('Camera2')
        self.win3 = cv2.namedWindow('Last trial')
        self.win_ctrl = cv2.namedWindow('Controls', cv2.WINDOW_NORMAL)
        cv2.createTrackbar('thresh_eye', 'Controls', self.thresh_eye, 255, self._cb_eye)
        cv2.createTrackbar('thresh_wheel', 'Controls', self.thresh_wheel, 255, self._cb_wheel)
    def _cb_eye(self, pos):
        self.thresh_eye = pos
    def _cb_wheel(self, pos):
        self.thresh_wheel = pos
    def end(self):
        while not self.done:
            pass
        self.cam1.end()
        self.cam2.end()
        self.ni.end()
        cv2.destroyAllWindows()
        pl.close('all')
        self.data_file.close()
