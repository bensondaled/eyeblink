import numpy as np
import time
import cv2
now = time.clock

class Experiment():
    def __init__(self):

        # hardware
        self.cam1 = Camera()
        self.cam2 = Camera()
            
        # UI
        self.win1 = cv2.namedWindow('Camera1')
        self.win2 = cv2.namedWindow('Camera2')

        # params
        self.min_iti = 10.

    def run(self):
        
        # runtime vars
        saving = False
        last_end = now()
        q = 0
        
        # main loop
        while q!=ord('q'):
            
            dt = now()-last_end
            moving = self.determine_motion()
            eyelid = self.determine_eyelid()

            if (dt>self.min_iti) and (not moving) and (eyelid):
                self.deliver_trial()

            self.update()

            q = cv2.waitKey(1)

        self.end()
    def deliver_trial(self, stim):
        pass
        # this func will be a blocking call that tells cam to save then delivers stimuli
    def update(self):
        pass
        # this func will only be run when trials are not on. will update displays and params, etc
    def end(self):
        self.cam1.end()
        self.cam2.end()
        cv2.destroyAllWindows()
