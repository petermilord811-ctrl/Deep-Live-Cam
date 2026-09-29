"""Shared path constants for the Deep-Live-Cam project.

Frozen-aware: when running from a PyInstaller bundle the Python modules live
inside the embedded archive, so ``__file__`` no longer points at a real folder
on disk. In that case we anchor everything to the directory that contains the
executable (``dist/Deep-Live-Cam/``), where ``models/`` and ffmpeg ship beside
the exe. When running from source we keep the original repo-root resolution.
"""

import os
import sys


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller onedir: exe sits in the distribution folder, models/ beside it.
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ROOT_DIR = _app_dir()
MODELS_DIR = os.path.join(ROOT_DIR, "models")

# insightface resolves models at <root>/models/<name> (e.g. models/buffalo_l).
# Anchoring its root at ROOT_DIR keeps everything beside the exe when frozen,
# while staying ~/.insightface-free for portable installs.
INSIGHTFACE_ROOT = ROOT_DIR
