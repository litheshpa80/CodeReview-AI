from pathlib import Path
import sys

# Ensure project root is importable in Vercel's serverless runtime.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.main import app
