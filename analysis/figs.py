from soup.classic import *
import matplotlib.pyplot as pl
import os, h5py

pad = np.array((2.,2.))

path = '/Users/ben/data/eyeblink/'
files = sorted([p for p in os.listdir(path) if p.endswith('_series.pd')])
skipsesh = 2
files = files[skipsesh:]

pl.style.use('classic')
fig,axs = pl.subplots(2,4, sharex=True, sharey=True, figsize=(16,9)); axs=axs.ravel()

for idx,(f,ax) in enumerate(zip(files,axs)):
    sesh = f[:f.index('_')]
    eyelid,dff,proj = pd.read_pickle(os.path.join(path,f))

    emean = eyelid.mean(axis=1)
    eerr = eyelid.std(axis=1)
    ax.fill_between(emean.index, emean.values-eerr.values, emean.values+eerr.values, color='k', alpha=0.2)
    emean.plot(color='k', label='eyelid', ax=ax)
    dmean = dff.mean(axis=1)
    derr = dff.std(axis=1)
    ax.fill_between(dmean.index, dmean.values-derr.values, dmean.values+derr.values, color='m', alpha=0.2)
    dmean.plot(color='m', label=r'$\Delta F/F$', ax=ax)

    ax.vlines([pad[0], pad[0]+.250], 0, 1, linestyles='--', colors='gray')
    ax.annotate(s='CS', xy=[pad[0], 1.05], ha='center')
    ax.annotate(s='US', xy=[pad[0]+0.250, 1.05], ha='center')
    ax.set_xlabel('Time (s)')
    ax.set_xlim(pad[0]-0.2, pad[0]+.850)
    ax.set_ylim([-0.1, 1.2])
    ax.set_xticklabels(map(str,ax.get_xticks()-pad[0]))
    ax.set_title('Session {}'.format(idx+1+skipsesh))

    pretty(ax=ax)

pl.figlegend(ax.get_lines()[-2:], ['~eyelid', '∆F/F'], loc='upper left', fontsize='large', ncol=1)
pl.savefig(os.path.join(path, 'summary.pdf'))
