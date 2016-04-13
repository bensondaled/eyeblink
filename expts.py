import numpy as np
import pylab as pl
pl.ion()
import time, os
import cv2, json
import multiprocessing as mp
from cameras import PSEye as Camera
from cameras import default_cam_params
now = time.clock
from ni845x import NI845x

class Experiment():
    EYE, WHEEL = 0,1
    CS,US,CSUS = 0,1,2
    LINE_SI_ON, LINE_SI_OFF, LINE_CS, LINE_US = 3,4,0,1
    def __init__(self, name, animal, save_path=r'C:\Users\deverett\Desktop\dummydata'):

        self.name = name
        self.animal = animal
        self.base_path = save_path
        self.path = os.path.join(self.base_path, self.animal, self.name)
        self.data_filename = self.path + '_data.csv'
        
        # hardware
        sync_flag = mp.Value('b', False)
        cp1 = default_cam_params.copy()
        cp1.update(idx=1,frame_rate=60,query_rate=5,save_name=self.path+'_cam1', sync_flag=sync_flag)
        cp2 = default_cam_params.copy()
        cp2.update(idx=0,frame_rate=60,query_rate=5,save_name=self.path+'_cam2', sync_flag=sync_flag)
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
        self.trial_duration = 6.0
        self.cs_dur = 1.0
        self.us_dur = 0.100
        self.csus_gap = 0.100
        self.intro = 1.0
        
        # params
        self.min_iti = 10.
        self.plot_n = 100.
        self.window_motion = 50.
        self.window_eye = 50.
        self.thresh_wheel = 2
        self.thresh_eye = 2

    def run(self):

        self.data_file = open(self.data_filename, 'a')
        self.data_file.write('main={:0.15f},cam1={:0.15f},cam2={:0.15f}\n'.format(self.sync_val, self.cam1.pseye.sync_val.value, self.cam2.pseye.sync_val.value))

        self.acquire_masks()
        self.setup_panels()
        
        # runtime vars
        saving = False
        self.last_start = now()
        self.last_end = now()
        self.data_eye = np.zeros(self.plot_n)-1
        self.data_rawwheel = np.zeros(self.plot_n)-1
        self.data_wheel = np.zeros(self.plot_n)-1
        q = 0
        
        # main loop
        while q!=ord('q'):
            
            dt = now() - self.last_end
            moving = self.determine_motion()
            eyelid = self.determine_eyelid()

            if (dt>self.min_iti) and (not moving) and (eyelid):
                self.set_flush(False)
                self.last_start = now()
                kind = np.random.choice([self.CS, self.US, self.CSUS])
                stim_time = self.deliver_trial(kind)
                self.last_end = now()
                self.save_trial(dict(start=self.last_start, end=self.last_end, stim=stim_time, kind=kind))
                self.set_flush(True)

            self.update()

            q = cv2.waitKey(1)

        self.end()

    def set_flush(self,val):
        self.cam1.flushing.value = val
        self.cam2.flushing.value = val
    def set_save(self,val):
        self.cam1.set_save(val)
        self.cam2.set_save(val)
    def determine_motion(self):
        return self.data_wheel[-1] > self.thresh_wheel
    def determine_eyelid(self):
        return np.mean(self.data_eye[-self.window_eye:]) > self.thresh_eye
    def deliver_trial(self, stim):
        self.ni.write_dio(self.LINE_SI_ON, 1)
        self.ni.write_dio(self.LINE_SI_ON, 0)
        self.set_save(True)
        self.t0 = now()
        while now()-self.t0 < self.intro:
            pass
        
        if stim == self.CS:
            stim_time = self.send_cs()
        elif stim==self.US:
            stim_time = self.send_us()
        elif stim==self.CSUS:
            stim_time = self.send_csus()
            
        while now()-self.t0 < self.trial_duration:
            pass
        self.set_save(False)
        self.t0 = None
        self.ni.write_dio(self.LINE_SI_OFF, 1)
        self.ni.write_dio(self.LINE_SI_OFF, 0)
        return stim_time
    def send_cs(self):
        self.ni.write_i2c('CS_ON')
        self.ni.write_dio(self.LINE_CS, 1)
        t0 = now()
        while now()-t0 < self.cs_dur:
            pass
        self.ni.write_i2c('CS_OFF')
        self.ni.write_dio(self.LINE_CS, 0)
        return t0
    def send_us(self):
        self.ni.write_i2c('US_ON')
        self.ni.write_dio(self.LINE_US, 1)
        t0 = now()
        while now()-t0 < self.us_dur:
            pass
        self.ni.write_i2c('US_OFF')
        self.ni.write_dio(self.LINE_US, 0)
        return t0
    def send_csus(self):
        self.ni.write_i2c('CS_ON')
        self.ni.write_dio(self.LINE_CS, 1)
        t0 = now()
        while now()-t0 < self.csus_gap:
            pass
        self.ni.write_i2c('US_ON')
        self.ni.write_dio(self.LINE_US, 1)
        t1 = now()
        while now()-t0 < self.cs_dur:
            pass
        self.ni.write_i2c('CS_OFF')
        self.ni.write_dio(self.LINE_CS, 0)
        while now()-t1 < self.us_dur: ## NOTE! This assumes CS finishes before US. if not, change this
            pass
        self.ni.write_i2c('US_OFF')
        self.ni.write_dio(self.LINE_US, 0)
        return [t0,t1]
    def save_trial(self, dic):
        self.data_file.write('{}\n'.format(json.dumps(dic)))
    def update(self):
        # this func will only be run when trials are not on. will update displays and params, etc
        fr1 = self.cam1.get()
        fr2 = self.cam2.get()
        
        if fr1 is not None:
            cv2.imshow('Camera1', fr1)
            roi_data = self.extract(fr1)
            self.data_eye = np.roll(self.data_eye, -1)
            self.data_rawwheel = np.roll(self.data_rawwheel, -1)
            self.data_wheel = np.roll(self.data_wheel, -1)
            self.data_eye[-1] = roi_data[self.EYE]
            self.data_rawwheel[-1] = roi_data[self.WHEEL]
            self.data_wheel[-1] = np.std(self.data_rawwheel[-self.window_motion:])
            self.plot_line_eye.set_ydata(self.data_eye)
            self.plot_line_wheel.set_ydata(self.data_wheel)
            self.fig.canvas.draw()
        if fr2 is not None:
            cv2.imshow('Camera2', fr2)
            
        self.line_eyethresh.set_ydata(self.thresh_eye)
        self.line_wheelthresh.set_ydata(self.thresh_wheel)
        
    def extract(self, fr):
        flat = fr.reshape((1,-1)).T
        dp = (self.mask_flat.dot(flat)).T
        return np.squeeze(dp/self.mask_flat.sum(axis=-1))
    def acquire_masks(self):
        im1 = self.cam1.get()
        pl.imshow(im1, cmap='gray')
        pl.title('Select Eye')
        pts_eye = pl.ginput(n=0, timeout=0)
        pts_eye = np.array(pts_eye, dtype=np.int32)
        mask_eye = np.zeros(im1.shape, dtype=np.int32)
        cv2.fillConvexPoly(mask_eye, pts_eye, (1,1,1), lineType=cv2.LINE_AA)

        pl.clf()
        
        im2 = self.cam1.get()
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
    def setup_panels(self):
        self.fig = pl.figure()
        self.ax = self.fig.add_subplot(111)
        self.plot_line_eye, = self.ax.plot(np.zeros(self.plot_n), color='b')
        self.plot_line_wheel, = self.ax.plot(np.zeros(self.plot_n), color='g')
        self.line_eyethresh, = self.ax.plot([0, self.plot_n], [10,10], 'b--')
        self.line_wheelthresh, = self.ax.plot([0, self.plot_n], [10,10], 'g--')
        self.ax.set_ylim([-1,256])
        
        self.win1 = cv2.namedWindow('Camera1')
        self.win2 = cv2.namedWindow('Camera2')
        self.win_ctrl = cv2.namedWindow('Controls')
        cv2.createTrackbar('thresh_eye', 'Controls', self.thresh_eye, 255, self._cb_eye)
        cv2.createTrackbar('thresh_wheel', 'Controls', self.thresh_wheel, 255, self._cb_wheel)
    def _cb_eye(self, pos):
        self.thresh_eye = pos
    def _cb_wheel(self, pos):
        self.thresh_wheel = pos
    def end(self):
        self.cam1.end()
        self.cam2.end()
        self.ni.end()
        cv2.destroyAllWindows()
        pl.close('all')
        self.data_file.close()
