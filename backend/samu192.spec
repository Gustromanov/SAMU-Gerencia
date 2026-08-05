# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — SAMU 192 Desktop.

Uso:
    pip install pyinstaller pywebview
    pyinstaller samu192.spec --clean

Windows gera:  dist/SAMU192.exe
macOS gera:    dist/SAMU 192.app  (defina --osx-bundle-identifier)
Linux gera:    dist/SAMU192       (binário)

Todos os assets (templates, static, migrations) são embarcados.
O banco `db.sqlite3` é criado no primeiro run junto ao executável.
"""
import sys
from pathlib import Path

BLOCK_CIPHER = None
BASE = Path(SPECPATH).resolve()  # noqa: F821 (PyInstaller injects SPECPATH)

datas = [
    (str(BASE / "templates"), "templates"),
    (str(BASE / "static"), "static"),
    (str(BASE / "core" / "migrations"), "core/migrations"),
]

hiddenimports = [
    "core",
    "core.apps",
    "core.admin",
    "core.forms",
    "core.models",
    "core.urls",
    "core.views",
    "core.exportacao",
    "core.context_processors",
    "core.management.commands.seed_samu",
    "samu.settings",
    "samu.urls",
    "samu.wsgi",
    "samu.asgi",
    "django.contrib.admin.apps",
    "django.contrib.auth.apps",
    "django.contrib.contenttypes.apps",
    "django.contrib.sessions.apps",
    "django.contrib.messages.apps",
    "django.contrib.staticfiles.apps",
    "django.template.loaders.app_directories",
    "django.template.loaders.filesystem",
    "whitenoise",
    "whitenoise.middleware",
    "whitenoise.storage",
    "openpyxl",
    "reportlab",
    "reportlab.pdfgen",
    "reportlab.platypus",
]

a = Analysis(  # noqa: F821
    ["main.py"],
    pathex=[str(BASE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SAMU192",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # sem console preto (Windows)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # substitua por 'samu.ico' se disponibilizar um ícone
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SAMU192",
)

# macOS bundle (executado apenas quando você builda em macOS)
if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="SAMU 192.app",
        icon=None,
        bundle_identifier="br.gov.samu.estoque",
        info_plist={
            "CFBundleDisplayName": "SAMU 192",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )
