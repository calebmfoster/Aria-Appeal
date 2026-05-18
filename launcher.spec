# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Aria Appeal Dev Launcher
# Build: pyinstaller launcher.spec --clean
# Output: dist\AriaAppealLauncher.exe

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[r'D:\\Repo\\Aria Appeal'],
    binaries=[],
    datas=[],
    hiddenimports=['tkinter', 'tkinter.scrolledtext', 'tkinter.font', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'transformers', 'numpy', 'scipy',
        'PIL', 'cv2', 'matplotlib', 'pandas',
    ],
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
    name='AriaAppealLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # windowed — no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # set to an .ico path here if you have one
)
