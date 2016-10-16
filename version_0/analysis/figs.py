from soup.classic import *
import matplotlib.pyplot as pl
import os, h5py
from skimage import exposure

def get_cr(e):
    #baseline = e.ix[:pad[0]]
    #thresh = baseline.min() + baseline.std()
    aoi = e.ix[pad[0]:pad[0]+0.250]
    return aoi.max()
    #return aoi.max() > thresh

cr_thresh = 0.15
pad = np.array((2.,2.))

path = '/Users/ben/data/eyeblink/'
files = sorted([p for p in os.listdir(path) if p.endswith('_series.pd')])
skipsesh = 2
files = files[skipsesh:]

pl.style.use('classic')
fig,axs = pl.subplots(3,4, sharex=True, sharey=True, figsize=(16,9)); axs=axs.ravel()
fig2,axs2 = pl.subplots(3,4, sharex=True, sharey=True, figsize=(16,9)); axs2=axs2.ravel()

patches = [None,None]

for idx,(f,ax,ax2) in enumerate(zip(files,axs,axs2)):
    sesh = f[:f.index('_')]
    eyelid,dff,proj_ = pd.read_pickle(os.path.join(path,f))

    dff[dff>5] = 0

    cr = eyelid.apply(get_cr, axis=0)
    cridx = np.argwhere(cr>cr_thresh).squeeze()

    #eyelid = eyelid.iloc[:,cridx]
    #dff = dff.iloc[:,cridx]

    emean = eyelid.mean(axis=1)
    eerr = eyelid.std(axis=1)
    eyelid.plot(ax=ax, alpha=0.1, color='gray')
    #ax.fill_between(emean.index, emean.values-eerr.values, emean.values+eerr.values, color='k', alpha=0.2)
    emean.plot(color='k', label='eyelid', ax=ax, linewidth=3)
    patches[0] = ax.get_lines()[-1]
    dmean = dff.mean(axis=1)
    derr = dff.std(axis=1)
    #ax.fill_between(dmean.index, dmean.values-derr.values, dmean.values+derr.values, color='m', alpha=0.2)
    dff.plot(ax=ax, alpha=0.1, color='m')
    dmean.plot(color='m', label=r'$\Delta F/F$', ax=ax, linewidth=3)
    patches[1] = ax.get_lines()[-1]

    ax.vlines([pad[0], pad[0]+.250], 0, 1, linestyles='--', colors='gray')
    ax.annotate(s='CS', xy=[pad[0], 1.05], ha='center')
    ax.annotate(s='US', xy=[pad[0]+0.250, 1.05], ha='center')
    ax.set_xlabel('Time (s)')
    ax.set_xlim(pad[0]-0.2, pad[0]+.850)
    ax.set_ylim([-0.1, 1.2])
    ax.set_xticklabels(map(str,ax.get_xticks()-pad[0]))
    ax.set_title('Session {}'.format(idx+1+1+skipsesh))

    pretty(ax=ax)

    proj = (proj_-proj_.min())/(proj_.max()-proj_.min())
    proj = exposure.equalize_adapthist(proj, clip_limit=0.025)
    ax2.imshow(proj, cmap=pl.cm.Greys_r, vmin=0, vmax=1)
    ax2.axis('off')
    ax2.set_title('Session {}'.format(idx+1+1+skipsesh))

pl.figure(fig.number)
pl.figlegend(patches, ['~eyelid', 'FOV ∆F/F'], loc='upper left', fontsize='large', ncol=1)
pl.savefig(os.path.join(path, 'summary.pdf'))
pl.figure(fig2.number)
pl.savefig(os.path.join(path, 'summary2.pdf'))
