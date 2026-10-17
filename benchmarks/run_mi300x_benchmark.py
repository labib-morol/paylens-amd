"""Thin wrapper for backwards-compatibility; delegates to run_benchmark.py."""
import sys
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from benchmarks.run_benchmark import main

if __name__ == "__main__":
    main()
