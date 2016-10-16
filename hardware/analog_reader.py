import time, sys, threading, logging, copy, Queue, warnings
import multiprocessing as mp
import numpy as np
import pylab as pl
from daq import DAQIn
from expts.routines import add_to_saver_buffer
from util import now,now2

class AnalogReader(mp.Process):
    """
    Instantiates a new process that handles a DAQIn object.
    The main thread constantly checks the DAQIn for anything in its data_q, saving it when there, and also making it available to public requests, like the exp interface
    """

    READ_BUF_SIZE = 10
    ACCUM_SIZE = 2000 # Must be multiple of READ_BUF_SIZE

    def __init__(self, ports=['ai0'], portnames=['hall'], runtime_ports=[0], movement_port=0, movement_window=1.0, movement_thresh=3., daq_sample_rate=500., save_buffer_size=8000, saver_obj_buffer=None, sync_flag=None, **daq_kwargs):
        super(AnalogReader, self).__init__()
        self.daq_kwargs = daq_kwargs
        
        # Sync
        self.sync_flag = sync_flag
        self.sync_val = mp.Value('d', 0)

        # Data acquisition parameters
        self.ports = ports
        self.portnames = portnames
        self.runtime_ports = runtime_ports # to be used in accumulator
        self.movement_port = movement_port # index *of runtime_ports* that corresponds to wheel sensor
        self.daq_sample_rate = daq_sample_rate
        
        # Data processing parameters
        self.movement_window = int(movement_window * self.daq_sample_rate) # movement_window
        self.movement_thresh = movement_thresh

        # data containers
        self.accum = np.zeros((len(self.ports),self.ACCUM_SIZE))
        self.accum_ts = []
        self.accum_q = mp.Array('d', len(self.runtime_ports)*self.ACCUM_SIZE)

        # processing containers
        self.moving_ = mp.Value('b', False)
        
        # threading structures
        self.logic_lock = mp.Lock()

        # saving
        self._saving = mp.Value('b', False)
        self.save_buffer_size = save_buffer_size
        self.n_added_to_save_buffer = 0
        self.save_buffer = np.zeros([len(self.ports),self.save_buffer_size])
        self.save_buffer_ts = np.zeros([2,self.save_buffer_size])
        self.saver_obj_buffer = saver_obj_buffer

        self._on = mp.Value('b', True)
        self._kill_flag = mp.Value('b', False)
        self.start()

    @property
    def moving(self):
        with self.logic_lock:
            temp = self.moving_.value
            self.moving_.value = False
        return temp

    def run(self):
        while not self.sync_flag.value:
            self.sync_val.value = now()

        self.daq = DAQIn(ports=self.ports, read_buffer_size=self.READ_BUF_SIZE, sample_rate=self.daq_sample_rate, **self.daq_kwargs)
        
        while self._on.value:
            
            if self._kill_flag.value:
                self.daq.release()

            try:
                ts,ts2,dat = self.daq.data_q.get(timeout=0.5)
            except Queue.Empty:
            
                if self._kill_flag.value:
                   # final dump:
                    if self.n_added_to_save_buffer:
                        add_to_saver_buffer(self.saver_obj_buffer, 'analogreader', self.save_buffer[:,-self.n_added_to_save_buffer:].T.copy(), ts=self.save_buffer_ts[0,-self.n_added_to_save_buffer:].copy(), ts2=self.save_buffer_ts[1,-self.n_added_to_save_buffer:].copy(), columns=self.portnames)
                    self._on.value = False
                    
                continue

            if self._kill_flag.value:
                logging.info('Analogreader final flush: {} reads remain.'.format(self.daq.data_q.qsize()))

            dat = dat.reshape((len(self.ports),self.READ_BUF_SIZE))
            
            # update save buffer with new data
            self.save_buffer = np.roll(self.save_buffer, -self.READ_BUF_SIZE, axis=1)
            self.save_buffer_ts = np.roll(self.save_buffer_ts, -self.READ_BUF_SIZE, axis=1)
            self.save_buffer[:,-self.READ_BUF_SIZE:] = dat[:,:]
            self.save_buffer_ts[:,-self.READ_BUF_SIZE:] = np.array([ts,ts2])[:,None]
            if self._saving.value:
                self.n_added_to_save_buffer += self.READ_BUF_SIZE
                dump = self.n_added_to_save_buffer >= self.save_buffer_size
            else:
                dump = False

            # update accumulator (runtime analysis buffer)
            self.accum = np.roll(self.accum, -self.READ_BUF_SIZE, axis=1)
            self.accum[:,-self.READ_BUF_SIZE:] = dat[:,:]
            self.accum_ts += [ts]*self.READ_BUF_SIZE
            self.accum_q[:] = (self.accum.copy()[self.runtime_ports]).ravel()
            
            # update experimental logic
            with self.logic_lock:
                
                _tmp_moving = self.accum[self.runtime_ports[self.movement_port], -self.movement_window:]
                self.moving_.value = np.max(_tmp_moving)-np.min(_tmp_moving) > self.movement_thresh

            if dump and self._saving.value:
                if self.n_added_to_save_buffer > self.save_buffer_size:
                    warnings.warn('DAQ save buffer size larger than expected: some samples were missed. Size={}, Expected={}'.format(self.n_added_to_save_buffer,self.save_buffer_size))
                add_to_saver_buffer(self.saver_obj_buffer, 'analogreader', self.save_buffer.T.copy(), ts=self.save_buffer_ts[0,:].copy(), ts2=self.save_buffer_ts[1,:].copy(), columns=self.portnames)
                self.n_added_to_save_buffer = 0
    
    def get_accum(self):
        return np.frombuffer(self.accum_q.get_obj()).reshape([len(self.runtime_ports), self.ACCUM_SIZE])
    
    def begin_saving(self):
        self.n_added_to_save_buffer = 0
        self._saving.value = True

    def end(self):
        self._kill_flag.value = True
        while self._on.value:
            pass

if __name__ == '__main__':
    pl.figure()
    lr = AnalogReader()
    lr.start()
    show_lines = pl.plot(lr.accum.T)
    pl.ylim([-.1,10.1])
    while True:
        for idx,sl in enumerate(show_lines):
            sl.set_ydata(lr.accum[idx])
        pl.draw()
        pl.pause(0.001)
