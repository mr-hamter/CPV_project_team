import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sign_recognizer.speech import Speaker, speak_windows


class SpeechTest(unittest.TestCase):
    def test_repeated_jobs_and_recovery_after_failure(self):
        spoken = []
        def speak(text):
            if text == 'FAIL':
                raise RuntimeError('audio unavailable')
            spoken.append(text)
        with patch('sign_recognizer.speech.sys.platform', 'win32'), \
                patch('sign_recognizer.speech.speak_windows', side_effect=speak):
            worker = Speaker()
            try:
                for text in ('FIRST', 'SECOND', 'FAIL', 'THIRD', 'THIRD'):
                    worker.speak(text)
                    result, error = worker.results.get(timeout=3)
                    self.assertEqual(result, text)
                    self.assertEqual(error, 'audio unavailable' if text == 'FAIL' else None)
                self.assertEqual(spoken, ['FIRST', 'SECOND', 'THIRD', 'THIRD'])
            finally:
                worker.close()
                worker.thread.join(timeout=3)
            self.assertFalse(worker.thread.is_alive())

    def test_success_only_reported_after_speech_returns(self):
        started, finish = threading.Event(), threading.Event()
        def speak(text):
            started.set()
            if not finish.wait(3):
                raise RuntimeError('test timeout')
        with patch('sign_recognizer.speech.sys.platform', 'win32'), \
                patch('sign_recognizer.speech.speak_windows', side_effect=speak):
            worker = Speaker()
            try:
                worker.speak('HELLO')
                self.assertTrue(started.wait(3))
                with self.assertRaises(queue.Empty):
                    worker.results.get_nowait()
                finish.set()
                self.assertEqual(worker.results.get(timeout=3), ('HELLO', None))
            finally:
                finish.set()
                worker.close()
                worker.thread.join(timeout=3)

    def test_com_lifecycle_plain_text_and_error_cleanup(self):
        com = SimpleNamespace(CoInitialize=Mock(), CoUninitialize=Mock())
        voices = [Mock(), Mock(), Mock()]
        voices[1].Speak.side_effect = RuntimeError('device failed')
        dispatch = Mock(side_effect=voices)
        with patch.dict('sys.modules', {'pythoncom': com,
                                      'win32com.client': SimpleNamespace(Dispatch=dispatch)}):
            speak_windows('A < B')
            with self.assertRaisesRegex(RuntimeError, 'device failed'):
                speak_windows('SECOND')
            speak_windows('THIRD')
        self.assertEqual(com.CoInitialize.call_count, 3)
        self.assertEqual(com.CoUninitialize.call_count, 3)
        self.assertEqual(dispatch.call_count, 3)
        voices[0].Speak.assert_called_once_with('A < B', 16)
        voices[2].Speak.assert_called_once_with('THIRD', 16)
