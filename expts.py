import numpy as np
import pylab as pl
pl.ion()
import time, os
import cv2
from cameras import PSEye as Camera
from cameras import default_cam_params
now = time.clock
from ni845x import NI845x

class Experiment():
    EYE, WHEEL = 0,1
    CS,US,CSUS = 0,1,2
    LINE_SI, LINE_CS, LINE_US = 0,1,2
    def __init__(self, name, animal, save_path=r'C:\Users\deverett\Desktop\dummydata'):

        self.name = name
        self.animal = animal
        self.base_path = save_path
        self.path = os.path.join(self.base_path, self.animal, self.name)
        self.data_filename = self.path + '_data.csv'
        
        # hardware
        
        # TODO!!! Include sync value for cameras
        cp1 = default_cam_params.copy()
        cp1.update(idx=1,frame_rate=60,query_rate=5,save_name=self.path+'_cam1')
        cp2 = default_cam_params.copy()
        cp2.update(idx=0,frame_rate=60,query_rate=5,save_name=self.path+'_cam2')
        self.cam1 = Camera(**cp1)
        self.cam2 = Camera(**cp2)
        self.cam1.set_save(True)
        self.cam2.set_save(True)
        self.set_flush(True)
        self.ni = NI845x()

        # trial params
        self.trial_duration = 6.0
        self.cs_dur = 0.100
        self.us_dur = 0.100
        self.csus_gap = 0.100
        self.intro = 1.0
        
        # params
        self.min_iti = 10.
        self.plot_n = 100.
        self.window_motion = 50.
        self.window_eye = 50.
        self.thresh_wheel = 2.0
        self.thresh_eye = 2.0

    def run(self):

        self.data_file = open(self.data_filename, 'a')

        self.acquire_masks()
        self.setup_panels()
        
        # runtime vars
        saving = False
        self.last_start = now()
        self.last_end = now()
        self.last_type = now()
        self.last_sitrig = now()
        self.data_eye = np.zeros(self.plot_n)-1
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
    def determine_motion(self):
        if -1 in self.data_wheel:
            return True
        return np.std(self.data_wheel[-self.window_motion:]) > self.thresh_motion
    def determine_eyelid(self):
        return np.mean(self.data_eye[-self.window_eye:]) > self.thresh_eye
    def deliver_trial(self, stim):
        self.ni.write_dio(self.LINE_SI)
        self.cam.set_save(True)
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
        self.cam.set_save(False)
        self.t0 = None
        return stim_time
    def send_cs(self):
        self.ni.write_dio(self.LINE_CS, 1)
        t0 = now()
        while now()-t0 < self.cs_dur:
            pass
        self.ni.write_dio(self.LINE_CS, 0)
        return t0
    def send_us(self):
        self.ni.write_dio(self.LINE_US, 1)
        t0 = now()
        while now()-t0 < self.us_dur:
            pass
        self.ni.write_dio(self.LINE_US, 0)
        return t0
    def send_csus(self):
        self.ni.write_dio(self.LINE_CS, 1)
        t0 = now()
        while now()-t0 < self.csus_gap:
            pass
        self.ni.write_dio(self.LINE_US, 1)
        t1 = now()
        while now()-t0 < self.cs_dur:
            pass
        self.ni.write_dio(self.LINE_CS, 0)
        while now()-t1 < self.us_dur: ## NOTE! This assumes CS finishes before US. if not, change this
            pass
        self.ni.write_dio(self.LINE_US, 0)
        return [t0,t1]
    def save_trial(self):
        pass
        # this func will save all details about a trial (start time, end time, stim type, scanimage trigger time,)
        #self.data_file.write('{:0.15f},{:0.15f},{},{:0.15f}'.format(self.last_start, self.last_end, self.last_type, self.last_sitrig))
    def update(self):
        # this func will only be run when trials are not on. will update displays and params, etc
        fr1 = self.cam1.get()
        fr2 = self.cam2.get()
        
        if fr1 is not None:
            cv2.imshow('Camera1', fr1)
            roi_data = self.extract(fr1)
            self.data_eye = np.roll(self.data_eye, -1)
            self.data_wheel = np.roll(self.data_wheel, -1)
            self.data_eye[-1] = roi_data[self.EYE]
            self.data_wheel[-1] = roi_data[self.WHEEL]
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
        self.ax.set_ylim([0,255])
        
        self.win1 = cv2.namedWindow('Camera1')
        self.win2 = cv2.namedWindow('Camera2')
    def end(self):
        self.cam1.end()
        self.cam2.end()
        self.ni.end()
        cv2.destroyAllWindows()
        pl.close('all')
        self.data_file.close()
