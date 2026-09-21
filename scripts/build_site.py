from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

if DIST.exists():
    shutil.rmtree(DIST)

shutil.copytree(ROOT / "site", DIST)
shutil.copytree(ROOT / "data/public", DIST / "data")
print(f"Built static site at {DIST}")
