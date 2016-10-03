from ni845x import NI845x
import time, winsound, multiprocessing

if __name__ == '__main__':
    dur = float(raw_input('Enter trial duration (seconds): '))
    lag = float(raw_input('Enter wait time before starting (seconds): '))

    ni = NI845x(False)

    t0 = time.clock()
    ni.write_dio(3, 1)
    ni.write_dio(3, 0)
    while time.clock()-t0 < lag:
        pass
    t0 = time.clock()
    p = multiprocessing.Process(target=winsound.PlaySound, args=('click.wav',winsound.SND_FILENAME))
    p.start()
    print 'Running...'
    while time.clock()-t0 < dur:
        pass
    print 'Complete.'
    p.terminate()
    ni.write_dio(4, 1)
    ni.write_dio(4, 0)
    ni.end()