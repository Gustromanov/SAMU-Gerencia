# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — SAMU 192 Desktop.

Uso:
    bash build_desktop.sh        (Linux/macOS/Git Bash)
    build_windows.bat            (Windows)
    pyinstaller samu192.spec --clean --noconfirm

Windows gera:  dist/SAMU192/SAMU192.exe   (ícone assets/icons/samu192.ico)
macOS gera:    dist/SAMU 192.app          (ícone assets/icons/samu192.icns)
Linux gera:    dist/SAMU192/SAMU192       (ícone da janela assets/icons/samu192.png)

Ícones: gerados a partir do SVG oficial com `python gerar_icones.py`.
O banco `db.sqlite3` é criado no primeiro run junto ao executável.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

BLOCK_CIPHER = None
BASE = Path(SPECPATH).resolve()  # noqa: F821 (PyInstaller injects SPECPATH)
ICONES = BASE / "assets" / "icons"


def _icone(nome):
    p = ICONES / nome
    return str(p) if p.exists() else None


datas = [
    (str(BASE / "templates"), "templates"),
    (str(BASE / "static"), "static"),
    (str(BASE / "core" / "migrations"), "core/migrations"),
]
if ICONES.exists():
    datas.append((str(ICONES), "assets/icons"))

# Firebase/Google Cloud leem a própria versão via metadata do pacote.
for pacote in ("firebase-admin", "google-cloud-storage", "google-cloud-firestore",
               "google-api-core", "google-auth", "grpcio"):
    try:
        datas += copy_metadata(pacote)
    except Exception:
        pass

hiddenimports = (
    collect_submodules("core")
    + collect_submodules("samu")
    + [
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
        "firebase_admin",
        "firebase_admin.storage",
        "firebase_admin.firestore",
        "google.cloud.storage",
        "google.cloud.firestore",
    ]
)

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
    icon=_icone("samu192.ico") if sys.platform.startswith("win") else None,
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
        icon=_icone("samu192.icns"),
        bundle_identifier="br.gov.samu.estoque",
        info_plist={
            "CFBundleDisplayName": "SAMU 192",
            "CFBundleShortVersionString": "1.1.0",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )
