# Imports
from __future__ import print_function
from hardware import DAQOut, PSEye
import os, sys, atexit, time, csv, threading
now,now2 = time.clock, time.time
import numpy as np
import settings

# Experiment class handles a single run of the experiment
class Experiment():

    def __init__(self, name='NONAME'):

        # Saving params
        self.save_dir = os.path.join(settings.save_dir, name)
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        data_filename = '{}_data.csv'
        cam_filename = '{}_video.h5'
        self.data_file = os.path.join(self.save_dir, data_filename)
        self.cam_file = os.path.join(self.save_dir, cam_filename)
        self.fieldnames = ['log_time','trial_idx','start_time','end_time','start_clock','end_clock','cs_ts0','cs_ts1','us_ts0','us_ts1','kind']

        # Initialize hardware
        self.cam = PSEye(save_name=self.cam_file, **settings.cam_params)
        self.daq = DAQOut(ports=settings.daq_ports)

        # Register events
        atexit.register(self.end)

        # Runtime vars
        self.kill_flag = False
        self.complete = False

    def run(self):
       
        # open data logging file
        self.df_handle = open(self.data_file)
        self.logger = csv.DictWriter(self.df_handle, fieldnames=self.fieldnames)
        self.logger.writeheader()

        # Run-start variable resets
        self.trial_idx = -1 # keep track of trial index
        self.stim_cycle_idx = 0
        self.cam.begin_saving()
        self.cam.set_flush(True)

        # Deliver trials until program is terminated
        while not self.kill_flag:
            self.deliver_trial()

        self.end()
    
    def send_stim(self, kind):
        if kind == settings.CS:
            t = (now(), now2())
            self.daq.go(settings.lines['cs'], 1)
            self.wait(settings.cs_duration)
            self.daq.go(settings.lines['cs'], 0)
            stim_time = [t,(-1,-1)]

        elif kind == settings.US:
            self.wait(settings.cs_duration) # for trial continuity
            t = (now(), now2())
            self.daq.go(settings.lines['us'], 1)
            self.wait(settings.us_duration)
            self.daq.go(settings.lines['us'], 0)
            stim_time = [(-1,-1),t]

        elif kind == settings.CSUS:
            t_cs = (now(), now2())
            self.daq.go(settings.lines['cs'], 1)
            self.wait(settings.cs_us_interval)
            t_us = (now(), now2())
            self.daq.go(settings.lines['us'], 1)
            self.wait(settings.us_duration) # assumes US ends before settings.CS does
            self.daq.go(settings.lines['us'], 0)
            self.wait(settings.cs_duration, t0=t_cs[0])
            self.daq.go(settings.lines['cs'], 0)
            stim_time = [t_cs,t_us]

        return stim_time

    def wait(self, dur, t0=None):
        if t0 is None:
            t0 = now()
        while now()-t0 < dur:
            pass
    
    def next_kind(self, inc=True):
        st = settings.stim_cycle[self.stim_cycle_idx]
        if inc:
            self.stim_cycle_idx += 1
            if self.stim_cycle_idx == len(settings.stim_cycle):
                self.stim_cycle_idx = 0
        return st

    def deliver_trial(self):
        start_clock = now()
        start_time = now2()

        self.trial_idx += 1
        kind = self.next_kind()
        self.cam.set_flush(False)

        self.wait(settings.cs_onset)
        cs_time,us_time = self.send_stim(kind)

        end_clock = now()
        end_time = now2()
        self.cam.set_flush(True)

        # log trial info
        trial_dict = dict(
                            start_time  = start_time,
                            start_clock = start_clock,
                            end_time    = trial_off,
                            end_clock   = end_clock,
                            cs_ts0      = cs_time[0],
                            cs_ts1      = cs_time[1],
                            us_ts0      = us_time[0],
                            us_ts1      = us_time[1],
                            kind        = kind,
                            trial_idx   = self.trial_idx,
        )
        self.logger.writerow(trial_dict)

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

        self.complete = True

if __name__ == '__main__':
    name = ''
    while not name.isalnum():
        name = raw_input('Enter a unique experiment name: ')
        name = name.lower()

    print('Now running experiment:\t', name)

    exp = Experiment(name=name)
    threading.thread(target=exp.run).start()

    stop = input('Hit enter to stop experiment.')
    exp.kill_flag = True

    print('Experiment ending...')
    while exp.complete is False:
        continue
    print('Experiment {} complete.'.format(name))
