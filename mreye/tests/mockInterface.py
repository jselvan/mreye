from mreye.interface import Interface
from mreye.main import Experiment
from mreye.multiwindow_display import MultiWindowDisplay as Display
from mreye.getLogger import getLogger

import time
import threading
import queue
from pathlib import Path

import numpy as np
import cv2


class MockExperiment(Experiment):
    def __init__(self, sequence, session_name, verbose=False):
        if session_name is None:
            session_name = time.strftime("%Y%m%d_%H%M%S")
        analog_data_path = "{}.bin".format(session_name)
        self.analog_data_path = Path(analog_data_path)
        self.logger_path = self.analog_data_path.with_suffix(".log")
        self.data_path = f"{session_name}.data.txt"
        self.logger=getLogger('main', printLevel='DEBUG' if verbose else 'WARN', fileName=self.logger_path)
        self.logger.info('Main logger initialized')

        self.interface = MockInterface(self.analog_data_path, logger=getLogger(name='interface', fileName=self.logger_path))
        self.display = Display([1920,0,1920,1080], 119, 38.4, logger=getLogger(name='display', fileName=self.logger_path))
        
        self.sequence = sequence
        self.logger.info("Experiment initialized.")



class MockInterface(Interface):
    reward_duration = 0.1
    channels = {
        'eyeh': 'Dev2/ai0',
        'eyev': 'Dev2/ai1',
        # 'TR': 'Dev2/port1/line0',
        'TR': 'Dev2/ai2',
        'reward': 'Dev2/ao0',
    }
    sampling_rate = 2000
    read_chunk_size = 50

    def __init__(self, output_path, logger):
        super().__init__(output_path, logger)
        self.mouse_data = []

    def start(self):
        self.running = True

        self.queues["input"] = queue.Queue()
        self.queues["output"] = queue.Queue()
        self.threads["acquire"] = threading.Thread(target=self.acquire, name="acquire", daemon=True)
        self.threads["acquire"].start()

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            chunk_duration = (self.read_chunk_size*self.sampling_rate)
            oldest_sample_time = time.time()-chunk_duration
            self.mouse_data.append((x, y, time.time()))
            self.mouse_data = list(filter(lambda x: x[2] > oldest_sample_time, self.mouse_data))

    def acquire(self):
        start_time = time.time()
        tick = 100
        TR_interval = 15
        tick_count = 0
        while self.running:
            self.analog_data = np.array(self.mouse_data)
            if tick_count % TR_interval == 0:
                self.analog_data[2, :] = 0
            else:
                self.analog_data[2, :] = 5
            time.sleep(tick/1000)
            tick_count += 1

    def stop(self):
        self.running = False
        for thread in self.threads.values():
            thread.join()
        # self.logger.info("Stopped acquisition thread.")

    def good_monkey(self, blocking=False):
        self.threads['reward'] = threading.Thread(target=self.reward, name="reward", daemon=True)
        self.threads['reward'].start()
        if blocking:
            self.threads.pop('reward').join()

    def reward(self):
        task, writer = self.init_outputs()
        writer.write_many_sample(self.reward_trace)
        task.wait_until_done()
        task.stop()
        task.close()