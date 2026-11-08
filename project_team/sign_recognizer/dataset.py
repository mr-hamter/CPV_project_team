"""Lưu văn bản đang soạn, lịch sử đã gửi và kết quả đo thử."""
import csv
import json
from pathlib import Path
from .config import DATA_DIR


class DatasetManager:
    def __init__(self, directory=DATA_DIR):
        self.directory = Path(directory)
        self.path = self.directory / 'session.json'
        self.text = ''
        self.history = []
        self.warning = ''
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                text, history = data['text'], data['history']
                if not isinstance(text, str) or not all(isinstance(s, str) for s in history):
                    raise ValueError('sai định dạng')
                self.text, self.history = text, list(history)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                # Không ghi đè file hỏng, lưu phiên mới sang file khác
                self.warning = f'Không đọc được phiên cũ ({exc}), đã bắt đầu phiên mới.'
                self.path = self.directory / 'session-new.json'

    def save(self, text, history):
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps({'text': text, 'history': history}, ensure_ascii=False, indent=2),
                        encoding='utf-8')
        temp.replace(self.path)
        self.text, self.history = text, list(history)

    def record_trial(self, expected, actual, elapsed, contact_expected, contact_actual, mode, condition):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / 'trials.csv'
        exists = path.exists() and path.stat().st_size > 0
        with path.open('a', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            if not exists:
                writer.writerow(['expected', 'actual', 'seconds', 'contact_expected', 'contact_actual', 'mode', 'condition'])
            writer.writerow([expected, actual, elapsed, int(contact_expected), int(contact_actual), mode, condition])
        return path
