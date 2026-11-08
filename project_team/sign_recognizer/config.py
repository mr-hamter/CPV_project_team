from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ERROR_LOG = BASE_DIR / 'sign_error.log'
DATA_DIR = BASE_DIR.parent / 'data'
