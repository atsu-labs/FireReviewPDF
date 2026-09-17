# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# プロジェクトアセットとQtAwesomeのデータファイルを収集
datas = [
    ('src/firereview/ui/assets', 'firereview/ui/assets'),
]
datas += collect_data_files('qtawesome')

# 隠しインポートの定義
hiddenimports = [
    'qtawesome',
    'fitz',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]
hiddenimports += collect_submodules('firereview')

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FireReviewPDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
