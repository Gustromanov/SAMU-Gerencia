"""
main.py — Empacota o SAMU 192 como app desktop com pywebview.

Requisitos: Python 3.10+, Django, pywebview, whitenoise.
Instale (localmente) com:
    pip install django==5.1.4 pywebview whitenoise

Rodando:
    python main.py

O SQLite fica em `db.sqlite3` no mesmo diretório, sem risco de perder dados
ao fechar. A exclusão só ocorre via interface do sistema.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "samu.settings")
# Local desktop: expor sem prefixo /api, direto na raiz.
os.environ["DJANGO_FORCE_SCRIPT_NAME"] = ""

# Reajuste dinâmico: quando rodando no desktop, remove o FORCE_SCRIPT_NAME.
import samu.settings as django_settings  # noqa: E402

django_settings.FORCE_SCRIPT_NAME = None

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402


def _prepare_database() -> None:
    call_command("migrate", "--noinput", verbosity=0)
    from core.models import Medicamento

    if Medicamento.objects.count() == 0:
        call_command("seed_samu", verbosity=1)


def _run_django(port: int = 8765) -> None:
    from django.core.wsgi import get_wsgi_application
    from wsgiref.simple_server import make_server

    application = get_wsgi_application()
    with make_server("127.0.0.1", port, application) as server:
        server.serve_forever()


def main() -> None:
    _prepare_database()

    port = 8765
    thread = threading.Thread(target=_run_django, args=(port,), daemon=True)
    thread.start()

    time.sleep(0.4)  # pequena espera para o servidor subir

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
