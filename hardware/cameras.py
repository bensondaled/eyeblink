from config import TESTING_MODE

if TESTING_MODE:
    from dummy import PSEye, default_cam_params

elif not TESTING_MODE:

    ### MULTICAM SECTION ###
    from ctypes import c_int, c_void_p, c_char_p, c_float, c_uint16, c_uint32, c_uint8
    from ctypes import Structure, byref
    import ctypes
    import warnings

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
    CLEYE_HKEYSTONE = 10#[-500, 500]
    CLEYE_VKEYSTONE = 11#[-500, 500]
    CLEYE_XOFFSET = 12#[-500, 500]
    CLEYE_YOFFSET = 13#[-500, 500]
    CLEYE_ROTATION = 14#[-500, 500]
    CLEYE_ZOOM = 15#[-500, 500]
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

    class GUID(Structure):
        _fields_ = [("Data1", c_uint32),
                 ("Data2", c_uint16),
                 ("Data3", c_uint16),
                 ("Data4", ctypes.c_uint8 * 8)]
        def __str__(self):
            return "%X-%X-%X-%s" % (self.Data1, self.Data2, self.Data3, ''.join('%02X'%x for x in self.Data4))

    def CLEyeCameraGetFrameDimensions(dll, cam):
        width = c_int()
        height = c_int()
        dll.CLEyeCameraGetFrameDimensions(cam, byref(width), byref(height))
        return width.value, height.value

        
    class Ps3Eye():
        def __init__(self, index, color_mode, resolution_mode, fps, dll=None):
            self.dll = dll
            self.cam = self.dll.CLEyeCreateCamera(self.dll.CLEyeGetCameraUUID(index), color_mode, resolution_mode, fps)
            if not self.cam:
                warnings.warn('Camera failed to initialize')
                return
            if color_mode == CLEYE_GREYSCALE:
                self.bytes_per_pixel = 1
            elif color_mode == CLEYE_COLOR:
                self.bytes_per_pixel = 4
            self.x, self.y = CLEyeCameraGetFrameDimensions(self.dll,self.cam)
            
        def configure(self, settings):
            if not self.cam:
                return
            for param, value in settings:
                self.dll.CLEyeSetCameraParameter(self.cam, param, value)
                
        def start(self):
            if not self.cam:
                return
            return self.dll.CLEyeCameraStart(self.cam)
        
        def stop(self):
            if not self.cam:
                return
            return self.dll.CLEyeCameraStop(self.cam)
            
        def get_frame(self, buffer=None, timeout=200):
            if not self.cam:
                return [None,None]
            buffer = buffer or ctypes.create_string_buffer(self.x * self.y * self.bytes_per_pixel) 
            got=self.dll.CLEyeCameraGetFrame(self.cam, buffer, timeout)
            return (got,buffer)
        
        def end(self):
            self.__del__()
        def __del__(self):
            if not self.cam:
                return
            self.stop()
            self.dll.CLEyeDestroyCamera(self.cam)
    ### END MULTICAM SECTION ###

    import numpy as np
    import pylab as pl
    import h5py
    #import multicam as mc
    import cv2, os, time, json, sys, warnings,ctypes,logging,threading
    import multiprocessing as mp
    from util import now,now2

    def mp2np(a):
        return np.frombuffer(a.get_obj(), dtype=np.uint8)

    class PSEye(mp.Process):

        RES_SMALL = CLEYE_QVGA
        RES_LARGE = CLEYE_VGA   
        available_framerates = dict(RES_LARGE=[15,30,40,50,60,75], RES_SMALL=[15,30,60,75,100,125])
        DIMS_SMALL = (320,240)
        DIMS_LARGE = (640,480)
        COLOR = CLEYE_COLOR
        GREYSCALE = CLEYE_GREYSCALE

        def __init__(self, idx, resolution, frame_rate, color_mode, clock_sync_obj=None, vflip=False, hflip=False, gain=60, exposure=24, wbal_red=50, wbal_blue=50, wbal_green=50, auto_gain=0, auto_exposure=0, auto_wbal=0, save_name=None):
            super(PSEye, self).__init__()
            self.daemon = True

            self.idx = idx
            self.resolution_code = resolution
            self.resolution = [self.DIMS_SMALL,self.DIMS_LARGE][[self.RES_SMALL,self.RES_LARGE].index(self.resolution_code)]
            self.frame_rate = frame_rate
            self.color_mode = color_mode
            self.vflip = vflip
            self.hflip = hflip
            self.gain = gain
            self.exposure = exposure
            self.auto_gain = auto_gain
            self.auto_exposure = auto_exposure
            self.auto_wbal = auto_wbal
            self.wbal_red,self.wbal_blue,self.wbal_green = wbal_red,wbal_blue,wbal_green
            self.read_dims = self.resolution[::-1]
            if self.color_mode == self.COLOR:
                self.read_dims.append(4)
            
            self.save_name = save_name
            
            self.READING = mp.Value('i',1)
            self.SAVING = mp.Value('i',0)
            self.flush = mp.Value('i',0)
            self.thread_complete = mp.Value('i',0)
            
            self.cS = mp.Array(ctypes.c_uint8,np.product(self.read_dims))
            #self.frame = np.frombuffer(self.cS.get_obj(), dtype=np.uint8).reshape(self.read_dims)
            self.ts = mp.Value('d',0)
            self.clock_sync_obj = clock_sync_obj
            self.offset = mp.Value('d',0)
        def vid_name(self, i):
            return self.save_name+'_{:02}'.format(i)+'.avi'
        def run(self):
            now()
            lib = "CLEyeMulticam.dll"
            dll = ctypes.cdll.LoadLibrary(lib)
            dll.CLEyeGetCameraUUID.restype = GUID
            dll.CLEyeCameraGetFrame.argtypes = [c_void_p, c_char_p, c_int]
            dll.CLEyeCreateCamera.argtypes = [GUID, c_int, c_int, c_float]
        
            self.vc = Ps3Eye(self.idx, self.color_mode, self.resolution_code, self.frame_rate, dll=dll)
            settings = [    (CLEYE_AUTO_GAIN, self.auto_gain),
                            (CLEYE_AUTO_EXPOSURE, self.auto_exposure),
                            (CLEYE_AUTO_WHITEBALANCE,self.auto_wbal),
                            (CLEYE_GAIN, self.gain),
                            (CLEYE_EXPOSURE, self.exposure),
                            (CLEYE_WHITEBALANCE_RED,self.wbal_red),
                            (CLEYE_WHITEBALANCE_BLUE,self.wbal_blue),
                            (CLEYE_WHITEBALANCE_GREEN,self.wbal_green),
                            (CLEYE_VFLIP, self.vflip),
                            (CLEYE_HFLIP, self.hflip),
                     ]
            self.vc.configure(settings)
            self.vc.start()
            time.sleep(0.1)
           
            SAVEMODE = 'opencv'
            if self.save_name != None:
                if SAVEMODE=='opencv':
                    self.vidts_name = self.save_name+'.tstmp'
                    self.vidts_file_temp = open(self.vidts_name, 'a')
                elif SAVEMODE=='hdf5':
                    self.vid_name = self.save_name+'.h5'
                    self.movbuf = []
                    self.timebuf = []

                if SAVEMODE=='opencv':
                    self.vws = [cv2.VideoWriter(self.vid_name(0),cv2.VideoWriter_fourcc(*'MSVC'),self.frame_rate,frameSize=self.resolution,isColor=False)]
                if SAVEMODE=='hdf5':
                    self.vw = h5py.File(self.vid_name)
                    self.dset_mov = self.vw.create_dataset('mov', [0,np.product(self.read_dims)], maxshape=[None,np.product(self.read_dims)])
                    self.dset_time = self.vw.create_dataset('time', [0,2], maxshape=[None,2])
                    
                self.offset.value = self.clock_sync_obj.value-now()
                if SAVEMODE=='opencv':
                    self.vidts_file_temp.write('%0.20f\n'%self.offset.value)
                if SAVEMODE=='opencv' and not self.vws[0].isOpened():
                    logging.error('Video writer failed to open')
                    #raise Exception('Video writer failed to open')   

            # begin true run
            if SAVEMODE=='hdf5':
                self.writethread = True
                threading.Thread(target=self.continuous_write).start()
                self.writelock = threading.Lock()

            n_frames_read = 0
            vw_idx = 0
            while self.READING.value:
                changed_file = False
                val = False
                val,fr = self.vc.get_frame()
                if val:
                    n_frames_read += 1
                    if n_frames_read == 50000:
                        changed_file = True
                        n_frames_read = 0
                        self.vws[-1].release()
                        self.vws.append(cv2.VideoWriter(self.vid_name(vw_idx+1),0,self.frame_rate,frameSize=self.resolution,isColor=False))
                        vw_idx += 1
                    self.ts.value = now()#(time.time(),time.clock(), now())
                    ts2 = now2()
                    self.cS[:] = np.fromstring(fr, np.uint8)
                    if self.SAVING.value and self.save_name:
                        if SAVEMODE=='opencv':
                            self.vws[vw_idx].write(mp2np(self.cS).reshape(self.read_dims))
                            if changed_file:
                                self.vidts_file_temp.write('FILE{:02}:'.format(vw_idx))
                            self.vidts_file_temp.write('%0.20f/%0.20f,'%(self.ts.value,ts2))
                        elif SAVEMODE=='hdf5':
                            with self.writelock:
                                self.movbuf.append(mp2np(self.cS))
                                self.timebuf.append([ts2, self.ts.value])

            if SAVEMODE=='opencv' and self.save_name:
                self.vws[vw_idx].release()
                self.vidts_file_temp.close()
            self.thread_complete.value = 1
            if SAVEMODE=='hdf5':
                while self.writethread:
                    pass
                self.vw.close()

        def continuous_write(self):
            while not self.thread_complete.value:
                if len(self.movbuf) and self.flush.value:
                    with self.writelock:
                        assert len(self.movbuf) == len(self.timebuf)
                        towrite1,towrite2 = self.movbuf[:],self.timebuf[:]
                        self.movbuf,self.timebuf = [],[]
                    self.flush.value = 0
                    towrite1 = np.array(towrite1)
                    towrite2 = np.array(towrite2)
                    self.dset_mov.resize([len(self.dset_mov)+len(towrite1), towrite1.shape[1]])
                    self.dset_time.resize([len(self.dset_time)+len(towrite2), towrite2.shape[1]])
                    self.dset_mov[-len(towrite1):,:] = towrite1
                    self.dset_time[-len(towrite2):,:] = towrite2
            self.writethread = False
                
        def get_current_frame(self, fr, shape=None):
            # give obj.cS as arg
            if shape is None:
                shape = self.read_dims
            return mp2np(fr).reshape(shape)
        def save_on(self, b):
            self.SAVING.value = int(b)
        def end(self):
            self.READING.value = 0
            self.SAVING.value = 0
            while not (self.thread_complete.value):
                pass
            try:
                self.vws = None;del self.vws #attempt to release reference
                del self.vc
            except:
                pass

########
    default_cam_params = dict(      idx=0, 
                        resolution=PSEye.RES_SMALL, 
                        frame_rate=100, 
                        color_mode=PSEye.GREYSCALE,
                        auto_gain = False,
                        auto_exposure = False,
                        auto_wbal = False,
                        gain = 10,
                        exposure = 20,
                        wbal_red = 50,
                        wbal_blue = 50,
                        wbal_green = 50,
                        vflip = True,
                        hflip = True,
            )
            
if __name__ == '__main__':
    cam_params = dict(      idx=0, 
                        resolution=PSEye.RES_SMALL, 
                        frame_rate=100, 
                        color_mode=PSEye.GREYSCALE,
                        auto_gain = False,
                        auto_exposure = False,
                        auto_wbal = True,
                        gain = 100,
                        exposure = 300,
                        wbal_red = 100,
                        wbal_blue = 100,
                        wbal_green = 100,
                        vflip = False
                    )
    cam = PSEye(**cam_params)
    while True:
        fr,ts = cam.read()
        if fr is not None:
            cv2.imshow('Camera View', fr)
            q = cv2.waitKey(1)
            if q == ord('q'):
                break
    cv2.destroyAllWindows()
    cam.end()
    
