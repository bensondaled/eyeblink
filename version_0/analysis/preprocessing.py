import pyfluo as pf
import os, sys

jobid = int(sys.argv[1])

seshs = ['20160701113525']
gpath = '/jukebox/wang/agiovann/eyeblink2016/b37/'
if jobid >= len(seshs):
    print 'extraneous job.'
    sys.exit(0)

sesh = seshs[jobid]
path = os.path.join(gpath, '{}*'.format(sesh))
print 'Now starting file: {}'.format(sesh);sys.stdout.flush()

tg = pf.images.TiffGroup(path)
print 'Sending to hdf...';sys.stdout.flush()
tg.to_hdf5()

d = pf.Data(tg.hdf_path)
print 'Motion correcting...';sys.stdout.flush()
d.motion_correct(overwrite=True)

print 'Done {}.'.format(sesh)
