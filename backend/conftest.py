# Ensures pytest (run from any cwd) can import the `app` package
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
