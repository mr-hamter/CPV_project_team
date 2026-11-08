import threading
import time
import unittest

import numpy as np

from sign_recognizer.camera import HandCamera
from fake_hand import FakeDetector, make_hand


class FakeCapture:
    def __init__(self, opened=True, ok=True, shape=(480, 640, 3)):
        self.opened, self.ok, self.shape = opened, ok, shape
        self.released = threading.Event()
        self.count = 0

    def isOpened(self):
        return self.opened

    def set(self, *args):
        return True

    def read(self):
        time.sleep(.005)
        self.count += 1
        if not self.ok:
            return False, None
        frame = np.zeros(self.shape, np.uint8)
        frame[0, 0, 0] = self.count % 256
        return True, frame

    def release(self):
        self.released.set()


class CameraTest(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.005)
        self.fail('camera thread did not reach expected state')

    def test_latest_result_has_frame_and_hands(self):
        capture = FakeCapture(shape=(720, 1280, 3))
        detector = FakeDetector({'right': make_hand()})
        camera = HandCamera(0, lambda i: capture, lambda: detector)
        try:
            self.wait_for(lambda: camera.latest is not None)
            rgb, hands, captured = camera.read_latest()
            self.assertEqual(rgb.shape, (480, 640, 3))
            self.assertEqual(len(hands), 1)
            self.assertEqual(hands[0][0], 'right')
            self.assertEqual(len(hands[0][1]), 21)
            self.assertLessEqual(captured, time.monotonic())
            self.assertIsNone(camera.read_latest())   # mỗi khung chỉ lấy một lần
        finally:
            camera.release()
        self.assertFalse(camera.thread.is_alive())
        self.assertTrue(capture.released.is_set())
        self.assertTrue(detector.closed)

    def test_repeated_read_failure(self):
        capture = FakeCapture(ok=False)
        camera = HandCamera(0, lambda i: capture, FakeDetector)
        self.wait_for(lambda: camera.failed)
        self.assertIn('Không đọc được', camera.error)
        self.assertTrue(capture.released.is_set())
        camera.release()

    def test_camera_not_opened(self):
        camera = HandCamera(0, lambda i: FakeCapture(opened=False), FakeDetector)
        self.wait_for(lambda: camera.failed)
        self.assertIn('Không mở được camera', camera.error)
        camera.release()


if __name__ == '__main__':
    unittest.main()
