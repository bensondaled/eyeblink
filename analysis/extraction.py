import pyfluo as pf, numpy as np, pandas as pd
import matplotlib.pyplot as pl
pl.ioff()
import os, h5py, sys

path = '/jukebox/wang/deverett/2p/eyeblink/b37/'
seshs = sorted([os.path.splitext(i)[0] for i in os.listdir(path) if 'cam' not in i and 'data' not in i and 'series' not in i and 'fig' not in i])

jobid = int(sys.argv[1])
if jobid >= len(seshs):
    print 'extraneous job.'
    sys.exit(0)

sesh = seshs[jobid]

if os.path.exists(os.path.join(path, sesh+'_fig.png')):
    print 'analysis already done for {}'.format(sesh)
    sys.exit(0)

print 'Running job {}: {}'.format(jobid, sesh)

img_path = os.path.join(path, sesh+'.h5')
mov_path = os.path.join(path, sesh+'_cam2.h5')
md_path = os.path.join(path, sesh+'_data.h5')
Ts_behav = 1./60
pad = np.array((2.,2.))
pad_behav = (pad/Ts_behav).astype(int)

d = pf.Data(img_path)
pad_img = (pad/d.Ts).astype(int)

if not d._has_motion_correction:
    print 'motion correction available for {}'.format(sesh)
    sys.exit(0)

with h5py.File(md_path) as md:
    roi = pf.ROI(np.asarray(md['roi'])[0])
    trials = pd.DataFrame(np.asarray(md['trials']), columns=[i.decode('utf8') for i in md['trials'].attrs['keys']])
    trial_types = np.asarray(md['trials'].attrs['trial_types'])

all_eyelid = []
all_dff = []
trials = trials[trials.type==2]

for tidx,t in trials.iterrows():
    print(tidx)

    # behaviour
    with h5py.File(mov_path) as mov_file:
        tmov = mov_file['trial_{}'.format(tidx+1)]
        mov = pf.Movie(np.asarray(tmov['mov']), Ts=Ts_behav)
        ts = np.asarray(tmov['ts'])[:,-1]
    i0 = np.argmin(np.abs(ts-t.cs))
    start,end = i0-pad_behav[0], i0+pad_behav[1]
    eyelid = mov[start:end].extract(roi)
    eyelid -= eyelid.values[0]
    all_eyelid.append(eyelid.values.squeeze())
    #axs[0].plot(eyelid)

    # imaging
    i0 = d.i2c[(d.i2c.file_idx==tidx) & (d.i2c.data=='CS_ON')].frame_idx.squeeze()
    start,end = i0-pad_img[0], i0+pad_img[1]
    start,end = [d.framei(start, tidx), d.framei(end, tidx)]
    fov_tr = d[start:end].mean(axis=(1,2))
    fov_dff = pf.compute_dff(pf.Series(fov_tr, Ts=d.Ts))
    all_dff.append(fov_dff.values.squeeze())
    #axs[1].plot(fov_dff)

    #pl.draw()
    #pl.pause(0.001)

eyelid = pf.Series(np.array(all_eyelid).T, index=eyelid.index).astype(float)
eyelid = (eyelid-eyelid.min())/(eyelid.max()-eyelid.min())
dff = pf.Series(np.array(all_dff).T, index=fov_dff.index)

proj = np.mean(d[::500], axis=0)
pd.to_pickle([eyelid,dff,proj], os.path.join(path,sesh+'_series.pd'))

fig,axs = pl.subplots(1,2); axs=axs.ravel()

emean = eyelid.mean(axis=1)
eerr = eyelid.std(axis=1)
axs[0].fill_between(emean.index, emean.values-eerr.values, emean.values+eerr.values, color='k', alpha=0.2)
emean.plot(color='k', label='eyelid', ax=axs[0])
dmean = dff.mean(axis=1)
derr = dff.std(axis=1)
axs[0].fill_between(dmean.index, dmean.values-derr.values, dmean.values+derr.values, color='m', alpha=0.2)
dmean.plot(color='m', label=r'$\Delta F/F$', ax=axs[0])

axs[0].vlines([pad[0], pad[0]+.250], 0, 1, linestyles='--', colors='gray')
axs[0].annotate(s='CS', xy=[pad[0], 1.05], ha='center')
axs[0].annotate(s='US', xy=[pad[0]+0.250, 1.05], ha='center')
axs[0].set_xlabel('Time (s)')
axs[0].legend(loc='best')

axs[1].imshow(proj)

pl.savefig(os.path.join(path, sesh+'_fig.png'))
