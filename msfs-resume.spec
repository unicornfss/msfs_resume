# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / "msfs_resume" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "vendor" / "SimConnect.dll"), "vendor"),
        (str(root / "vendor" / "SimConnect_2024.dll"), "vendor"),
        (str(root / "LICENSE.txt"), "."),
        (str(root / "CHANGELOG.md"), "."),
        (str(root / "HELP.md"), "."),
        (str(root / "version.json"), "."),
    ],
    hiddenimports=["pystray._win32", "PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
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
