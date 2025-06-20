# -*- mode: python ; coding: utf-8 -*-

# Blocco di analisi principale
a = Analysis(
    ['gui_main.py'],  # Lo script di avvio dell'applicazione.
    pathex=['.'],  # Il percorso radice del progetto.
    binaries=[],
    datas=[
        ('resources', 'resources'),  # Include l'intera cartella 'resources'.
        ('styles', 'styles')        # Include l'intera cartella 'styles'.
    ],
    hiddenimports=[
        'psycopg2._psycopg'  # Importazione nascosta per il corretto funzionamento del driver PostgreSQL.
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Crea l'archivio Python con gli script compilati.
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Crea l'eseguibile (.exe).
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Meridiana',  # Il nome del file .exe finale.
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Impostato a False per applicazioni GUI (nasconde la console).
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/logo_meridiana.ico',  # Percorso dell'icona dell'applicazione.
    version='file_version_info.txt'  # File per i metadati dell'eseguibile.
)

# Raccoglie tutti i file (eseguibile, librerie, dati) in un'unica cartella.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meridiana'  # Il nome della cartella di output che conterrà l'applicazione.
)