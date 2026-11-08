"""Đọc camera và chạy MediaPipe trên luồng riêng để giao diện không bị giật."""
import threading
import time
import cv2

WIDTH, HEIGHT = 640, 480
EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
         (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
         (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def make_detector():
    import mediapipe as mp
    return mp.solutions.hands.Hands(max_num_hands=2, model_complexity=0,
                                    min_detection_confidence=.65, min_tracking_confidence=.65)


def find_hands(detector, rgb):
    h, w = rgb.shape[:2]
    result = detector.process(rgb)
    hands = []
    for marks, info in zip(result.multi_hand_landmarks or [], result.multi_handedness or []):
        side = info.classification[0].label.lower()
        hands.append((side, [(p.x * w, p.y * h) for p in marks.landmark]))
    return hands


def draw_hand(rgb, points):
    pts = [(round(x), round(y)) for x, y in points]
    for a, b in EDGES:
        cv2.line(rgb, pts[a], pts[b], (120, 220, 160), 2)
    for pt in pts:
        cv2.circle(rgb, pt, 3, (255, 255, 255), -1)


class HandCamera:
    """Luồng nền: đọc khung hình -> lật gương -> tìm tay -> vẽ khung xương.

    Giao diện chỉ lấy kết quả mới nhất bằng read_latest(), không phải chờ MediaPipe.
    """

    def __init__(self, index=0, open_capture=cv2.VideoCapture, detector_factory=make_detector):
        self.index = index
        self.open_capture = open_capture
        self.detector_factory = detector_factory
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.latest = None
        self.failed = False
        self.error = ''
        self.thread = threading.Thread(target=self._run, name='hand-camera', daemon=True)
        self.thread.start()

    def _run(self):
        capture = detector = None
        try:
            # Mở camera và nạp mô hình ở đây để cửa sổ hiện ra ngay
            capture = self.open_capture(self.index)
            if not capture.isOpened():
                raise RuntimeError('Không mở được camera. Kiểm tra quyền hoặc ứng dụng khác đang dùng camera.')
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            detector = self.detector_factory()
            failures = 0
            while not self.stop.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    failures += 1
                    if failures >= 10:
                        raise RuntimeError('Không đọc được hình ảnh từ camera.')
                    self.stop.wait(.03)
                    continue
                failures = 0
                captured = time.monotonic()
                if frame.shape[:2] != (HEIGHT, WIDTH):
                    frame = cv2.resize(frame, (WIDTH, HEIGHT))
                rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                hands = find_hands(detector, rgb)
                for _, points in hands:
                    draw_hand(rgb, points)
                with self.lock:
                    self.latest = (rgb, hands, captured)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if capture is not None:
                capture.release()
            if detector is not None:
                detector.close()
            self.failed = True

    def read_latest(self):
        with self.lock:
            latest, self.latest = self.latest, None
        return latest

    def release(self):
        self.stop.set()
        self.thread.join(timeout=1)
