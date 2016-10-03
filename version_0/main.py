import time
from expts import Experiment
from pymat import TCPIP

## Params
si_data_path = r'D:\\deverett\\eyeblink'
tcpip_address = '128.112.217.150'

def safe_input(prompt):
    valid = False
    while not valid:
        s = raw_input(prompt)
        valid = True
        if len(s)==0 or any([c in s for c in [' ','\\','/','\'','\"']]):
            valid = False
    return s


if __name__ == '__main__':
    imaging = safe_input('Imaging? (y/n) ')
    imaging = imaging=='y'
    if imaging:
        tcpip = TCPIP(tcpip_address)
    cont = True
    while cont != 'q':
        animal = safe_input('Enter animal name: ')
        exp_name = time.strftime('%Y%m%d%H%M%S')
        if imaging:
            si_dict = dict(path=si_data_path+r'\\{}'.format(animal), name=exp_name, idx=1)
            tcpip.send(si_dict)
        exp = Experiment(name=exp_name, animal=animal, imaging=imaging)
        exp.run()
        cont = raw_input('Continue? (q to quit)')
    if imaging:
        tcpip.end()
