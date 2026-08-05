"""
server.py — ASGI entrypoint for Django (usado pelo supervisor via uvicorn).

O supervisor já roda `uvicorn server:app --host 0.0.0.0 --port 8001`. Este arquivo
faz o bootstrap do Django e expõe o ASGI application como `app`.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "samu.settings")

import django  # noqa: E402
django.setup()

# Garante schema atualizado apenas em contexto sync (subprocess fora do ASGI).
if os.environ.get("SAMU_SKIP_BOOTSTRAP") != "1":
    import subprocess
    try:
        subprocess.run(
            [sys.executable, "manage.py", "migrate", "--noinput"],
            cwd=str(BASE_DIR), check=False, capture_output=True, timeout=60,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[SAMU] Falha ao migrar: {exc}", file=sys.stderr)

from samu.asgi import application as app  # noqa: E402
