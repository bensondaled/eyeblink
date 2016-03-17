import numpy as np
from util import now
import pandas as pd
import logging
from settings.rules import *

class TrialHandler(object):
    L,R = 0,1
    COR,INCOR,EARLY,NULL,KILLED = 1,0,2,3,4

    def __init__(self, saver=None, levels=None, rate_sum=None, stim_duration=None, stim_phase_duration=None, delay_phase_duration=None, stim_phase_pad=None, min_isi=None, bias_correction=None, max_bias_correction=None, condition=None, n_previous_level=None):

        # Params
        self.saver = saver
        self.rate_sum = rate_sum
        self.stim_duration = stim_duration
        self.stim_phase_duration = stim_phase_duration # choices, probabilities
        self.delay_phase_duration = delay_phase_duration
        self.stim_phase_pad = stim_phase_pad
        self.min_isi = min_isi
        self.bias_correction = bias_correction
        self.max_bias_correction = max_bias_correction
        self.condition = condition
        self.n_previous_level = n_previous_level
       
        # Setup levels
        self.setup_levels(levels)

        # Storage
        self.trials = pd.DataFrame(columns=['idx','start','end','dur','ratio','nL','nR','nL_intended','nR_intended','side','condition','manipulation','outcome','reward','delay','rule','level'])
        self.trials_timing = pd.DataFrame(columns=['trial','side','time'])
        
        # Runtime vars
        self.history_glob = pd.DataFrame(columns=['perc','valid','perc_l','perc_r','valid_l','valid_r','outcome','side'])
        self.history_win = pd.DataFrame(columns=['perc','valid','perc_l','perc_r','valid_l','valid_r','outcome','side'])
        self.biases = [-1,-1]
        self.valid_idx = 0 # the current trial index, ignoring all trials that were invalid
        self.level_locked = False

    @property
    def trial(self):
        return self.trials.iloc[-1]

    @property
    def phase_dur(self):
        # Used to specify to a session how long it should allocate for the phase that presents this trial
        return self.trial.dur + np.sum(self.stim_phase_pad)

    @property
    def delay_dur(self):
        return self.trial.delay

    @property
    def idx(self):
        return len(self.trials)-1

    @property
    def rule_any(self):
        return rules[self.trial.rule][0]
    @property
    def rule_side(self):
        return rules[self.trial.rule][1]
    @property
    def rule_phase(self):
        return rules[self.trial.rule][2]
    @property
    def rule_fault(self):
        # answers: "am I allowed faults?"
        return rules[self.trial.rule][3]
    @property
    def rule_hint_delay(self):
        return rules[self.trial.rule][4]
    @property
    def rule_hint_reward(self):
        return rules[self.trial.rule][5]
    @property
    def manip(self):
        return self.trial.manipulation

    def setup_levels(self, levels):
        self.levels = levels
        self.in_intro = False

        self.past = self.saver.past_trials
        if self.past is not None:
            self.level = int(self.past.iloc[-1].level)
        else:
            self.level = 0
        templast = self.level
        if self.n_previous_level > 0 and self.level > 0:
            self.level -= 1
            self.in_intro = True
        logging.info('Last detected level: {}, starting on level {}.'.format(templast,self.level))

    def change_level(self, inc):
        if self.level_locked:
            logging.info('Level locked, no adjustment made.')
            return
        lev = self.level + inc
        if lev > len(self.levels)-1:
            lev = len(self.levels)-1
        if lev < 0:
            lev = 0
        self.level = lev
        self.in_intro = False
        logging.info('Manually changed to level {}.'.format(self.level))

    def update_level(self):
        if self.level_locked:
            return
            
        # if on last level:
        if self.level == len(self.levels)-1:
            return
            
        # at current level: gather all valid trials, all contiguous trials, and all valid contiguous trials
        allvtri = self.trials[(self.trials.outcome.isin([self.COR,self.INCOR])) & (self.trials.level==self.level)]
        most_recent_noncur_level = np.argwhere(self.trials.level != self.level).squeeze()
        if (not np.any(most_recent_noncur_level)) or len(most_recent_noncur_level) == 0:
            contig_tri = self.trials
        else:
            most_recent_noncur_level = most_recent_noncur_level[-1]
            contig_tri = self.trials.iloc[most_recent_noncur_level+1:]  # trials of contiguous level to most recent
        contig_vtri = contig_tri[contig_tri.outcome.isin([self.COR,self.INCOR])]
        
        if self.in_intro:
            cri = dict(win=self.n_previous_level, n=self.n_previous_level, perc=0, bias=1.0, valid=0)
        else:
            cri = self.levels[self.level]['criteria'] 
            if self.past is not None and len(self.past) and self.past.iloc[-1].level==self.level:
                allvtri = pd.concat([self.past, allvtri], ignore_index=True, axis=0)
        
        # check n requirement
        if len(allvtri) < cri['n']:
            return
            
        # check win requirement
        if len(contig_vtri) < cri['win']:
            return

        # window of trials to use for coming criteria
        win_alltri = contig_tri.iloc[-cri['win']:]
        win_valtri = contig_vtri.iloc[-cri['win']:] # window of valid trials

        # check % requirement
        pc = win_valtri.outcome.mean()
        if pc < cri['perc']:
            return

        # check bias requirement
        perc_l = win_valtri[win_valtri.side==self.L].outcome.mean()
        perc_r = win_valtri[win_valtri.side==self.R].outcome.mean()
        bi = np.array([perc_l,perc_r])
        bi /= np.sum(bi)
        if np.max(bi) > cri['bias']:
            return

        # check validity requirement
        val = win_alltri.outcome.isin([self.COR,self.INCOR]).mean()
        if val < cri['valid']:
            return

        # if all criteria passed:
        self.level += 1
        if self.in_intro:
            self.in_intro = False
        logging.info('Auto-advanced to level {}.'.format(self.level))

    def _next_ratio(self):
        ratio = self.levels[self.level]['ratio']
        if any([isinstance(ratio, dt) for dt in [float, int]]):
            return ratio
        elif isinstance(ratio, list):
            return np.random.choice(ratio)
    def _next_rule(self):
        return self.levels[self.level]['rule']
    def _next_manip(self):
        manip = self.levels[self.level]['manip']
        if any([isinstance(manip, i) for i in [float,int]]):
            return manip
        elif isinstance(manip, list):
            return np.random.choice(manip)

    def _next_side(self):
        rand = np.random.choice([self.L, self.R])

        # If bias correction is off
        if not self.bias_correction:
            return rand

        valid_trials = self.trials[self.trials['outcome'].isin([self.COR,self.INCOR])]

        # If not enough trials
        if np.sum(valid_trials['side']==self.L) < self.bias_correction or np.sum(valid_trials['side']==self.R) < self.bias_correction:
            return rand
        
        perc_l = np.mean(valid_trials[valid_trials['side']==self.L][-self.bias_correction:]['outcome'])
        perc_r = np.mean(valid_trials[valid_trials['side']==self.R][-self.bias_correction:]['outcome'])
        percs = np.array([perc_l,perc_r])
       
        # If no bias exists
        if perc_l==perc_r:
            self.biases = [0.5,0.5]
            return rand

        # Adjust to max correction if one side is 0
        if min(percs) == 0:
            percs[percs==0] = self.max_bias_correction*max(percs)
        self.biases = percs/np.sum(percs)
        
        return np.random.choice([self.L,self.R], p=self.biases[::-1])
    
    def _next_stimphase_dur(self):
        levdur = self.levels[self.level]['stim_phase_dur']
        if levdur is None:
            levdur = self.stim_phase_duration
        
        d = np.random.choice(levdur[0], p=levdur[1])
        return d
    def _next_delay(self):
        levdur = self.levels[self.level]['delay_phase_dur']
        if levdur is None:
            levdur = self.delay_phase_duration

        d = np.random.choice(levdur[0], p=levdur[1])
        return d
    def next_trial(self):
        side = self._next_side()
        self.update_level()
        ratio = self._next_ratio()
        rule = self._next_rule()
        manip = self._next_manip()
        dur = self._next_stimphase_dur() 
        delay = self._next_delay()

        self.trt,final_lam = self._generate_trial(side, ratio, dur)
        final_ratio = final_lam[self.R]/final_lam[self.L]
        panda_trt = pd.DataFrame(self.trt)
        panda_trt['trial'] = len(self.trials)
        self.saver.write('trials_timing', panda_trt)

        self.trials.loc[len(self.trials)] = pd.Series(dict(start=now(), ratio=final_ratio, side=side, dur=dur, nL_intended=np.sum(self.trt['side']==self.L), nR_intended=np.sum(self.trt['side']==self.R), condition=self.condition, idx=len(self.trials), delay=delay, rule=rule, level=float(self.level), manipulation=manip ))

    def end_trial(self, outcome, rew, nLnR):
        # Save trial
        self.trials.iloc[-1]['end'] = now()
        self.trials.iloc[-1]['outcome'] = outcome
        self.trials.iloc[-1]['reward'] = rew
        self.trials.iloc[-1]['nL'] = nLnR[self.L]
        self.trials.iloc[-1]['nR'] = nLnR[self.R]
        self.saver.write('trials',self.trials.iloc[-1].to_dict())

        if outcome in [self.COR,self.INCOR]:
            self.valid_idx += 1

        self.update_history()
    def update_history(self, win=15):    
        # GLOB
        ivalid = self.trials['outcome'].isin([self.COR,self.INCOR])
        if ivalid.sum() == 0:
            perc, perc_l, perc_r, valid, valid_l, valid_r = 0,0,0,0,0,0
        else:
            perc = self.trials.ix[ivalid]['outcome'].mean()
            perc_l = self.trials.ix[(ivalid) & (self.trials['side']==self.L)]['outcome'].mean()
            perc_r = self.trials.ix[(ivalid) & (self.trials['side']==self.R)]['outcome'].mean()
            valid = ivalid.mean()
            if (self.trials.side==self.L).sum() > 0:
                valid_l = ((ivalid) & (self.trials.side==self.L)).sum() / float((self.trials.side==self.L).sum())
            else:
                valid_l = np.nan
            if (self.trials.side==self.R).sum() > 0:
                valid_r = ((ivalid) & (self.trials.side==self.R)).sum() / float((self.trials.side==self.R).sum())
            else:
                valid_r = np.nan
        self.history_glob.loc[len(self.history_glob)] = pd.Series(dict(perc=perc, perc_l=perc_l, perc_r=perc_r, valid=valid, valid_l=valid_l, valid_r=valid_r, outcome=self.trials['outcome'].iloc[-1], side=self.trials['side'].iloc[-1]))
        
        # WIN
        if win>=len(self.trials):
            wtri = self.trials
        else:
            wtri = self.trials.iloc[-win:]
        ivalid = wtri['outcome'].isin([self.COR,self.INCOR])
        if ivalid.sum() == 0:
            perc, perc_l, perc_r, valid, valid_l, valid_r = 0,0,0,0,0,0
        else:
            perc = wtri.ix[ivalid]['outcome'].mean()
            perc_l = wtri.ix[(ivalid) & (wtri['side']==self.L)]['outcome'].mean()
            perc_r = wtri.ix[(ivalid) & (wtri['side']==self.R)]['outcome'].mean()
            valid = ivalid.mean()
            if (wtri.side==self.L).sum() > 0:
                valid_l = ((ivalid) & (wtri.side==self.L)).sum() / float((wtri.side==self.L).sum())
            else:
                valid_l = np.nan
            if (wtri.side==self.R).sum() > 0:
                valid_r = ((ivalid) & (wtri.side==self.R)).sum() / float((wtri.side==self.R).sum())
            else:
                valid_r = np.nan
        self.history_win.loc[len(self.history_win)] = pd.Series(dict(perc=perc, perc_l=perc_l, perc_r=perc_r, valid=valid, valid_l=valid_l, valid_r=valid_r, outcome=wtri['outcome'].iloc[-1], side=wtri['side'].iloc[-1]))
                
    def _generate_trial(self, side, ratio, dur):
        np.seterr(divide='ignore')

        # determine rate parameters for both sides
        lam = self.rate_sum/(ratio + 1)
        lam = np.array([lam, self.rate_sum-lam])
        assert np.sum(lam) == self.rate_sum
        assert lam[0]/lam[1]==ratio or lam[1]/lam[0]==ratio
        beta = 1./lam

        def generate_train(b,dur,isi):
            times = []
            while True:
                to_add = np.random.exponential(b)

                ## This is the simplest approach for enforcing inter-stimulus intervals, but can lead to non-randomness if rate_sum is too high relative to min_isi
                if to_add<isi:
                    to_add = isi

                if sum(times)+to_add >= dur-isi: #last "-isi" b/c added stereo stim at end
                    break

                times.append(to_add)
            return np.cumsum(times)

        # generate event times
        timesL,timesR = [],[]
        while len(timesL) == len(timesR):
            timesL,timesR = [generate_train(b,dur,self.min_isi) for b in beta]
        timesL,timesR = np.append(0,timesL),np.append(0,timesR) # first 2 puffs
        timesL,timesR = np.append(timesL,dur),np.append(timesR,dur) # last 2 puffs
        
        # build trial matrix
        sides = np.concatenate([np.zeros(len(timesL)), np.ones(len(timesR))])
        times = np.concatenate([timesL, timesR])
        trial = np.zeros(len(sides), dtype=[('side',int),('time',float)])
        trial['side'] = sides
        trial['time'] = times
        trial = trial[np.argsort(trial['time'])]
        if np.random.random()<0.5:
            trial[:2]['side'] = -trial[:2]['side']+1 # in case of systematic timing error, first one will be random
        if np.random.random()<0.5:
            trial[-2:]['side'] = -trial[-2:]['side']+1 # in case of systematic timing error, last one will be random

        # sanity checks
        assert np.all(trial['time']<=dur)
        assert np.all(np.round(np.diff(trial[trial['side']==0]['time']), 4) >= self.min_isi)
        assert np.all(np.round(np.diff(trial[trial['side']==1]['time']), 4) >= self.min_isi)

        # add intro
        trial['time'][2:] += self.stim_phase_pad[0]

        # construct trial object
        trial_obj = np.array(trial, dtype=[('side',int),('time',float)])

        # adjust for correct side
        curcor = np.round(np.mean(trial_obj['side']))
        if curcor != side:
            trial_obj['side'] = -trial_obj['side']+1
            lam = lam[::-1]

        # sanity checks
        assert np.all(trial_obj['time'][:2]==[0.,0.])
        assert np.all(trial_obj['time'][-2:]==[dur+self.stim_phase_pad[0],dur+self.stim_phase_pad[0]])

        return trial_obj,lam
    
    def get_cum_performance(self, n=None):
        cum = np.asarray(self.trial_outcomes)
            
        markers = cum.copy()
        if self.lick_rule_phase:
            ignore = [self.SKIPPED,self.EARLY,self.NULL,self.KILLED]
        else:
            ignore = [self.SKIPPED,self.NULL,self.KILLED]
        valid = np.array([c not in ignore for c in cum]).astype(bool)
        cum = cum==self.COR
        if n is None:
            cum = [np.mean([c for c,v in zip(cum[:i],valid[:i]) if v]) if np.any(valid[:i]) else 0. for i in xrange(1,len(cum)+1)] #cumulative
        else:
            cum = [np.mean([c for c,v in zip(cum[max([0,i-n]):i],valid[max([0,i-n]):i]) if v]) if np.any(valid[max([0,i-n]):i]) else 0. for i in xrange(1,len(cum)+1)] #cumulative
        return cum,markers,np.asarray(self.trial_corrects)
