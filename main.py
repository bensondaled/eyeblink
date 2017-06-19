# Imports
from __future__ import print_function
from hardware import DAQOut, Camera
import os, sys, atexit, time
import numpy as np
import settings

# Experiment class handles a single run of the experiment
class Experiment():

    def __init__(self, name='NONAME'):

        # Saving directories
        self.save_dir = os.path.join(settings.save_dir, name)
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        data_filename = '{}_data.csv'
        self.data_file = os.path.join(self.save_dir, data_filename)

        # Initialize hardware
        self.cam = Camera(**settings.cam_params)
        self.daq = DAQOut(ports=settings.daq_ports)

        # Register events
        atexit.register(self.end)

        # Runtime vars
        self.kill_flag = False

    def run(self):
        
        # Run initialization
        self.df_handle = open(self.data_file) # open data logging file
        self.trial_idx = 0 # keep track of trial index

        # Deliver trials until program is terminated
        while not self.kill_flag:
            self.deliver_trial()

    def deliver_trial(self):
        pass

    def end(self):
        try:
            self.df_handle.close()
        except:
            pass

        try:
            self.daq.end()
        except:
            pass

        try:
            self.cam.end()
        except:
            pass


if __name__ == '__main__':
    name = ''
    while not name.isalnum():
        name = raw_input('Enter a unique experiment name: ')
        name = name.lower()

    print('Now running experiment:\t', name)

    exp = Experiment(name=name)
    exp.run()
