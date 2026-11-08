import json
import tempfile
import unittest
from pathlib import Path

from sign_recognizer.codebook import CODEBOOK, MAX_CODE_LENGTH, SYMBOL_CODES, CodeInput, build_codebook
from sign_recognizer.dataset import DatasetManager


class CodebookTest(unittest.TestCase):
    def test_short_codes_first(self):
        expected = ['1', '2', '11', '12', '21', '22',
                    '111', '112', '121', '122', '211', '212', '221', '222',
                    '1111', '1112', '1121', '1122', '1211', '1212',
                    '1221', '1222', '2111', '2112', '2121', '2122']
        self.assertEqual(list(CODEBOOK)[:26], expected)
        self.assertEqual(list(CODEBOOK.values())[:26], list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        self.assertEqual(SYMBOL_CODES['BACKSPACE'], '2211')
        self.assertNotIn('SPACE', SYMBOL_CODES)
        self.assertEqual(MAX_CODE_LENGTH, 4)
        self.assertEqual(list(build_codebook(range(31)))[-2:], ['2222', '11111'])

    def test_every_code_roundtrip(self):
        for code, value in CODEBOOK.items():
            entry = CodeInput()
            text = 'X'
            for digit in code:
                text, _ = entry.apply(digit, text)
            text, _ = entry.apply('CONFIRM', text)
            self.assertEqual(text, '' if value == 'BACKSPACE' else 'X' + value)
            self.assertEqual(entry.pending, '')

    def test_prefix_waits_for_confirm(self):
        entry = CodeInput()
        text, _ = entry.apply('1', '')
        text, _ = entry.apply('1', text)
        self.assertEqual(text, '')
        self.assertEqual(entry.apply('CONFIRM', text)[0], 'C')

    def test_overflow_and_empty_confirm_keep_text(self):
        entry = CodeInput()
        entry.pending = '2222'
        self.assertEqual(entry.apply('1', 'ABC')[0], 'ABC')
        self.assertEqual(entry.apply('CONFIRM', 'ABC')[0], 'ABC')
        self.assertEqual(entry.pending, '2222')
        self.assertEqual(CodeInput().apply('CONFIRM', 'ABC')[0], 'ABC')

    def test_backspace_edits_code_only(self):
        entry = CodeInput()
        entry.pending = '121'
        self.assertEqual(entry.apply('BACKSPACE', 'ABC')[0], 'ABC')
        self.assertEqual(entry.pending, '12')
        self.assertEqual(entry.apply('CONFIRM', 'ABC')[0], 'ABCD')
        self.assertEqual(entry.apply('BACKSPACE', 'ABC')[0], 'ABC')

    def test_space_needs_empty_code(self):
        entry = CodeInput()
        self.assertEqual(entry.apply('SPACE', 'HI')[0], 'HI ')
        entry.apply('1', '')
        text, message = entry.apply('SPACE', 'HI')
        self.assertEqual(text, 'HI')
        self.assertEqual(entry.pending, '1')
        self.assertIn('chưa xác nhận', message)


class DatasetTest(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            DatasetManager(directory).save('HELLO', ['A', 'B'])
            store = DatasetManager(directory)
            self.assertEqual((store.text, store.history), ('HELLO', ['A', 'B']))

    def test_old_session_file_still_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'session.json').write_text(json.dumps(
                {'text': 'HI', 'history': ['X'], 'pending': '12', 'codebook_version': 2}), encoding='utf-8')
            store = DatasetManager(directory)
            self.assertEqual((store.text, store.history, store.warning), ('HI', ['X'], ''))

    def test_broken_session_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'session.json')
            path.write_text('{broken', encoding='utf-8')
            store = DatasetManager(directory)
            self.assertTrue(store.warning)
            store.save('NEW', [])
            self.assertEqual(path.read_text(encoding='utf-8'), '{broken')


if __name__ == '__main__':
    unittest.main()
