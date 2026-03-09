# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sistema de Restaurante
Builds a standalone Windows executable with all Django assets
"""

import os
import sys
from pathlib import Path

block_cipher = None

# Get base directory
BASE_DIR = Path(SPECPATH)

# Collect all Django templates
templates_datas = []
templates_dir = BASE_DIR / 'templates'
for root, dirs, files in os.walk(templates_dir):
    for file in files:
        src = Path(root) / file
        dest_dir = Path(root).relative_to(BASE_DIR)
        templates_datas.append((str(src), str(dest_dir)))

# Collect all static files
static_datas = []
static_dir = BASE_DIR / 'static'
if static_dir.exists():
    for root, dirs, files in os.walk(static_dir):
        for file in files:
            src = Path(root) / file
            dest_dir = Path(root).relative_to(BASE_DIR)
            static_datas.append((str(src), str(dest_dir)))

# Collect migrations
migrations_datas = []
migrations_dir = BASE_DIR / 'restaurante' / 'migrations'
if migrations_dir.exists():
    for root, dirs, files in os.walk(migrations_dir):
        for file in files:
            if file.endswith('.py'):
                src = Path(root) / file
                dest_dir = Path(root).relative_to(BASE_DIR)
                migrations_datas.append((str(src), str(dest_dir)))

# Collect media folder structure (empty folders)
media_dir = BASE_DIR / 'media'
if not media_dir.exists():
    media_dir.mkdir(parents=True, exist_ok=True)

# Database file
db_file = BASE_DIR / 'db.sqlite3'
db_data = []
if db_file.exists():
    db_data.append((str(db_file), '.'))

# Media files (product images, settings)
media_datas = []
media_dir = BASE_DIR / 'media'
if media_dir.exists():
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            if not file.startswith('.'):
                src = Path(root) / file
                dest_dir = Path(root).relative_to(BASE_DIR)
                media_datas.append((str(src), str(dest_dir)))

# .env.example
env_example = BASE_DIR / '.env.example'
env_data = []
if env_example.exists():
    env_data.append((str(env_example), '.'))

# Combine all data files
datas = templates_datas + static_datas + migrations_datas + media_datas + db_data + env_data + [
    (str(BASE_DIR / 'requirements.txt'), '.'),
]

# Hidden imports for Django and dependencies
hiddenimports = [
    'django',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.core.management',
    'django.core.management.commands',
    'django.db.backends.sqlite3',
    'django.db.backends.postgresql',
    'waitress',
    'daphne',
    'channels',
    'channels.routing',
    'channels.auth',
    'channels_redis',
    'redis',
    'psycopg2',
    'qrcode',
    'PIL',
    'crispy_forms',
    'crispy_forms.templatetags',
    'crispy_forms.templatetags.crispy_forms_tags',
    'crispy_forms.templatetags.crispy_forms_field',
    'crispy_bootstrap5',
    'crispy_bootstrap5.bootstrap5',
    'billar_project',
    'billar_project.settings',
    'billar_project.urls',
    'billar_project.wsgi',
    'billar_project.asgi',
    'billar_project.routing',
    'restaurante',
    'restaurante.models',
    'restaurante.views',
    'restaurante.admin',
    'restaurante.forms',
    'restaurante.urls',
    'restaurante.consumers',
    'restaurante.realtime',
    'restaurante.signals',
    'restaurante.context_processors',
]

a = Analysis(
    [str(BASE_DIR / 'deploy' / 'windows' / 'launcher.py')],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'jupyter',
        'notebook',
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
    [],
    exclude_binaries=True,
    name='SistemaRestaurante',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add your .ico file path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SistemaRestaurante',
)
