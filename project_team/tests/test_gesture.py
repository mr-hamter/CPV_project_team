import unittest

from sign_recognizer.gesture import GestureProcessor, thumb_on_palm
from fake_hand import make_hand, make_fist, lerp


class GestureTest(unittest.TestCase):
    def setUp(self):
        self.g = GestureProcessor()
        self.hand = make_hand()
        self.now = 0
        self.events = []
        self.feed(self.hand, .3)

    def feed(self, points, seconds, side='right'):
        hands = [(side, points)] if points else []
        for _ in range(round(seconds / .02)):
            self.now += .02
            self.events.extend(self.g.update(hands, self.now))

    def thumb_at(self, pos):
        points = list(self.hand)
        points[4] = pos
        return points

    def swipe(self, start, end, seconds):
        steps = round(seconds / .02)
        for i in range(steps + 1):
            self.feed(self.thumb_at(lerp(start, end, i / steps)), .02)

    def palm_points(self):
        # Ngay dưới gốc ngón trỏ và gốc ngón út (lệch một chút về phía cổ tay)
        h = self.hand
        return lerp(h[5], h[0], .15), lerp(h[17], h[0], .15)

    def test_four_fingers_and_held_contact(self):
        for tip in (8, 12, 16, 20):
            count = len(self.events)
            self.feed(self.thumb_at(self.hand[tip]), 1)
            self.assertEqual(len(self.events), count)   # giữ lâu không lặp lệnh
            self.feed(self.hand, .2)
        self.assertEqual(self.events, ['1', '2', 'CONFIRM', 'SEND'])

    def test_loss_does_not_commit(self):
        self.feed(self.thumb_at(self.hand[8]), .3)
        self.feed(None, .1)
        self.feed(self.hand, .2)
        self.assertEqual(self.events, [])

    def test_two_hands_do_not_trigger(self):
        for _ in range(25):
            self.now += .02
            self.events.extend(self.g.update([('right', self.thumb_at(self.hand[20])), ('left', self.hand)], self.now))
        self.feed(self.hand, .2)
        self.assertEqual(self.events, [])

    def test_left_hand_works(self):
        self.feed(self.hand, .3, side='left')
        self.feed(self.thumb_at(self.hand[8]), .3, side='left')
        self.feed(self.hand, .2, side='left')
        self.assertEqual(self.events, ['1'])

    def test_motion_without_contact(self):
        for offset in range(30):
            self.feed([(x + offset, y + offset) for x, y in self.hand], .04)
        self.assertEqual(self.events, [])

    def test_fist_deletes_once_per_release(self):
        fist = make_fist(self.hand)
        self.feed(fist, 1)
        self.assertEqual(self.events, [])
        self.feed(self.hand, .3)
        self.feed(fist, .3)
        self.feed(self.hand, .3)
        self.assertEqual(self.events, ['BACKSPACE', 'BACKSPACE'])

    def test_fist_cancelled_by_tracking_loss(self):
        self.feed(make_fist(self.hand), .5)
        self.feed(None, .2)
        self.feed(self.hand, .3)
        self.assertEqual(self.events, [])

    def test_fist_overrides_unfinished_pinch(self):
        self.feed(self.thumb_at(self.hand[8]), .4)
        self.feed(make_fist(self.hand), .4)
        self.feed(self.hand, .4)
        self.assertEqual(self.events, ['BACKSPACE'])

    def test_palm_coordinates(self):
        start, end = self.palm_points()
        u, v = thumb_on_palm(self.thumb_at(start))
        self.assertLess(u, .25)
        self.assertGreater(v, 0)
        u, v = thumb_on_palm(self.thumb_at(end))
        self.assertGreater(u, .8)
        # Đầu các ngón nằm ngoài vùng lòng bàn tay
        for tip in (8, 12, 16, 20):
            self.assertLess(thumb_on_palm(self.thumb_at(self.hand[tip]))[1], -.25)

    def test_swipe_index_to_little_finger_is_space(self):
        start, end = self.palm_points()
        self.swipe(start, end, .4)
        self.feed(self.hand, .3)
        self.assertEqual(self.events, ['SPACE'])
        self.swipe(start, end, .4)
        self.assertEqual(self.events, ['SPACE', 'SPACE'])

    def test_swipe_works_for_mirrored_hand(self):
        mirrored = [(640 - x, y) for x, y in self.hand]
        self.hand = mirrored
        self.feed(mirrored, .3, side='left')
        start, end = self.palm_points()
        steps = 20
        for i in range(steps + 1):
            self.feed(self.thumb_at(lerp(start, end, i / steps)), .02, side='left')
        self.assertEqual(self.events, ['SPACE'])

    def test_reverse_or_slow_swipe_is_ignored(self):
        start, end = self.palm_points()
        self.swipe(end, start, .4)
        self.feed(self.hand, .5)
        self.swipe(start, end, 2.5)
        self.assertEqual(self.events, [])


if __name__ == '__main__':
    unittest.main()
