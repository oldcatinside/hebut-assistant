# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import os
import sys
from pathlib import Path
diagnostic = os.environ.get('TALK_DEBUG_CONSOLE') == '1'

# 仅从当前 Python、依赖及 Windows 系统目录解析 DLL。
# 开发机 PATH 中其他软件的 ICU / UCRT / OpenSSL DLL 不能混入发行包。
windows_dir = Path(os.environ.get('WINDIR', 'C:/Windows'))
os.environ['PATH'] = os.pathsep.join(str(p) for p in (
    Path(sys.executable).parent, Path(sys.base_prefix), Path(sys.base_prefix) / 'DLLs',
    windows_dir / 'System32', windows_dir,
))

a = Analysis(
    ['launcher.py'],
    pathex=[SPECPATH],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('xlrd') + collect_submodules('openpyxl') + ['pandas.io.excel._xlrd', 'pandas.io.excel._openpyxl'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'tkinter', 'matplotlib', 'scipy', 'IPython', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='talk-diagnostic' if diagnostic else '宣讲会信息助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=diagnostic,
    disable_windowed_traceback=False,
)
