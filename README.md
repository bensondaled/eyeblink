(*Note that as of September 2017, I have completely re-implemented the python interface to the PS3Eye cameras. The method used in this package still works, but the new version has many advantages, including being entirely open-source and not demanding a 32-bit architecture. That project is still in progress, but can be found here: https://github.com/bensondaled/pseyepy)

Eyeblink Conditioning Interface
--------------------------------

This repository stores the code for running eyeblink conditioning experiments in mice. Capabilities include daq interfacing, 2-camera acqusition, live monitoring and closed-loop trial initiation, and interfacing with two-photon microscopes for synchronization. All data are saved to HDF-5.

For details on camera usage, see the hardware/cameras.py file, and specifically the PSEye class and the example code at the bottom.

Usage notes:
------------

* Due to restrictions imposed by the CLEye driver, the software must be run in a 32-bit python installation if you want to use 2 cameras simultaneously

Contact deverett [at] princeton [dot] edu for more info.
