"""Chạy thử giao diện ẩn: không dùng webcam, loa hay dữ liệu thật."""
import queue
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sign_recognizer import recognizer
from sign_recognizer.camera import HandCamera
from sign_recognizer.dataset import DatasetManager
from fake_hand import FakeDetector, make_hand
from test_camera import FakeCapture


class FakeSpeaker:
    def __init__(self):
        self.results = queue.Queue()

    def speak(self, text):
        self.submitted = text

    def close(self):
        pass


def fake_camera(index):
    return HandCamera(index, lambda i: FakeCapture(), lambda: FakeDetector({'right': make_hand()}))


real_tk = recognizer.tk.Tk


def hidden_root():
    root = real_tk()
    root.withdraw()
    return root


with tempfile.TemporaryDirectory() as directory:
    with patch.object(recognizer.tk, 'Tk', hidden_root), \
            patch.object(recognizer, 'DatasetManager', lambda: DatasetManager(directory)), \
            patch.object(recognizer, 'Speaker', FakeSpeaker), \
            patch.object(recognizer, 'HandCamera', fake_camera):
        app = recognizer.SignRecognizer()
        try:
            app.root.update()
            deadline = time.monotonic() + 3
            while app.camera.latest is None and time.monotonic() < deadline:
                time.sleep(.005)
            app.process_latest_frame()
            assert app.gesture.hand is not None
            # Nhập H (112) rồi I (121), vuốt cách, rồi xóa bằng nắm tay
            for event in ('1', '1', '2', 'CONFIRM', '1', '2', '1', 'CONFIRM', 'SPACE'):
                app.handle_event(event)
            assert app.ui.get_text() == 'HI '
            app.handle_event('1')
            app.handle_event('SPACE')
            assert app.ui.get_text() == 'HI '
            app.handle_event('BACKSPACE')
            assert app.code_input.pending == ''
            app.send()
            assert app.busy and app.speaker.submitted == 'HI '
            app.speaker.results.put(('HI ', 'simulated voice failure'))
            app.speech_results()
            assert not app.busy and app.ui.get_text() == 'HI '
            app.send()
            app.speaker.results.put(('HI ', None))
            app.speech_results()
            assert app.ui.get_text() == '' and app.store.history == ['HI ']
            app.ui.set_text('OLD')
            app.send()
            app.ui.text.insert('end', ' NEW')
            app.speaker.results.put(('OLD', None))
            app.speech_results()
            assert app.ui.get_text() == 'OLD NEW'
            app.handle_event('1')
            app.send()
            assert not app.busy   # còn mã chưa xác nhận thì không gửi
            app.clear_code()
            app.root.update()
            app.close()
            assert DatasetManager(directory).text == 'OLD NEW'
            assert DatasetManager(directory).history == ['HI ', 'OLD']
        finally:
            if not app.closed:
                app.camera.release()
                app.root.destroy()
print('PASS: giao diện, camera giả, nhập mã, vuốt cách, đọc loa, lưu phiên')
