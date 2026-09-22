"""Local API runner for Windows (stubs libmagic) on port 8011."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

mod = types.ModuleType("magic")
mod.from_buffer = lambda data, mime=False: "application/octet-stream"  # type: ignore[attr-defined]
sys.modules["magic"] = mod

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.chdir(ROOT)
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8011, reload=False, app_dir=str(SRC))
