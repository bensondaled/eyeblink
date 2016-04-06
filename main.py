import time
from pymat import TCPIP

## Params
si_data_path = r'D:\\deverett\\eyeblink'

def safe_input(prompt):
    valid = False
    while not valid:
        s = raw_input(prompt)
        valid = True
        if len(s)==0 or any([c in s for c in [' ','\\','/','\'','\"']]):
            valid = False
    return s

tcpip = TCPIP()

cont = True
while cont != 'q':
    animal = safe_input('Enter animal name: ')
    exp_name = time.strftime('%Y%m%d%H%M%S')
    si_dict = dict(path=si_data_path+r'\\{}'.format(animal), name=exp_name, count=1)
    tcpip.send(si_dict)
    exp = Experiment(name=exp_name, animal=animal)
    exp.run()
    cont = raw_input('Continue? (q to quit)')

tcpip.end()
