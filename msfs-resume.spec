# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / "launch.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "vendor" / "SimConnect.dll"), "vendor"),
        (str(root / "vendor" / "SimConnect_2024.dll"), "vendor"),
        (str(root / "LICENSE.txt"), "."),
        (str(root / "CHANGELOG.md"), "."),
        (str(root / "HELP.md"), "."),
        (str(root / "version.json"), "."),
        (str(root / "assets" / "msfs-resume.ico"), "assets"),
    ],
    hiddenimports=["pystray._win32", "PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PIL.AvifImagePlugin",
        "PIL.WebPImagePlugin",
        "PIL.FtexImagePlugin",
        "PIL.ImageCms",
        "PIL.ImageTk",
        "PIL.ImageQt",
    ],
    noarchive=False,
)

# Pillow pulls in AVIF/WebP/FreeType codecs we do not use (AVIF alone is ~7.5 MB).
_DROP_PIL = ("_avif", "_webp", "_imagingcms", "_imagingft", "_imagingtk")
a.binaries = [
    item for item in a.binaries
    if not any(name in item[0].replace("\\", "/").lower() for name in _DROP_PIL)
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MSFSResume",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(root / "assets" / "msfs-resume.ico") if (root / "assets" / "msfs-resume.ico").exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MSFSResume",
)
