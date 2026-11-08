"""Bàn tay giả lập 21 điểm (lòng bàn tay hướng vào camera) để test không cần camera."""
from types import SimpleNamespace

HAND = [(0.52, .96), (.31, .78), (.20, .61), (.12, .45), (.05, .29),
        (.34, .51), (.32, .32), (.30, .15), (.29, .04),
        (.51, .47), (.51, .26), (.51, .10), (.51, .00),
        (.68, .49), (.70, .29), (.71, .15), (.72, .05),
        (.83, .56), (.89, .40), (.93, .29), (.96, .20)]


def make_hand(size=200, x0=200, y0=50):
    return [(x0 + x * size, y0 + y * size) for x, y in HAND]


def make_fist(hand):
    fist = list(hand)
    for mcp, tip in ((5, 8), (9, 12), (13, 16), (17, 20)):
        fist[tip] = hand[mcp]
    return fist


def lerp(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


class FakeDetector:
    """Giả lập mp.solutions.hands.Hands: trả về các tay trong self.hands (tọa độ pixel)."""

    def __init__(self, hands=None):
        self.hands = hands or {}
        self.closed = False

    def process(self, frame):
        h, w = frame.shape[:2]
        return SimpleNamespace(
            multi_hand_landmarks=[SimpleNamespace(landmark=[SimpleNamespace(x=x / w, y=y / h) for x, y in points])
                                  for points in self.hands.values()],
            multi_handedness=[SimpleNamespace(classification=[SimpleNamespace(label=side.title(), score=.99)])
                              for side in self.hands])

    def close(self):
        self.closed = True
