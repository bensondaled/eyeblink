import pyfluo as pf, numpy as np
import os, sys

jobid = int(sys.argv[1])

gpath = '/jukebox/wang/deverett/2p/eyeblink/b38/'
tufs = sorted([t[:t.index('_')] for t in os.listdir(gpath) if t.endswith('tif')])
seshs = np.unique(tufs)

#OVERWRITE
seshs = ['20160726142746']

if jobid >= len(seshs):
    print 'extraneous job.'
    sys.exit(0)

sesh = seshs[jobid]
path = os.path.join(gpath, '{}*'.format(sesh))
print 'Now starting files with prefix: {}'.format(sesh);sys.stdout.flush()

path = os.path.join(gpath, '{}*'.format(sesh))
print(sesh)

try:

    tg = pf.images.TiffGroup(path)
    print 'Sending to hdf...';sys.stdout.flush()
    if os.path.exists(tg.hdf_path):
        os.remove(tg.hdf_path)
    tg.to_hdf5()

    d = pf.Data(tg.hdf_path)
    print 'Motion correcting...';sys.stdout.flush()
    d.motion_correct(overwrite=True)

    print 'Done {}.'.format(sesh)
except:
    print('error with {}'.format(sesh))
