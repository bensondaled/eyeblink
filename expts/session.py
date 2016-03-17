import numpy as np
import pandas as pd
import time, threading, os, logging, csv, json, multiprocessing
from hardware import AnalogReader, Valve, Light, PSEye, Speaker, default_cam_params, LED
from settings.manipulations import *
from trials import TrialHandler
from saver import Saver
from util import now
import config
pjoin = os.path.join

class Session(object):

    L,R = 0,1
    COR,INCOR,EARLY,NULL,KILLED = 1,0,2,3,4
    PHASE_INTRO, PHASE_STIM, PHASE_DELAY, PHASE_LICK, PHASE_REWARD, PHASE_ITI, PHASE_END = 0,1,2,3,4,5,6
    DEFAULT_PARAMS = {}

    def __init__(self, session_params):
        self.params = self.DEFAULT_PARAMS

        # incorporate kwargs
        self.params.update(session_params)
        self.__dict__.update(self.params)
        self.verify_params()

        # saver
        self.saver = Saver(self.subj, self.name, self)

        # hardware
        self.init_camera()
        self.ar = AnalogReader(saver_obj_buffer=self.saver.buf, **self.ar_params)
        self.stimulator = Valve(saver=self.saver, name='stimulator', **self.stimulator_params)
        self.spout = Valve(saver=self.saver, name='spout', **self.spout_params)
        self.light = Light(saver=self.saver, **self.light_params)
        self.opto_led = LED(saver=self.saver, **self.opto_led_params)
        self.speaker = Speaker(saver=self.saver)

        # trials
        self.th = TrialHandler(saver=self.saver, condition=self.condition, **self.trial_params)

        # runtime variables
        self.stdinerr = None
        self.notes = {}
        self.session_on = 0
        self.session_complete = False
        self.session_kill = False
        self.session_runtime = -1
        self.trial_runtime = -1
        self.rewards_given = 0
        self.paused = 0
        self.holding = False

    def verify_params(self):
        if self.name is None:
            self.name = pd.datetime.now()
        self.cam_params.update(dict(save_name=pjoin(self.subj.subj_dir, self.name.strftime('%Y%m%d%H%M%S'))))

    def init_camera(self):
        def update_sync(sync, dur=10.):
            t0 = now()
            while now()-t0 < dur:
                sync.value = now()

        syncobj = multiprocessing.Value('d',0)
        threading.Thread(target=update_sync, args=(syncobj,)).start()
        try: # this will not catch most exceptions, since theyll happen in a new process
            self.cam = PSEye(clock_sync_obj=syncobj, **self.cam_params)
            self.cam.start()
        except:
            logging.error('Camera failed to initialize.')
            raise

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
        # Write last phase
        phase_info = dict(  trial = self.th.idx, 
                            phase = self.current_phase,
                            start_time = self.phase_start, 
                            end_time = now(),
                         )
        self.saver.write('phases',phase_info)

        self.current_phase = ph

        # determine duration
        if self.current_phase==self.PHASE_STIM:
            self.current_phase_duration = self.th.phase_dur
        elif self.current_phase==self.PHASE_DELAY:
            self.current_phase_duration = self.th.delay_dur
        else:
            self.current_phase_duration = self.phase_durations[ph] #intended phase duration

        self.phase_start = now()
        self.last_hint = now()

        # Flush saving buffer
        if ph in [self.PHASE_ITI, self.PHASE_END] and not self.flushed:
            self.flushed = True
            #self.saver.flush()
        if ph in [self.PHASE_ITI]:
            self.cam.flush.value = 1
        else:
            self.cam.flush.value = 0

        # Opto LED : based on constants defined in manipulations.py
        if self.th.manip == MANIP_NONE:
            self.opto_led.off()
        elif self.th.manip == MANIP_PAN and self.current_phase!=self.PHASE_ITI:
            self.opto_led.on()
        elif self.th.manip == MANIP_ACC and self.current_phase==self.PHASE_STIM:
            self.opto_led.on()
        elif self.th.manip == MANIP_INTROACC and (self.current_phase==self.PHASE_STIM or self.current_phase==self.PHASE_INTRO):
            self.opto_led.on()
        elif self.th.manip == MANIP_DELAY and self.current_phase==self.PHASE_DELAY:
            self.opto_led.on()
        elif self.th.manip == MANIP_REW and self.current_phase==self.PHASE_REWARD:
            self.opto_led.on()
        else:
            self.opto_led.off()

        # Trial ending logic
        if ph == self.PHASE_END:
            lpl = self.licks[self.licks['phase']==self.PHASE_LICK] #lick phase licks

            # sanity check. should have been rewarded only if solely licked on correct side
            if self.th.rule_side and self.th.rule_phase and (not self.licked_early) and (not self.th.rule_fault) and self.use_trials:
                assert bool(self.rewarded) == (any(lpl['side']==self.th.trial.side) and not any(lpl['side']==-self.th.trial.side+1))
            
            # determine trial outcome
            if not self.use_trials:
                if any(lpl):
                    outcome = self.COR
                else:
                    outcome = self.INCOR
            elif not self.th.rule_any:
                lprl = self.licks[(self.licks['phase']==self.PHASE_LICK) | (self.licks['phase']==self.PHASE_REWARD)]
                if not any(lprl):
                    outcome = self.NULL
                elif lprl[0]['side'] == self.th.trial.side:
                    outcome = self.COR
                else:
                    outcome = self.INCOR
            elif self.use_trials:
                if self.rewarded and self.th.rule_side and not self.th.rule_fault:
                    outcome = self.COR
                elif self.rewarded and ((not self.th.rule_side) or self.th.rule_fault):
                    if not any(lpl):
                        outcome = self.NULL
                    else:
                        if lpl[0]['side'] == self.th.trial.side:
                            outcome = self.COR
                        else:
                            outcome = self.INCOR
                elif self.trial_kill:
                    outcome = self.KILLED
                elif self.licked_early:
                    outcome = self.EARLY
                elif any(lpl['side']==-self.th.trial.side+1):
                    outcome = self.INCOR
                elif not any(lpl):
                    outcome = self.NULL
            # Save trial info
            nLnR = self.stimulator.get_nlnr()
            if config.TESTING_MODE:
                fake_outcome = np.random.choice([self.COR, self.INCOR, self.EARLY, self.NULL, self.KILLED], p=[0.5,0.3,0.15,0.04,0.01])
                self.th.end_trial(fake_outcome, -0.1*(fake_outcome==self.COR), nLnR)
                if fake_outcome == self.COR:
                    self.rewards_given += 1
            else:
                self.th.end_trial(outcome, self.rewarded, nLnR)

    def update_licked(self):
        l = self.ar.licked
        tst = now()
        for idx,li in enumerate(l):
            if li:
                try:
                    self.licks[self.lick_idx] = (self.current_phase, tst, idx)
                    self.lick_idx += 1
                except:
                    logging.error(self.licks)
                if self.lick_idx >= len(self.licks):
                    self.licks = self.licks.resize(len(self.licks)+2000)
                
        
        if self.hold_rule:
            if (not self.holding) and np.any(self.ar.holding):
                self.holding = True
                self.paused += 1
            elif self.holding and not np.any(self.ar.holding):
                self.paused = max(self.paused-1,0)
                self.holding = False
            if self.holding:
                self.speaker.pop()

            
    def run_phase(self):
        ph = self.current_phase
        ph_dur = self.current_phase_duration
        dt_phase = now() - self.phase_start
        self.session_runtime = now() - self.session_on
        self.trial_runtime = now() - self.th.trial.start
        self.update_licked()

        # special cases
        if ph == self.PHASE_ITI and not self.rewarded:
            ph_dur *= 1+self.penalty_iti_frac

        if self.paused and self.current_phase in [self.PHASE_INTRO,self.PHASE_STIM,self.PHASE_DELAY,self.PHASE_LICK]:
            self.trial_kill = True
            return

        if self.trial_kill and not self.current_phase==self.PHASE_ITI:
            self.to_phase(self.PHASE_ITI)
            return

        # Intro
        if ph == self.PHASE_INTRO:
            self.light.off()
            if not self.intro_signaled:
                self.speaker.intro()
                self.intro_signaled = True
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_STIM)
                return
            
        # Stim
        elif ph == self.PHASE_STIM:
            if self.th.rule_phase and any(self.licks['phase']==self.PHASE_STIM):
                self.licked_early = self.licks['ts'][0]
                self.to_phase(self.PHASE_ITI)
                return
            
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_DELAY)
                return
            
            if self.puffs_on and not self.stimulated:
                threading.Thread(target=self.stimulate).start()
                self.stimulated = True

        # Delay
        elif ph == self.PHASE_DELAY:
            if any(self.licks['phase']==self.PHASE_DELAY) and self.th.rule_phase:
                self.licked_early = self.licks['ts'][0]
                self.to_phase(self.PHASE_ITI)
                return
                    
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_LICK)
                return
                
            if self.th.rule_hint_delay and now()-self.last_hint > self.hint_interval:
                self.stimulator.go(self.th.trial.side)
                self.last_hint = now()
            
        # Lick
        elif ph == self.PHASE_LICK:
            self.light.on()
            
            #if not self.laser_signaled:
            #    self.speaker.laser()
            #    self.laser_signaled = True
            
            if not self.th.rule_any:
                self.to_phase(self.PHASE_REWARD)
                return

            if any(self.licks['phase'] == self.PHASE_LICK) and not self.th.rule_fault:
                self.to_phase(self.PHASE_REWARD)
                return
            elif any(self.licks['phase'] == self.PHASE_LICK) and self.th.rule_fault and any(self.licks[(self.licks['phase']==self.PHASE_LICK) & (self.licks['side']==self.th.trial.side)]):
                self.to_phase(self.PHASE_REWARD)
                return
            
            # if time is up, to reward phase
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_REWARD)
                return

        # Reward
        elif ph == self.PHASE_REWARD:
            self.light.on() #probably redundant
            
            if self.th.rule_side and any(self.licks[(self.licks['phase']==self.PHASE_LICK) & (self.licks['side']==-self.th.trial.side+1)]) and not self.rewarded and not self.th.rule_fault:
                self.speaker.wrong()
                self.to_phase(self.PHASE_ITI)
                return
        
            # sanity check. cannot reach here if any incorrect licks, ensure that:
            if self.th.rule_side and not self.th.rule_fault:
                assert (not any(self.licks[(self.licks['phase']==self.PHASE_LICK)&(self.licks['side']==-self.th.trial.side+1)]))
        
            # if no licks at all, go straight to ITI
            if self.th.rule_any and not any(self.licks[self.licks['phase']==self.PHASE_LICK]):
                self.to_phase(self.PHASE_ITI)
                return
            
            # if allowed multiple choices but only licked wrong side
            if self.th.rule_any and self.th.rule_fault and not any(self.licks[(self.licks['phase']==self.PHASE_LICK) & (self.licks['side']==self.th.trial.side)]):
                self.to_phase(self.PHASE_ITI)
                return

            # sanity check. can only reach here if licked correct side only
            if self.th.rule_any and self.th.rule_side:
                assert any(self.licks[(self.licks['side']==self.th.trial.side)&(self.licks['phase']==self.PHASE_LICK)])
     
            # from this point on, it is assumed that rewarding should occur. 
            if self.use_trials:
                rside = self.th.trial.side
            else:
                rside = (self.licks[self.licks['phase']==self.PHASE_LICK].side)[0]
                
            if self.rewards_on and not self.rewarded:
                self.spout.go(side=rside)
                self.rewarded = now()
                self.rewards_given += 1
                
            if self.th.rule_hint_reward and now()-self.last_hint > self.hint_interval:
                self.stimulator.go(self.th.trial.side)
                self.last_hint = now()

            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_ITI)
        # ITI
        elif ph == self.PHASE_ITI:
            self.light.off()
            
            if any((self.licks['phase']>self.PHASE_INTRO) & (self.licks['phase']<self.PHASE_LICK)) and self.th.rule_phase and not self.error_signaled:
                self.speaker.error()
                self.error_signaled = True
        
            if dt_phase >= ph_dur:
                self.to_phase(self.PHASE_END)
                return
                    
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
        self.stim_idx = 0
        self.rewarded = False
        self.error_signaled = False
        self.laser_signaled = False
        self.intro_signaled = False
        self.stimulated = False
        self.licked_early = False
        self.trial_kill = False
        self.flushed = False
        self.last_hint = -1

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
            self.ar.begin_saving()
            self.cam.SAVING.value = 1

            cont = True
            while cont:
                cont = self.next_trial()

            self.end()
        except:
            logging.error('Session has encountered an error!')
            raise
   
    def end(self):
        to_end = [self.ar, self.stimulator, self.spout, self.light, self.opto_led, self.cam]
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
