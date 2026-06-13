"""Init context for tests to include project root folder to path."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import common  # noqa: F401
