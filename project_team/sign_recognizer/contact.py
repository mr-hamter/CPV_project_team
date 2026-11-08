"""Một lần chạm chỉ được tính khi giữ đủ lâu rồi tách ra; mất dấu tay thì hủy."""


class ContactMachine:
    def __init__(self, dwell=.12, release=.10):
        self.dwell = dwell        # thời gian giữ tối thiểu (giây)
        self.release = release    # thời gian tách ra tối thiểu (giây)
        self.reset()

    def reset(self):
        self.candidate = self.active = None
        self.since = self.released = None
        self.armed = False        # chỉ nhận chạm sau khi tay đã mở ra

    def update(self, target, now, valid=True):
        """Trả về tên điểm vừa chạm xong (khi tách ra), nếu không thì None."""
        if not valid:
            self.reset()
            return None
        if not self.armed:
            if target is not None:
                self.released = None
            elif self.released is None:
                self.released = now
            elif now - self.released >= self.release:
                self.armed, self.released = True, None
            return None
        if self.active is not None:
            if target is not None:
                self.released = None
                return None
            if self.released is None:
                self.released = now
            if now - self.released < self.release:
                return None
            done = self.active
            self.candidate = self.active = None
            self.since = self.released = None
            return done
        if target != self.candidate:
            self.candidate, self.since = target, now
        if target is not None and now - self.since >= self.dwell:
            self.active = target
        return None
