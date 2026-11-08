"""Chuyển 21 điểm bàn tay (MediaPipe) thành lệnh: 1, 2, CONFIRM, SEND, SPACE, BACKSPACE."""
import math
from .contact import ContactMachine

# Đầu ngón cái (điểm 4) chạm vào đầu ngón nào thì ra lệnh tương ứng
TIPS = {'1': 8, '2': 12, 'CONFIRM': 16, 'SEND': 20}
NAMES = {'1': '1', '2': '2', 'CONFIRM': 'xác nhận', 'SEND': 'gửi', 'BACKSPACE': 'xóa'}


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def is_fist(p):
    """Cả 4 ngón đều gập: đầu ngón gần cổ tay và gần gốc ngón hơn khớp giữa."""
    for mcp, pip, tip in ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)):
        if distance(p[tip], p[0]) >= distance(p[pip], p[0]) * 1.12:
            return False
        if distance(p[tip], p[mcp]) >= distance(p[pip], p[mcp]) * 1.65:
            return False
    return True


def thumb_on_palm(p):
    """Vị trí đầu ngón cái so với lòng bàn tay.

    u = 0 ở gốc ngón trỏ (điểm 5), u = 1 ở gốc ngón út (điểm 17).
    v = khoảng cách tới đường nối hai gốc ngón, dương về phía cổ tay.
    Cả hai chia cho độ rộng bàn tay nên không phụ thuộc tay xa hay gần camera.
    """
    ax, ay = p[5]
    dx, dy = p[17][0] - ax, p[17][1] - ay
    width2 = dx * dx + dy * dy or 1
    tx, ty = p[4][0] - ax, p[4][1] - ay
    u = (tx * dx + ty * dy) / width2
    v = (dx * ty - dy * tx) / width2
    # Tay trái/phải cho dấu ngược nhau, nên lấy cổ tay làm chiều dương
    if dx * (p[0][1] - ay) - dy * (p[0][0] - ax) < 0:
        v = -v
    return u, v


class PalmSwipe:
    """Vuốt ngón cái trên lòng bàn tay từ gốc ngón trỏ sang gốc ngón út = dấu cách."""
    START, END = .25, .8    # vùng bắt đầu / kết thúc theo u
    MAX_TIME = 1.0          # phải vuốt xong trong 1 giây

    def __init__(self):
        self.started = None
        self.last_seen = None

    def reset(self):
        self.started = None

    def update(self, u, v, now):
        if not (-.3 <= u <= 1.3 and -.25 <= v <= 1.0):
            # Ngón cái rời lòng bàn tay; bỏ qua vài khung nhiễu ngắn
            if self.started is not None and now - self.last_seen > .2:
                self.started = None
            return False
        self.last_seen = now
        if u <= self.START:
            self.started = now
        elif u >= self.END and self.started is not None:
            done = now - self.started <= self.MAX_TIME
            self.started = None
            return done
        return False


class GestureProcessor:
    def __init__(self, threshold=.28):
        self.threshold = threshold   # khoảng cách chạm / kích thước lòng bàn tay
        self.contact = ContactMachine()
        self.swipe = PalmSwipe()
        self.hand = None             # 21 điểm của bàn tay đang dùng
        self.side = None
        self.target = None
        self.last_time = None
        self.status = 'Đưa một bàn tay vào camera.'

    def reset(self):
        self.contact.reset()
        self.swipe.reset()
        self.target = None

    def nearest_tip(self, p, scale):
        ranked = sorted((distance(p[4], p[i]) / scale, name) for name, i in TIPS.items())
        limit = self.threshold * (1.35 if self.contact.active else 1)
        if ranked[0][0] > limit:
            return None, True
        if ranked[1][0] - ranked[0][0] < .07:
            return None, False       # ngón cái nằm giữa hai đầu ngón, không chắc chạm ngón nào
        return ranked[0][1], True

    def update(self, hands, now):
        """hands: danh sách (trái/phải, 21 điểm). Trả về danh sách lệnh vừa nhận được."""
        if self.last_time is not None and now - self.last_time > .5:
            self.reset()             # mất hình quá lâu thì hủy thao tác đang dở
        self.last_time = now
        self.hand = self.target = None
        if len(hands) != 1:
            self.reset()
            self.side = None
            self.status = ('Chỉ đưa MỘT bàn tay vào camera.' if hands
                           else 'Đưa một bàn tay vào camera, mở tay để bắt đầu.')
            return []
        side, p = hands[0]
        if side != self.side:
            self.reset()             # không chuyển thao tác đang dở sang tay khác
            self.side = side
        self.hand = p
        palm = (sum(p[i][0] for i in (5, 9, 13, 17)) / 4, sum(p[i][1] for i in (5, 9, 13, 17)) / 4)
        scale = distance(palm, p[0])
        if scale < 25:
            self.reset()
            self.status = 'Đưa tay lại gần camera hơn.'
            return []

        events = []
        if is_fist(p):
            self.swipe.reset()
            if 'BACKSPACE' not in (self.contact.active, self.contact.candidate):
                self.contact.active = self.contact.candidate = None   # nắm tay hủy cú chạm đang dở
            target, valid = 'BACKSPACE', True
        else:
            target, valid = self.nearest_tip(p, scale)
            if target is None and valid:
                if self.swipe.update(*thumb_on_palm(p), now):
                    events.append('SPACE')
            else:
                self.swipe.reset()
        self.target = target
        done = self.contact.update(target, now, valid)
        if done:
            events.append(done)

        if target == 'BACKSPACE':
            self.status = 'Nắm tay: mở tay ra để xóa dấu cuối của mã.'
        elif not valid:
            self.status = 'Tách rõ các đầu ngón tay.'
        elif target:
            self.status = f'Đang chạm: {NAMES[target]} – tách ra để nhập.'
        elif self.swipe.started is not None:
            self.status = 'Đang vuốt sang ngón út...'
        elif not self.contact.armed:
            self.status = 'Mở tay ra để bắt đầu.'
        else:
            self.status = 'Sẵn sàng.'
        return events
