"""
main.py — Empacota o SAMU 192 como app desktop com pywebview.

Requisitos: Python 3.10+, Django, pywebview, whitenoise.
Instale (localmente) com:
    pip install django==5.1.4 pywebview whitenoise openpyxl reportlab

Rodando (modo dev):
    python main.py

Empacotando (.exe / .app / binário Linux):
    bash build_desktop.sh
    # ou manualmente:  pyinstaller samu192.spec --clean

O SQLite fica em `db.sqlite3` no diretório do executável, sem risco de perder
dados ao fechar. A exclusão só ocorre via interface do próprio sistema.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path


def _resource_base() -> Path:
    """Diretório de trabalho — considera empacotamento via PyInstaller."""
    if getattr(sys, "frozen", False):  # PyInstaller
        # sys._MEIPASS aponta para o diretório temporário com os assets;
        # o banco e arquivos de usuário ficam ao lado do executável.
        exe_dir = Path(sys.executable).resolve().parent
        os.environ["SAMU_ASSETS_BASE"] = str(Path(sys._MEIPASS))  # type: ignore[attr-defined]
        return exe_dir
    return Path(__file__).resolve().parent


BASE_DIR = _resource_base()
sys.path.insert(0, str(BASE_DIR))
# Quando empacotado, os módulos Django estão dentro de _MEIPASS:
if getattr(sys, "frozen", False):
    sys.path.insert(0, os.environ["SAMU_ASSETS_BASE"])

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "samu.settings")

import samu.settings as django_settings  # noqa: E402

# Modo desktop: URLs sem prefixo /api, sirva na raiz.
django_settings.FORCE_SCRIPT_NAME = None
# Banco no diretório do executável, sobrevive a atualizações do app.
django_settings.DATABASES["default"]["NAME"] = str(BASE_DIR / "db.sqlite3")
django_settings.STATIC_ROOT = str(BASE_DIR / "staticfiles")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402


def _prepare_database() -> None:
    call_command("migrate", "--noinput", verbosity=0)
    from core.models import Medicamento

    if Medicamento.objects.count() == 0:
        call_command("seed_samu", verbosity=1)


def _find_free_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _run_django(port: int) -> None:
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server

    application = get_wsgi_application()
    with make_server("127.0.0.1", port, application) as server:
        server.serve_forever()


def main() -> None:
    _prepare_database()

    port = _find_free_port(8765)
    thread = threading.Thread(target=_run_django, args=(port,), daemon=True)
    thread.start()

    # aguarda servidor
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    try:
        import webview  # type: ignore
    except ImportError:
        print(
            "\n[SAMU 192] Este script precisa da biblioteca 'pywebview' para abrir o app desktop.\n"
            "Instale com:  pip install pywebview\n"
            f"Enquanto isso o servidor está rodando em http://127.0.0.1:{port}/\n"
        )
        while True:
            time.sleep(3600)
        return

    webview.create_window(
        "SAMU 192 · Sistema de estoque",
        f"http://127.0.0.1:{port}/",
        width=1440,
        height=900,
        min_size=(1024, 720),
    )
    webview.start()


if __name__ == "__main__":
    main()
