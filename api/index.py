import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import app

# Vercel WSGI entrypoint
app = app
