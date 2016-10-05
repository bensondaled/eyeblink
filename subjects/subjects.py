import numpy as np
import pandas as pd
import os, sys, h5py, time, logging
pjoin = os.path.join
import config

def list_subjects():
    subs = [d for d in os.listdir('./data') if os.path.isdir(pjoin('./data',d))]
    return subs

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
        elif os.path.exists(self.subj_dir):
            pass

    def __json__(self):
        return dict(name=self.name, path=self.subj_dir)
