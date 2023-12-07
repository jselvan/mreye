from mreye.getLogger import getLogger

from queue import Queue, Empty
import time

import cv2
import numpy as np

class Display:
    SUBJECT_SCREEN_NAME = 'SUBJECT_SCREEN'
    def __init__(self, subject_rect, distance, diagonal_size, logger=None):
        if logger is None:
            logger = getLogger()
        self.logger = logger
        self.subject_screen_name = self.SUBJECT_SCREEN_NAME
        self.X, self.Y, self.W, self.H = subject_rect
        self.objects = []
        pixels_diagonal = (self.W**2 + self.H**2)**0.5
        screen_angle = 2 * np.arctan((diagonal_size/2)/distance)
        self.pixels_per_degree = pixels_diagonal / np.rad2deg(screen_angle)
        self.center = (self.W//2, self.H//2)
        self.update_queue = Queue()

    def start(self):
        cv2.namedWindow(self.subject_screen_name, cv2.WINDOW_NORMAL)
        cv2.moveWindow(self.subject_screen_name, self.X, self.Y)
        cv2.resizeWindow(self.subject_screen_name, self.W, self.H)
        self.render_interval = 1/60
        self.last_frame_time = time.time()
        self.running = True
        self.logger.debug("Display started")
        self.render_loop()

    def post_update(self, update):
        self.update_queue.put(update)  # Method to post updates to the queue

    def stop(self):
        self.running = False
        # self.rendering_timer.join()
        # self.logger.info('final render completed')
        cv2.destroyAllWindows()
        cv2.waitKey(0)
        self.logger.info('window destroyed')

    def render_loop(self):
        while self.running:
            try:
                update = self.update_queue.get(timeout=self.render_interval)
            except Empty:
                pass
            try:
                self.process_update(update)
            except Exception as e:
                self.logger.error(e)
            self.render_frame(time.time()-self.last_frame_time)
        self.stop()

    def process_update(self, update):
        for item in update:
            if item=='CLEAR':
                self.clear()
            elif item=='QUIT':
                self.running = False
                return False
            else:
                self.add_object(**item)
        return True

    def get_frame(self, delta_t):
        frame = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        for v in sorted(self.objects, key=lambda x: x['z']):
            if v['type'] == 'circle':
                frame = cv2.circle(frame, (v['x'], v['y']), v['r'], v['c'], -1)
            elif v['type'] == 'video':
                v['elapsed_time'] += delta_t
                frames_passed = v['elapsed_time'] // v['frame_interval']
                v['elapsed_time'] -= frames_passed * v['frame_interval']
                if frames_passed > 1:
                    v['cap'].set(cv2.CAP_PROP_POS_FRAMES, v['cap'].get(cv2.CAP_PROP_POS_FRAMES) + frames_passed)
                    self.logger.warn("Dropped {} frames".format(frames_passed-1))
                if frames_passed > 0 or v['frame'] is None:
                    ret, video_frame = v['cap'].read()
                    if not ret and v['loop']:
                        v['cap'].set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, video_frame = v['cap'].read()
                    elif not ret:
                        # remove this from object list
                        self.objects.remove(v)
                        continue
                    v['frame'] = video_frame
                frame[v['y']:v['y']+v['frame'].shape[0], v['x']:v['x']+v['frame'].shape[1]] = v['frame']
            else:
                raise NotImplementedError("Unknown object type: {}".format(v['type']))
        return frame

    def render_frame(self, delta_t):
        frame = self.get_frame(delta_t)
        cv2.imshow(self.subject_screen_name, frame)
        cv2.waitKey(1)
        self.last_frame_time = time.time()

    def add_object(self, **kwargs):
        if kwargs['type'] == 'circle':
            kwargs['x'] = int(kwargs['x'] * self.pixels_per_degree + self.center[0])
            kwargs['y'] = int(kwargs['y'] * self.pixels_per_degree + self.center[1])
            kwargs['r'] = int(kwargs['r'] * self.pixels_per_degree)
            kwargs['c'] = kwargs['c'][::-1] # BGR -> RGB
        elif kwargs['type'] == 'video':
            kwargs['cap'] = cv2.VideoCapture(kwargs['path'])
            fps = kwargs['cap'].get(cv2.CAP_PROP_FPS)
            kwargs['frame'] = None
            kwargs['elapsed_time'] = 0
            kwargs['frame_interval'] = 1 / fps
            kwargs['loop'] = kwargs.get('loop', True)
            video_offset_x = kwargs['cap'].get(cv2.CAP_PROP_FRAME_WIDTH) /2
            video_offset_y = kwargs['cap'].get(cv2.CAP_PROP_FRAME_HEIGHT)/2
            
            kwargs['x'] = int(kwargs['x'] * self.pixels_per_degree + self.center[0] - video_offset_x)
            kwargs['y'] = int(kwargs['y'] * self.pixels_per_degree + self.center[1] - video_offset_y)
        else:
            raise NotImplementedError("Unknown object type: {}".format(kwargs['type']))
        self.logger.info(kwargs)
        self.objects.append( kwargs )

    def clear(self):
        self.objects = []
