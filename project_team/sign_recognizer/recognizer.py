"""Phần điều khiển: lấy kết quả camera, xử lý cử chỉ, cập nhật giao diện."""
import queue
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from .camera import HandCamera
from .codebook import CodeInput
from .dataset import DatasetManager
from .gesture import GestureProcessor
from .speech import Speaker
from .ui import MainWindow


class SignRecognizer:
    def __init__(self, camera=0, threshold=.28):
        self.camera_index = camera
        self.camera = None
        self.store = DatasetManager()
        self.code_input = CodeInput()
        self.gesture = GestureProcessor(threshold)
        self.speaker = Speaker()
        self.paused = self.busy = self.closed = False
        self.speech_send = False
        self.trial = None
        self.save_job = None
        self.root = tk.Tk()
        self.ui = MainWindow(self.root, self)
        self.ui.set_text(self.store.text)
        self.ui.show_code('', self.store.warning or 'Có thể gõ phím trực tiếp vào ô văn bản.')
        self.open_camera()

    # ---------- camera và cử chỉ ----------
    def open_camera(self):
        if self.camera is not None:
            self.camera.release()
        self.gesture.reset()
        self.camera = HandCamera(self.camera_index)
        self.ui.set_status('Đang mở camera...')

    def reset_gesture(self):
        self.gesture.reset()
        self.ui.set_status('Đã đặt lại nhận diện. Mở tay ra để bắt đầu.')

    def toggle_pause(self):
        self.paused = not self.paused
        self.gesture.reset()
        self.ui.set_status('Đã tạm dừng (F3 để tiếp tục).' if self.paused else 'Tiếp tục nhận diện.')

    def tick(self):
        if self.closed:
            return
        try:
            self.process_latest_frame()
        except Exception:
            import sys
            self.callback_error(*sys.exc_info())
        self.root.after(15, self.tick)

    def process_latest_frame(self):
        self.speech_results()
        if self.camera is None:
            return
        latest = self.camera.read_latest()
        if latest is None:
            if self.camera.failed:
                self.ui.set_status((self.camera.error or 'Mất kết nối camera.') + ' Chọn Camera → Kết nối lại.')
                self.camera = None
            return
        rgb, hands, captured = latest
        events = []
        if not (self.paused or self.busy):
            events = self.gesture.update(hands, captured)
            self.ui.set_status(self.gesture.status)
            self.ui.draw_feedback(rgb, self.gesture)
        self.ui.show_frame(rgb)
        if self.trial is not None and self.gesture.contact.active:
            self.trial['contact'] = True
        for event in events:
            self.handle_event(event)

    def handle_event(self, event):
        if self.busy:
            return
        if event == 'SEND':
            self.send()
            return
        text = self.ui.get_text()
        new_text, message = self.code_input.apply(event, text)
        if new_text != text:
            self.ui.set_text(new_text)
            if self.trial is not None and len(new_text) > len(text):
                self.trial['actual'] += new_text[len(text):]
                if self.trial['elapsed'] is None:
                    self.trial['elapsed'] = time.monotonic() - self.trial['start']
        self.ui.show_code(self.code_input.pending, message)

    # ---------- nút bấm ----------
    def delete_digit(self):
        self.handle_event('BACKSPACE')

    def clear_code(self):
        self.code_input.pending = ''
        self.ui.show_code('', 'Đã xóa mã.')

    def clear_text(self):
        if not self.busy:
            self.ui.set_text('')

    # ---------- lưu file ----------
    def save(self):
        if self.save_job is not None:
            self.root.after_cancel(self.save_job)
            self.save_job = None
        try:
            self.store.save(self.ui.get_text(), self.store.history)
            return True
        except OSError as exc:
            self.ui.notify(f'Không lưu được văn bản: {exc}')
            return False

    def text_changed(self, event=None):
        if self.ui.text.edit_modified():
            self.ui.text.edit_modified(False)
            if self.save_job is not None:
                self.root.after_cancel(self.save_job)
            self.save_job = self.root.after(500, self.save)

    def export_text(self):
        path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text', '*.txt')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.store.history + [self.ui.get_text()]))
            self.ui.notify('Đã xuất văn bản.')
        except OSError as exc:
            self.ui.notify(f'Không xuất được: {exc}')

    # ---------- đọc bằng loa ----------
    def send(self):
        if self.busy:
            return
        if self.code_input.pending:
            self.ui.notify('Còn mã chưa xác nhận, hãy xác nhận hoặc xóa mã trước khi gửi.')
            return
        text = self.ui.get_text()
        if text.strip() and self.save():
            self.speech_send = True
            self.speak(text)

    def read_last(self):
        text = self.ui.get_text() or (self.store.history[-1] if self.store.history else '')
        if text.strip() and not self.busy:
            self.speech_send = False
            self.speak(text)

    def speak(self, text):
        self.busy = True
        self.gesture.reset()
        self.ui.set_status('Đang đọc...')
        try:
            self.speaker.speak(text)
        except Exception as exc:
            self.busy = False
            self.ui.notify(f'Không đọc được qua loa: {exc}')

    def speech_results(self):
        try:
            text, error = self.speaker.results.get_nowait()
        except queue.Empty:
            return
        self.busy = False
        if error:
            self.ui.notify(f'Không đọc được qua loa: {error}. Văn bản được giữ lại.')
        elif self.speech_send:
            self.store.history.append(text)
            # Nếu người dùng gõ thêm trong lúc đọc thì giữ lại phần đó
            if self.ui.get_text() == text:
                self.ui.set_text('')
            if self.save():
                self.ui.notify('Đã đọc và lưu vào lịch sử.')
        else:
            self.ui.notify('Đã đọc xong.')

    # ---------- đo thử ----------
    def start_trial(self):
        if self.trial is not None:
            self.ui.notify('Hãy kết thúc lần đo hiện tại trước.')
            return
        if self.camera is None or self.paused or self.busy:
            self.ui.notify('Cần bật camera và nhận diện trước khi đo.')
            return
        expected = simpledialog.askstring('Đo thử', 'Chữ cần nhập (A–Z, để trống = thử không chạm):', parent=self.root)
        if expected is None:
            return
        expected = expected.strip().upper()
        if expected and (len(expected) != 1 or not 'A' <= expected <= 'Z'):
            self.ui.notify('Chữ cần nhập phải là một chữ cái A–Z.')
            return
        condition = simpledialog.askstring('Đo thử', 'Điều kiện ánh sáng / góc quay:',
                                           initialvalue='đủ sáng / chính diện', parent=self.root)
        if condition is None:
            return
        self.trial = {'expected': expected, 'start': time.monotonic(), 'actual': '',
                      'elapsed': None, 'contact': False, 'condition': condition}
        self.ui.notify('Đang đo... thực hiện cử chỉ rồi chọn Đo thử → Kết thúc đo.')

    def finish_trial(self):
        if self.trial is None:
            return
        t = self.trial
        try:
            path = self.store.record_trial(t['expected'], t['actual'], '' if t['elapsed'] is None else t['elapsed'],
                                           bool(t['expected']), t['contact'], 'touch', t['condition'])
            self.trial = None
            self.ui.notify(f'Đã ghi kết quả vào {path}')
        except OSError as exc:
            self.ui.notify(f'Không lưu được kết quả đo: {exc}')

    # ---------- chạy / đóng ----------
    def close(self):
        if not self.save() and not messagebox.askyesno('Thoát', 'Không lưu được văn bản. Vẫn thoát?'):
            return
        self.closed = True
        if self.camera is not None:
            self.camera.release()
        self.speaker.close()
        self.root.destroy()

    def run(self):
        self.root.report_callback_exception = self.callback_error
        self.root.after(0, self.tick)
        try:
            self.root.mainloop()
        finally:
            if self.camera is not None:
                self.camera.release()
            self.speaker.close()

    def callback_error(self, kind, value, tb):
        import traceback
        from .config import ERROR_LOG
        self.paused = True
        self.gesture.reset()
        try:
            ERROR_LOG.write_text(''.join(traceback.format_exception(kind, value, tb)), encoding='utf-8')
        except OSError:
            pass
        self.ui.set_status(f'Lỗi: {value}. Đã tạm dừng nhận diện, xem sign_error.log (F3 để tiếp tục).')
