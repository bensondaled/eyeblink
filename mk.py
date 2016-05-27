from ni845x import NI845x
import time

f = float(raw_input('Enter frequency: '))
dur = float(raw_input('Enter trial duration (seconds): '))

ni = NI845x()

t0 = time.clock()
tls = time.clock()
while time.clock()-t0 < dur:
    if (time.clock()-tls) >= 1./f:
        ni.write_dio(1, 1)
        time.sleep(0.015)
        ni.write_dio(1, 0)
        tls = time.clock()

ni.end()