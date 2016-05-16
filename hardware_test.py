from ni845x import NI845x

ni = NI845x()

ni.write_dio(0, 1)
raw_input('Light on')
ni.write_dio(0, 0)

ni.write_dio(1, 1)
raw_input('Puff on')
ni.write_dio(1, 0)

ni.end()