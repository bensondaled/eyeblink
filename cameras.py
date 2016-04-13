from ctypes import c_int, c_void_p, c_char_p, c_float, c_uint16, c_uint32, c_uint8
from ctypes import Structure, byref
import cv2, os, time, json, sys, warnings, ctypes, logging, threading, h5py, Queue
import numpy as np
import multiprocessing as mp
now = time.clock
now2 = time.time
############ Constants ##############

# camera sensor parameters
CLEYE_AUTO_GAIN = 0 #[false, true]
CLEYE_GAIN = 1 #[0, 79]
CLEYE_AUTO_EXPOSURE = 2 #[false, true]
CLEYE_EXPOSURE = 3#[0, 511]
CLEYE_AUTO_WHITEBALANCE = 4 #[false, true]
CLEYE_WHITEBALANCE_RED = 5#[0, 255]
CLEYE_WHITEBALANCE_GREEN = 6#[0, 255]
CLEYE_WHITEBALANCE_BLUE = 7#[0, 255]
# camera linear transform parameters
CLEYE_HFLIP = 8#[false, true]
CLEYE_VFLIP = 9#[false, true]
CLEYE_HKEYSTONE = 0#[-500, 500]
CLEYE_VKEYSTONE = 0#[-500, 500]
CLEYE_XOFFSET = 0#[-500, 500]
CLEYE_YOFFSET = 0#[-500, 500]
CLEYE_ROTATION = 0#[-500, 500]
CLEYE_ZOOM = 0#[-500, 500]
# camera non-linear transform parameters
CLEYE_LENSCORRECTION1 = 16#[-500, 500]
CLEYE_LENSCORRECTION2 = 17#[-500, 500]
CLEYE_LENSCORRECTION3 = 18#[-500, 500]
CLEYE_LENSBRIGHTNESS = 19#[-500, 500]
#CLEyeCameraColorMode
CLEYE_GREYSCALE = 0
CLEYE_COLOR = 1
#CLEyeCameraResolution
CLEYE_QVGA = 0
CLEYE_VGA = 1

############# Special API Structures ################

class GUID(Structure):
    _fields_ = [("Data1", c_uint32),
             ("Data2", c_uint16),
             ("Data3", c_uint16),
             ("Data4", c_uint8 * 8)]
    def __str__(self):
        return "%X-%X-%X-%s" % (self.Data1, self.Data2, self.Data3, ''.join('%02X'%x for x in self.Data4))

def CLEyeCameraGetFrameDimensions(dll, cam):
    width = c_int()
    height = c_int()
    dll.CLEyeCameraGetFrameDimensions(cam, byref(width), byref(height))
    return width.value, height.value

def mp2np(a):
    return np.frombuffer(a.get_obj(), dtype=np.uint8)

class MovieSaver(mp.Process):
    def __init__(self, name, x, y, kill_flag, q, flushing, buffer_size=2000, hdf_resize=30000, min_flush=200):
        super(MovieSaver, self).__init__()
        self.daemon = True
        self.name = name
        self.x = x
        self.y = y
        self.frame_buffer = q
        self.flushing = flushing
        self.saving_complete = mp.Value('b', False)
        self.kill_flag = kill_flag
        self.buffer_size = buffer_size # should be overkill, since flushing will do the real job of saving it out
        self.hdf_resize = hdf_resize
        self.min_flush = min_flush
        
        # Queries
        self.query_flag = mp.Value('b',False)
        self.query_queue = mp.Array(ctypes.c_uint8, np.product([self.x, self.y]))
        
        self.start()
    def run(self):
        self.vw_f = h5py.File(self.name,'w')
        self.vw = self.vw_f.create_dataset('mov', (self.hdf_resize, self.y, self.x), maxshape=(None, self.y, self.x), dtype='uint8', compression='gzip', compression_opts=7)
        self.vwts = self.vw_f.create_dataset('ts', (self.hdf_resize,2), maxshape=(None,2), dtype=np.float64, compression='gzip', compression_opts=7)
            
        _sav_idx = 0
        _buf_idx = 0
        _saving_buf = np.empty((self.buffer_size,self.y,self.x), dtype=np.uint8)
        _saving_ts_buf = np.empty((self.buffer_size,2), dtype=np.float64)
        while True:
            #print self.frame_buffer.qsize()
            # extend dataset if needed:
            if self.vw.shape[0]-_sav_idx <= self.buffer_size:
                #print 'extending file'
                assert self.vw.shape[0] == self.vwts.shape[0]
                self.vw.resize((self.vw.shape[0]+self.hdf_resize, self.vw.shape[1], self.vw.shape[2]))
                self.vwts.resize((self.vwts.shape[0]+self.hdf_resize,self.vwts.shape[1]))
            
            if self.frame_buffer.empty() and self.kill_flag.value==True:
                #print 'breaking1'
                break
            try:
                ts,temp,saveb = self.frame_buffer.get(block=False)
            except Queue.Empty:
                if self.kill_flag.value:
                    #print 'breaking2'
                    break
                else:
                    continue
            
            if self.query_flag.value:
                self.query_queue[:] = temp
                self.query_flag.value = False
            
            if saveb:
                _saving_buf[_buf_idx] = temp.reshape([self.y, self.x])
                _saving_ts_buf[_buf_idx] = ts
                _buf_idx += 1
                if (self.flushing.value and _buf_idx>=self.min_flush) or _buf_idx == self.buffer_size:
                    if _buf_idx == self.buffer_size:
                        logging.warning('Dumping camera b/c reached max buffer')
                    #print 'dumping to file'
                    self.vw[_sav_idx:_sav_idx+_buf_idx,:,:] = _saving_buf[:_buf_idx]
                    self.vwts[_sav_idx:_sav_idx+_buf_idx,:] = _saving_ts_buf[:_buf_idx]
                    _sav_idx += _buf_idx
                    _buf_idx = 0
        self.vw[_sav_idx:_sav_idx+_buf_idx,:,:] = _saving_buf[:_buf_idx]
        self.vwts[_sav_idx:_sav_idx+_buf_idx] = _saving_ts_buf[:_buf_idx]
        _sav_idx += _buf_idx
        
        self.vw.resize([_sav_idx,self.vw.shape[1],self.vw.shape[2]])
        self.vwts.resize([_sav_idx,2])
        self.vw_f.close()
        self.saving_complete.value = True

class PSEye():
    def __init__(self, *args, **kwargs):
        self.kill_flag = mp.Value('b',False)
        self.frame_buffer = mp.Queue()
        self.saving = mp.Value('b', False)
        self.flushing = mp.Value('b', False)
        self.query_rate = kwargs.pop('query_rate')
        self.x,self.y = [_PSEye.DIMS_SMALL,_PSEye.DIMS_LARGE][[_PSEye.RES_SMALL,_PSEye.RES_LARGE].index(kwargs['resolution'])]
        self.frame_shape = [self.y,self.x]
        self.saver = MovieSaver(name=kwargs.pop('save_name')+'.h5', x=self.x, y=self.y, kill_flag=self.kill_flag, q=self.frame_buffer, flushing=self.flushing)
        self.pseye = _PSEye(*args, frame_buffer=self.frame_buffer, kill_flag=self.kill_flag, saving_flag=self.saving, **kwargs)
        #self.sleep = 2
        #time.sleep(self.sleep)
        self.last_query = now()            
    def get(self):
        if now()-self.last_query < 1./self.query_rate:
            return None
        self.last_query = now()
        self.saver.query_flag.value = True
        while self.saver.query_flag.value:
            pass
        fr = mp2np(self.saver.query_queue)
        return fr.reshape([self.y,self.x])

    def end(self):
        self.kill_flag.value = True
        while (not self.pseye.thread_complete.value) or (not self.saver.saving_complete.value):
            pass
    def set_save(self, val):
        self.saving.value = val
        
class _PSEye(mp.Process):

    RES_SMALL = CLEYE_QVGA
    RES_LARGE = CLEYE_VGA   
    available_framerates = dict(RES_LARGE=[15,30,40,50,60,75], RES_SMALL=[15,30,60,75,100,125])
    DIMS_SMALL = (320,240)
    DIMS_LARGE = (640,480)
    COLOR = CLEYE_COLOR
    GREYSCALE = CLEYE_GREYSCALE

    def __init__(self, idx, resolution, frame_rate, color_mode, vflip=False, hflip=False, gain=60, exposure=24, wbal_red=50, wbal_blue=50, wbal_green=50, auto_gain=0, auto_exposure=0, auto_wbal=0, zoom=0, save_name=None, ts_buffer=1000, sync_flag=None, frame_buffer=None, kill_flag=None, saving_flag=None):

        # Process init
        super(_PSEye, self).__init__()
        self.daemon = True

        # Saver
        self.frame_buffer=frame_buffer
        # Parent
        self.kill_flag = kill_flag
        self.saving_flag = saving_flag
        
        # Parameters
        self.idx = idx
        self.resolution_mode = resolution
        self.resolution = [self.DIMS_SMALL,self.DIMS_LARGE][[self.RES_SMALL,self.RES_LARGE].index(self.resolution_mode)]
        self.frame_rate = frame_rate
        self.color_mode = color_mode
        self.vflip = vflip
        self.hflip = hflip
        self.gain = gain
        self.exposure = exposure
        self.auto_gain = auto_gain
        self.auto_exposure = auto_exposure
        self.auto_wbal = auto_wbal
        self.zoom = zoom
        self.wbal_red,self.wbal_blue,self.wbal_green = wbal_red,wbal_blue,wbal_green
        self.read_dims = self.resolution[::-1]
        if self.color_mode == self.COLOR:
            self.read_dims.append(4)

        self.lib = "CLEyeMulticam.dll"
        
        self.settings = [   (CLEYE_AUTO_GAIN, self.auto_gain),
                            (CLEYE_AUTO_EXPOSURE, self.auto_exposure),
                            (CLEYE_AUTO_WHITEBALANCE,self.auto_wbal),
                            (CLEYE_GAIN, self.gain),
                            (CLEYE_EXPOSURE, self.exposure),
                            (CLEYE_WHITEBALANCE_RED,self.wbal_red),
                            (CLEYE_WHITEBALANCE_BLUE,self.wbal_blue),
                            (CLEYE_WHITEBALANCE_GREEN,self.wbal_green),
                            (CLEYE_VFLIP, self.vflip),
                            (CLEYE_HFLIP, self.hflip),
                            (CLEYE_ZOOM, self.zoom),
                 ]

        self.save_name = save_name
        self.ts_buffer = ts_buffer
        
        if self.color_mode == CLEYE_GREYSCALE:
            self.bytes_per_pixel = 1
        elif self.color_mode == CLEYE_COLOR:
            self.bytes_per_pixel = 4
        
        self.thread_complete = mp.Value('b',False)

        self.cS = mp.Array(ctypes.c_uint8, np.product(self.read_dims))
        self.ts = mp.Value('d',0)

        # Sync
        self.sync_flag = sync_flag
        self.sync_val = mp.Value('d', 0)

        
        self.start()

    def vid_name(self, i):
        return self.save_name+'.h5'
        return self.save_name+'_{:02}'.format(i)+'.avi'
    
    def get_frame(self, timeout=20000):
        if not self._cam:
            return [None,None,None]
            
        got = self.dll.CLEyeCameraGetFrame(self._cam, self._buf, timeout)
        ts,ts2 = now(),now2()
        return (got,ts,ts2)
    
    def configure(self, settings):
        if not self._cam:
            return
        for param, value in settings:
            self.dll.CLEyeSetCameraParameter(self._cam, param, value)

    def run(self):
        self._init_cam()
        
        # Sync with parent process, if applicable
        while (not self.sync_flag is None) and (not self.sync_flag.value):
            self.sync_val.value = now()
       
        # Main loop
        while True:
            if self.kill_flag.value:
                break
            changed_file, got = False, False
            got,ts,ts2 = self.get_frame()

            if got:
                fr = np.frombuffer(self._buf, dtype=np.uint8)
                self.frame_buffer.put([[ts,ts2],fr, self.saving_flag.value])
                    
        try:
            self.dll.CLEyeCameraStop(self._cam)
            self.dll.CLEyeDestroyCamera(self._cam)
        except:
            pass
        self.thread_complete.value = 1

    def _init_cam(self):
        # Load dynamic library
        self.dll = ctypes.cdll.LoadLibrary(self.lib)
        self.dll.CLEyeGetCameraUUID.restype = GUID
        self.dll.CLEyeCameraGetFrame.argtypes = [c_void_p, c_char_p, c_int]
        self.dll.CLEyeCreateCamera.argtypes = [GUID, c_int, c_int, c_float]
    
        #print self.dll.CLEyeGetCameraCount()
    
        self._cam = self.dll.CLEyeCreateCamera(self.dll.CLEyeGetCameraUUID(self.idx), self.color_mode, self.resolution_mode, self.frame_rate)
        if not self._cam:
            warnings.warn('Camera {} failed to initialize.'.format(self.idx))
            return
            
        self.x, self.y = CLEyeCameraGetFrameDimensions(self.dll, self._cam)
        self._buf = ctypes.create_string_buffer(self.x * self.y * self.bytes_per_pixel) 
        
        self.configure(self.settings)
        self.dll.CLEyeCameraStart(self._cam)
        time.sleep(0.01)
            

##################################################################################################

default_cam_params = dict(  idx=0, 
                            resolution=_PSEye.RES_SMALL, 
                            query_rate = 10,
                            frame_rate=60, 
                            color_mode=_PSEye.GREYSCALE,
                            auto_gain = True,
                            auto_exposure = True,
                            auto_wbal = True,
                            #gain = 10,
                            #exposure = 20,
                            wbal_red = 50,
                            wbal_blue = 50,
                            wbal_green = 50,
                            vflip = True,
                            hflip = True,
        )
            
if __name__ == '__main__':

    cam_params = default_cam_params.copy()
    cam_params.update(idx=1,frame_rate=60,query_rate=5,save_name=r'C:\Users\deverett\Desktop\test1')
    cam = PSEye(**cam_params)
    cam_params2 = default_cam_params.copy()
    cam_params2.update(idx=0, frame_rate=60, save_name=r'C:\Users\deverett\Desktop\test2')
    cam2 = PSEye(**cam_params2)
    
    cam.set_save(True)
    cam2.set_save(True)
    t0 = now()
    while now()-t0<10:
        fr = cam.get()
        fr2 = cam2.get()
        if fr is not None:
            cv2.imshow('Camera View', fr)
        if fr2 is not None:
            cv2.imshow('Camera View2', fr2)
        q = cv2.waitKey(1)
        if q == ord('q'):
            break
    cam.end()
    cam2.end()
    cv2.destroyAllWindows()
    
