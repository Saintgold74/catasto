# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('styles', 'styles'),
        ('sql_scripts', 'sql_scripts')
    ],
    hiddenimports=[
        'psycopg2._psycopg',
        'PyQt5.sip',
        'PyQt5.QtSvg',
        'pandas',
        'openpyxl',
        'fpdf'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Meridiana',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Molto importante per le app GUI
    icon='resources/logo_meridiana.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meridiana'
)