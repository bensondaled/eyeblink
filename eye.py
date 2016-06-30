from soup.classic import *
from skimage.morphology import watershed
from skimage.filters import sobel
from skimage.measure import approximate_polygon, perimeter
from skimage.morphology import dilation
from skimage.measure import find_contours
from skimage.feature import canny
from skimage.filters import threshold_otsu
from skimage.transform import hough_ellipse
from skimage.draw import ellipse_perimeter
from scipy.ndimage import binary_fill_holes
from scipy.ndimage import label
from skimage.exposure import equalize_adapthist as clahe
import h5py

dat = h5py.File('20160521115131_data.h5', 'r')
roi = np.asarray(dat['roi'])[0]
mins,maxs = np.argwhere(roi).min(axis=0),np.argwhere(roi).max(axis=0)
roicent = np.argwhere(roi).mean(axis=0).astype(int)
mins-=5
maxs+=5
crop = [slice(None,None), slice(mins[0], maxs[0]), slice(mins[1], maxs[1])]

mov = np.load('cam2.91.npy')
mov = np.squeeze(mov[crop])
#mov = np.asarray([sobel(i) for i in mov])
mov = pf.Movie(mov, Ts=1/60)
thh = np.random.random(size=2)
# 0.82 0.39, 0.51 0.79
thh = [0.93, 0.71]
th = np.percentile(mov, thh)
movorig = mov.copy()
#mov = mov[420:450]

fig,axs = pl.subplots(2,2); axs=axs.ravel()
i0 = axs[0].imshow(mov[0], vmin=mov.min(), vmax=mov.max())
i1 = axs[1].imshow(mov[0], vmin=0, vmax=1)
i2 = axs[2].imshow(mov[0], vmin=0, vmax=1)
i3 = axs[3].imshow(mov[0], vmin=0, vmax=1)

imcent = np.asarray(mov[0].shape)/2

roicent -= mins
roicrop = roi[crop[1],crop[2]]
roii = np.where(roicrop)
roinoti = np.where(roicrop==0)
darkval = movorig[:,roii[0],roii[1]]
liteval = movorig[:,roinoti[0],roinoti[1]]
dark = np.percentile(liteval, 8)

values = []


for im in mov:
    edges = canny(im, sigma=0.5, low_threshold=np.min(thh), high_threshold=np.max(thh), use_quantiles=True)
    edges = dilation(edges, np.ones([2,2]))

    contours = find_contours(edges, 0)
    ccent = np.asarray([i.mean(axis=0) for i in contours])
    cont = contours[np.argmin(np.sqrt(np.sum((ccent-imcent)**2)))]
    contim = np.zeros(im.shape)
    contidx = cont.astype(int)
    contidx = contidx.T
    contim[contidx[0], contidx[1]] = 1
    
    black = (im<=dark).astype(int)
    lab,nl = label(black)
    cents = np.asarray([np.argwhere(lab==i).mean(axis=0) for i in range(1,nl+1)])
    dist = [ np.sqrt(np.sum((imcent-i)**2)) for i in cents]
    eyeidx = np.argmin(dist)+1
    eye = lab==eyeidx
   
    """
    i0.set_data(im)
    i1.set_data(edges)
    i2.set_data(contim)
    i3.set_data(eye)
    pl.draw()
    pl.pause(0.0001)
    """

    values.append(eye.sum())
    #values.append(np.mean(im[roicrop]))
