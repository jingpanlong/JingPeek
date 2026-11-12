# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('licenses', 'licenses'), ('THIRD_PARTY_NOTICES.txt', '.')]
binaries = []
hiddenimports = ['comtypes.gen.UIAutomationClient', 'PySide6.QtSvg', 'win32timezone']
hiddenimports += collect_submodules('pygments.lexers')
hiddenimports += collect_submodules('pygments.styles')
hiddenimports += collect_submodules('comtypes.gen')
tmp_ret = collect_all('imageio_ffmpeg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pillow_heif')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'tkinter'],
    noarchive=False,
    optimize=0,
)
# Keep the independently executed renderer intact: do not analyze or relocate its
# DLLs as dependencies of the application's Python/Qt runtime.
a.datas += Tree('office_runtime', prefix='office_runtime', typecode='DATA')
pyz = PYZ(a.pure)
onefile = os.environ.get('JINGPEEK_ONEFILE') == '1'
if onefile:
    exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='JingPeek',console=False,
              strip=False,upx=False,icon='icon.ico')
else:
    exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='JingPeek',console=False,
              strip=False,upx=False,icon='icon.ico')
    coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='JingPeek')
