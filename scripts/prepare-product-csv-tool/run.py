"""WRYDECO native Shopify CSV authoring tool. Run with --help."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wry_csv.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
