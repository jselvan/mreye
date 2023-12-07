import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import nidaqmx.system
from nidaqmx.stream_readers import AnalogMultiChannelReader, AnalogSingleChannelReader
from nidaqmx.stream_writers import AnalogSingleChannelWriter
import numpy as np

import threading
import queue

class Interface:
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
        self.output_path = output_path
        self.logger = logger
        data = np.ones(int(self.reward_duration*self.sampling_rate))
        self.reward_trace = np.append(5*data, -5*data)
        self.queues = {}
        self.threads = {}

    def init_analog_inputs(self, task):
        task.ai_channels.add_ai_voltage_chan(self.channels['eyeh'])
        task.ai_channels.add_ai_voltage_chan(self.channels['eyev'])
        task.ai_channels.add_ai_voltage_chan(self.channels['TR'])
        
        task.timing.cfg_samp_clk_timing(
            rate=self.sampling_rate, 
            sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
            samps_per_chan=self.read_chunk_size
        )
        reader = AnalogMultiChannelReader(task.in_stream)
        return reader

    def init_outputs(self):
        task = nidaqmx.Task()
        task.ao_channels.add_ao_voltage_chan(self.channels['reward'])

        task.timing.cfg_samp_clk_timing(
            rate=self.sampling_rate, 
            sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan=int(self.reward_duration*self.sampling_rate*2)
        )
        writer = AnalogSingleChannelWriter(task.out_stream, auto_start=True)
        return task, writer

    def start(self):
        self.running = True

        self.queues["input"] = queue.Queue()
        self.queues["output"] = queue.Queue()
        self.threads["acquire"] = threading.Thread(target=self.acquire, name="acquire", daemon=True)
        self.threads["acquire"].start()
        # self.logger.info("Started acquisition thread.")
        # self.threads["write"] = threading.Thread(target=self.write, name="write", daemon=True)
        # self.threads["write"].start()
        # self.logger.info("Started write thread.")

    def acquire(self):
        with (nidaqmx.Task() as readAnalogTask, 
            #   nidaqmx.Task() as readDigitalTask,
            open(self.output_path, 'ab') as output_file):
            analogReader = self.init_analog_inputs(readAnalogTask)
            # digitalReader = self.init_digital_inputs(readDigitalTask)
            analogData = np.zeros((3, self.read_chunk_size), dtype=np.float64)
            # digitalData = np.zeros(self.read_chunk_size, dtype=np.float64)

            while self.running:
                analogReader.read_many_sample(analogData, 
                    number_of_samples_per_channel=self.read_chunk_size)
                # digitalReader.read_many_sample(digitalData, number_of_samples_per_channel=self.read_chunk_size)
                analogData.tofile(output_file)
                self.queues["input"].put(analogData)
    
    def write(self):
        with nidaqmx.Task() as writeTask:
            writer = self.init_outputs(writeTask)
            while self.running:
                wave = self.queues["output"].get()
                writer.write_many_sample(wave)

    def stop(self):
        self.running = False
        for thread in self.threads.values():
            thread.join()

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