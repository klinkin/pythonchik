# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pythonchik/main.py'],
    pathex=[],
    binaries=[('/opt/homebrew/opt/tcl-tk/lib/libtcl9.0.dylib', 'lib'), ('/opt/homebrew/opt/tcl-tk/lib/libtcl9tk9.0.dylib', 'lib')],
    datas=[('pythonchik', 'pythonchik')],
    hiddenimports=['tkinter'],
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
    name='pythonchik',
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
app = BUNDLE(
    exe,
    name='pythonchik.app',
    icon=None,
    bundle_identifier=None,
)
