import numpy as np
import pylab as pl
pl.ion()
import time, os
import cv2
from cameras import PSEye as Camera
from cameras import default_cam_params
now = time.clock

class Experiment():
    EYE, WHEEL = 0,1
    def __init__(self, name, animal, save_path=r'C:\Users\deverett\Desktop\dummydata'):

        self.name = name
        self.animal = animal
        self.base_path = save_path
        self.path = os.path.join(self.base_path, self.animal, self.name)
        self.data_filename = self.path + '_data.csv'
        
        # hardware
        cp1 = default_cam_params.copy()
        cp1.update(idx=1,frame_rate=60,query_rate=5,save_name=self.path+'_cam1')
        cp2 = default_cam_params.copy()
        cp2.update(idx=0,frame_rate=60,query_rate=5,save_name=self.path+'_cam2')
        self.cam1 = Camera(**cp1)
        self.cam2 = Camera(**cp2)
        self.cam1.set_save(True)
        self.cam2.set_save(True)
        self.set_flush(True)

        # params
        self.min_iti = 10.
        self.plot_n = 100.
        self.window_motion = 50.
        self.window_eye = 50.
        self.thresh_motion = 2.0
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
                self.deliver_trial(None)
                self.last_end = now()
                self.save_trial()
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
        pass
        print ('trial delivered')
        # this func will be a blocking call that tells cam to save then delivers stimuli
        # start cam saving
        # wait for some duration
        # trigger scanimage
        # wait for some duration
        # send stim 1
        # (possibly) wait for some duration
        # (possibly) send stim 2
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
        self.plot_line_eye, = self.ax.plot(np.zeros(self.plot_n))
        self.plot_line_wheel, = self.ax.plot(np.zeros(self.plot_n))
        self.ax.set_ylim([0,255])
        
        self.win1 = cv2.namedWindow('Camera1')
        self.win2 = cv2.namedWindow('Camera2')
    def end(self):
        self.cam1.end()
        self.cam2.end()
        cv2.destroyAllWindows()
        pl.close('all')
        self.data_file.close()
