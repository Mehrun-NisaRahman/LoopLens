import os
import sys
from pathlib import Path

os.environ["LOOPLENS_PROVIDER"] = "mock"  # tests never call a real model
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
