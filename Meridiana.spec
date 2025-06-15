# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
	# Includi la cartella 'styles' per il tuo stylesheet
        ('styles', 'styles'),

        # Includi la cartella 'resources' per il logo e il manuale
        ('resources', 'resources'),

        # Includi il file di configurazione
        ('config.py', '.'), # Includi config.py nella root dell'eseguibile

        # Aggiungi qui altre cartelle o file se ne hai (es. 'dialogs', 'custom_widgets')
        # PyInstaller di solito include automaticamente i moduli importati, ma a volte 'datas' è più sicuro
        ('dialogs.py', '.'),
        ('custom_widgets.py', '.'),
        ('app_utils.py', '.'),
        ('fuzzy_search_unified.py', '.'),
        ('gui_widgets.py', '.'),],
    hiddenimports=[
		'psycopg2._psycopg', # Per assicurare che la parte C di psycopg2 sia inclusa
        'pandas._libs.interval', # A volte pandas ha bisogno di questo
        'pandas._libs.tslibs.np_datetime', # E questo
        'openpyxl', # La libreria openpyxl
        'fpdf', # fpdf2 si importa come fpdf
        'bcrypt', # bcrypt
		'defusedxml'
		'et_xmlfile'
		'fonttools'
		'pillow'
		'numpy'
		'PyQt5'
		'PyQt5-Qt5'
		'PyQt5_sip'
		'PyQtWebEngine'
		'PyQtWebEngine-Qt5'
		'python-dateutil'
		'pytz'
		'six'
		'tzdata'
        # Aggiungi qui qualsiasi modulo che PyInstaller potrebbe non rilevare automaticamente
        # es. se usi importlib.import_module() o moduli che non sono direttamente importati nello script principale.
    ],
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
    a.zipfiles,
    a.datas,
    [],
    exclude_binaries=True,
    name='Meridiana',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meridiana',
)
