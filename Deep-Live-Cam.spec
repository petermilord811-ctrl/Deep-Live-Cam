# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a self-contained Deep-Live-Cam (onedir) build.

Produces dist/Deep-Live-Cam/ containing:
    Deep-Live-Cam.exe   + _internal/ (all DLLs and Python packages)
Models (inswapper_128.onnx, gfpgan-1024.onnx, buffalo_l/) and ffmpeg are
staged beside the exe by build_standalone.ps1 — they are resolved at runtime
via modules.paths (frozen-aware), not bundled into the archive.

Build:  python -m PyInstaller Deep-Live-Cam.spec --noconfirm
"""

import os
import glob
import site

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# --- Heavy third-party packages PyInstaller can't fully trace statically ---
for pkg in [
    "onnxruntime",          # GPU provider DLLs + capi
    "insightface",          # FaceAnalysis / model_zoo
    "cv2",
    "skimage",              # used by insightface face alignment
    "scipy",
    "sklearn",              # KMeans in cluster_analysis
    "cv2_enumerate_cameras",
    "pygrabber",            # DirectShow camera enumeration (Windows)
    "pyvirtualcam",
    "comtypes",             # pygrabber dependency
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # noqa: BLE001
        print(f"[spec] collect_all('{pkg}') skipped: {exc}")

hiddenimports += collect_submodules("insightface")
hiddenimports += [
    "onnxruntime.capi._pybind_state",
    "sklearn.utils._typedefs",
    "sklearn.neighbors._partition_nodes",
    # Frame processors are loaded dynamically via importlib.import_module()
    # (modules/processors/frame/core.py), so PyInstaller's static analysis
    # misses them. List every one explicitly or the UI's enhancer/swapper
    # selection silently fails with "Frame processor ... not found".
    "modules.processors.frame.face_swapper",
    "modules.processors.frame.face_enhancer",
    "modules.processors.frame.face_enhancer_gpen256",
    "modules.processors.frame.face_enhancer_gpen512",
    "modules.processors.frame._onnx_enhancer",
]

# --- NVIDIA CUDA / cuDNN / cuBLAS DLLs from the nvidia-*-cu12 wheels ---
# Shipped under nvidia/<pkg>/bin so run.py's frozen DLL-dir registration finds them.
_site_dirs = list(site.getsitepackages())
_user_site = site.getusersitepackages()
if _user_site:
    _site_dirs.append(_user_site)

_nvidia_added = 0
for _sp in _site_dirs:
    _nvidia_root = os.path.join(_sp, "nvidia")
    if not os.path.isdir(_nvidia_root):
        continue
    for _sub in os.listdir(_nvidia_root):
        _bindir = os.path.join(_nvidia_root, _sub, "bin")
        if not os.path.isdir(_bindir):
            continue
        for _dll in glob.glob(os.path.join(_bindir, "*.dll")):
            binaries.append((_dll, os.path.join("nvidia", _sub, "bin")))
            _nvidia_added += 1
    break
print(f"[spec] bundled {_nvidia_added} NVIDIA CUDA DLLs")

# --- Things we deliberately leave out (not installed and/or feature disabled) ---
excludes = [
    "tensorflow", "tensorflow_intel", "keras", "tensorboard",  # NSFW only; guarded import
    "opennsfw2",                                                # NSFW filter (off by default)
    "torch", "torchvision", "torchaudio",                      # not installed
    "matplotlib", "tkinter",
    "PyQt5", "PyQt6",
    # Unused Qt subsystems — huge and never imported
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuick3D",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtMultimedia",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtDesigner",
    "PySide6.QtPdf", "PySide6.QtPositioning", "PySide6.QtSensors",
    "IPython", "notebook", "jupyter", "pytest",
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Deep-Live-Cam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="Deep-Live-Cam.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Deep-Live-Cam",
)
