# -*- mode: python ; coding: utf-8 -*-

# ===================================================================
#  File di Specifiche PyInstaller Definitivo per Meridiana 1.0
# ===================================================================

a = Analysis(
    ['gui_main.py'],  # Lo script Python principale da cui partire
    pathex=[],
    binaries=[],
    datas=[
        # Sezione FONDAMENTALE per includere cartelle e file non Python.
        # La sintassi è ('sorgente', 'destinazione nel pacchetto')
        ('resources', 'resources'),
        ('styles', 'styles'),
        ('sql_scripts', 'sql_scripts')
    ],
    hiddenimports=[
        # Moduli che PyInstaller potrebbe non trovare automaticamente.
        'psycopg2._psycopg',
        'PyQt5.sip',
        'PyQt5.QtSvg',
        'PyQt5.QtWebEngineWidgets',
        'pandas',
        'openpyxl',
        'fpdf',
        'keyring.backends.Windows' # Assicura la compatibilità con il portachiavi di Windows
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
    console=False, # IMPORTANTISSIMO: Nasconde la finestra di console nera
    icon='resources/logo_meridiana.ico' # Percorso del file icona (.ico)
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