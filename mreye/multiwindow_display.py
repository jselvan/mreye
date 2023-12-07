from mreye.display import Display

import time

import cv2


class MultiWindowDisplay(Display):
    EXPERIMENTER_SCREEN_NAME = 'EXPERIMENTER_SCREEN'
    DEFAULT_EXPERIMENTER_RECT = [0, 0, 888, 500]
    EYE_COLOR = (0, 0, 255)
    def __init__(self, subject_rect, distance, diagonal_size, experimenter_rect=None, logger=None, mouse_callback=None):
        super().__init__(subject_rect, distance, diagonal_size, logger)
        self.experimenter_screen_name = self.EXPERIMENTER_SCREEN_NAME
        self.experimenter_rect = experimenter_rect if experimenter_rect is not None else self.DEFAULT_EXPERIMENTER_RECT
        X, Y, W, H = self.experimenter_rect
        self.show_eye = True
        self.experimenter_center = (W//2, H//2)
        if W != self.W or H != self.H:
            self.rescale_experimenter = True
            pixels_diagonal = (self.W**2 + self.H**2)**0.5
            experimenter_pixels_diagonal = (W**2 + H**2)**0.5
            self.experimenter_pixels_per_degree = self.pixels_per_degree * experimenter_pixels_diagonal / pixels_diagonal 
        self.mouse_callback = mouse_callback

    def start(self):
        cv2.namedWindow(self.experimenter_screen_name, cv2.WINDOW_NORMAL)
        X, Y, W, H = self.experimenter_rect
        cv2.moveWindow(self.experimenter_screen_name, X, Y)
        cv2.resizeWindow(self.experimenter_screen_name, W, H)
        if self.mouse_callback is not None:
            cv2.setMouseCallback(self.experimenter_screen_name, self.mouse_callback)
        super().start()

    def draw_eye(self, frame):
        # eye_h, eye_v = self.update_queue.get()
        eye_h = eye_h * self.experimenter_pixels_per_degree + self.experimenter_center[0]
        eye_v = eye_v * self.experimenter_pixels_per_degree + self.experimenter_center[1]
        for h, v in zip(eye_h, eye_v):
            cv2.line(frame, h, v, self.EYE_COLOR, 2)
        cv2.circle(frame, (h, v), 5, self.EYE_COLOR, -1)
        return frame

    def render_frame(self, delta_t):
        frame = self.get_frame(delta_t)

        if self.rescale_experimenter:
            exp_frame = cv2.resize(frame, (self.experimenter_rect[2], self.experimenter_rect[3]), interpolation=cv2.INTER_LINEAR)
        else:
            exp_frame = frame
        if self.show_eye:
            exp_frame = self.draw_eye(exp_frame)

        cv2.imshow(self.subject_screen_name, frame)
        cv2.imshow(self.experimenter_screen_name, exp_frame)
        cv2.waitKey(1)
        self.last_frame_time = time.time()