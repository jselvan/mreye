from mreye.display import Display
from mreye.getLogger import getLogger
from mreye.interface import Interface

import json
from pathlib import Path
import time
import threading

ANALOG_THRESHOLD = 2
class Experiment:
    eye_calibration = {
        'gain': {'x': 10, 'y': 10},
        'offset': {'x': 0, 'y': 0},
    }
    def __init__(self, sequence, session_name, verbose=False):
        # set up data paths
        if session_name is None:
            session_name = time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = session_dir = Path(session_name).mkdir()
        self.analog_data_path = session_dir/'analog_data.bin'
        self.logger_path = session_dir/'experiment.log'
        self.data_path = session_dir/'data.txt'
        json.dump(sequence, open(session_dir/"sequence.json",'w'))

        # set up main logger
        self.logger=getLogger('main', printLevel='DEBUG' if verbose else 'WARN', fileName=self.logger_path)
        self.logger.info('Main logger initialized')

        # set up display and interface
        self.display = Display([1920,0,1920,1080], 119, 38.4, logger=getLogger(name='display', fileName=self.logger_path))
        self.interface = Interface(self.analog_data_path, logger=getLogger(name='interface', fileName=self.logger_path))
        self.sequence = sequence
        self.logger.info("Experiment initialized.")

    def run(self):
        self.interface.start()
        mainthread = threading.Thread(target=self.main, name="main")
        mainthread.start()
        self.display.start()
        mainthread.join()

    def log_event(self, event):
        with open(self.data_path, 'a') as f:
            f.write(event + '\n')
    
    def main(self):
        self.logger.info("Experiment started.")

        self.start_time = time.time()
        self.start_block()
        total_samples = fixated_samples = 0
        TRs = 0
        TR_HIGH = True
        # TOTAL_TR_NUMBER = 0
        while True:
            analogdata = self.interface.queues["input"].get()

            # detect fixation
            if 'fixation' in self.current_block:
                eye_h = ((analogdata[0]+self.eye_calibration['offset']['x'])) * self.eye_calibration['gain']['x']
                eye_v = ((analogdata[1]+self.eye_calibration['offset']['y'])) * self.eye_calibration['gain']['y']



                eye_h -= self.current_block['fixation']['x']
                eye_v -= self.current_block['fixation']['y']
                distance = (eye_h**2 + eye_v**2)**0.5
                fixated_samples += (distance <= self.current_block['fixation']['radius']).sum()
                total_samples += analogdata.shape[1]
                # self.logger.info((eye_h.min(), eye_v.min()))
                # self.logger.debug("{}/{} samples fixated".format(fixated_samples, total_samples))

            # detect trigger state changes
            digital_data = analogdata[2]
            if TR_HIGH and (digital_data<ANALOG_THRESHOLD).any():
                self.logger.debug(("TR LOW", digital_data.min(), digital_data.max()))
                self.log_event("TR_LOW {}".format(time.time()-self.start_time))
                TR_HIGH = False
                TRs += 1

                if 'fixation' in self.current_block and fixated_samples/total_samples > self.current_block['fixation']['proportion']:
                    prop_fix = fixated_samples/total_samples*100
                    self.logger.info("Good monkey: {}%".format(prop_fix))
                    self.log_event("REWARD {} {}".format(prop_fix, time.time()-self.start_time))
                    self.interface.good_monkey()
                total_samples = fixated_samples = 0
            elif not TR_HIGH and (digital_data>ANALOG_THRESHOLD).any():
                # self.logger.debug(("TR HIGH", digital_data.min(), digital_data.max()))
                TR_HIGH = True
                self.log_event("TR_HIGH {}".format(time.time()-self.start_time))

            # check if block is finished and start next block
            if TRs == self.current_block['n_triggers']:
                TRs = 0
                self.logger.debug("Block finished")
                self.display.post_update(['CLEAR'])
                if len(self.sequence) == 0:
                    break
                else:
                    self.start_block()
        self.display.post_update(['QUIT'])
        self.interface.stop()

    def start_block(self):
        self.current_block = self.sequence.pop(0)
        self.logger.info("Starting block: {}".format(self.current_block['name']))
        self.log_event("BLOCK_START {} {}".format(self.current_block['name'], time.time()-self.start_time))
        stimuli = self.current_block.get("stimuli", [])
        if stimuli:
            self.display.post_update(stimuli)

if __name__ == "__main__":
    from mreye.generate_sequence import generate_sequence
    import json
    import sys

    session_name = sys.argv[1]

    if len(sys.argv) > 2:
        sequence = json.load(open(sys.argv[2]))
    else:
        sequence = generate_sequence()

    experiment = Experiment(sequence, session_name, verbose=True)
    experiment.run()