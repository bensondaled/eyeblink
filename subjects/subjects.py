import numpy as np
import pandas as pd
import os, sys, h5py, time, logging
pjoin = os.path.join
import config

def list_subjects():
    #subs = [d for d in os.listdir(data_path) if os.path.isdir(pjoin(data_path,d))]
    #return subs
    if not os.path.exists(config.datafile):
        return []
    with pd.HDFStore(config.datafile) as f:
        if 'trials' not in f:
            return []
        return f.trials.subj.unique().astype(int).astype(str)

def list_rewards():
    today = time.strftime('%Y%m%d')
    if not os.path.exists(config.datafile):
        return {}
    with pd.HDFStore(config.datafile) as f:
        if 'trials' not in f:
            return {}
        tr = f.trials
        ses = tr.session
        dates = ses.map('{:0.0f}'.format).str[:8]
        tr = tr[dates==today]
        res = {}
        for subn in tr.subj.unique():
            res[str(int(subn))] = np.sum(tr[tr.subj==subn].reward != False)
    return res
    print '%s: %i (%i uL)\t-->\tGive %i uL'%(s,r,r*4,1000-r*4)

class Subject(object):
    def __init__(self, name, data_path='./data'):
        # name check
        try:
            int(name)
        except:
            raise Exception('Subject name must be an integer')
        self.num = int(name)
        self.name = str(self.num)

        # directory
        self.subj_dir = os.path.abspath(pjoin(data_path, self.name))
        if not os.path.exists(self.subj_dir):
            os.mkdir(self.subj_dir)
            #print 'New subject \"%s\" created.'%self.name
        elif os.path.exists(self.subj_dir):
            pass
            #print 'Loaded subject \"%s\".'%self.name
    def __json__(self):
        return dict(name=self.name, path=self.subj_dir)
