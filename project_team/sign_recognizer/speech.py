"""Speech runs off the UI thread; failures are delivered to the UI."""
import queue
import sys
import threading


def speak_windows(text):
    """Synchronous SAPI on the worker's own COM apartment, one voice per job.

    Avoid pyttsx3's reusable SAPI event loop: a stale end-of-stream event
    can end a later runAndWait before that utterance has actually finished.
    Flag 16 treats user text as plain text, not SAPI XML.
    """
    import pythoncom
    from win32com.client import Dispatch

    pythoncom.CoInitialize()
    voice = None
    try:
        voice = Dispatch('SAPI.SpVoice')
        voice.Rate = -2
        voice.Speak(text, 16)
    finally:
        voice = None
        pythoncom.CoUninitialize()


class Speaker:
    def __init__(self):
        self.jobs = queue.Queue(maxsize=1)
        self.results = queue.Queue()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        engine = None
        while True:
            text = self.jobs.get()
            if text is None:
                break
            try:
                if sys.platform == 'win32':
                    speak_windows(text)
                else:
                    if engine is None:
                        import pyttsx3
                        engine = pyttsx3.init()
                        engine.setProperty('rate', 150)
                    engine.say(text)
                    engine.runAndWait()
                self.results.put((text, None))
            except Exception as exc:
                self.results.put((text, str(exc)))
                engine = None
        if engine:
            engine.stop()

    def speak(self, text):
        self.jobs.put_nowait(text)

    def close(self):
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass
