# -*- mode: python ; coding: utf-8 -*-
# Compilar con:  pyinstaller Balidaf.spec   (o scripts\build_exe.bat)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/balidaf.ico', 'assets'), ('balidaf/web', 'balidaf/web')],
    hiddenimports=['webview', 'clr_loader', 'pythonnet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Balidaf',
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
    icon=['assets/balidaf.ico'],
)
