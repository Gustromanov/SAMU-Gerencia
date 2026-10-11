"""Backup do SQLite + snapshot do estoque no Firebase (Storage + Firestore), com modo simulado local."""
from __future__ import annotations

import gzip
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.utils import timezone

from . import models

MANTER_SIMULADOS = 10
INTERVALO_LOGIN_MIN = 10
PAUSA_APOS_FALHA_S = 900

_lock = threading.Lock()
_app = None
_app_chave = None
_agendador_iniciado = False


def pasta_dados() -> Path:
    return Path(settings.DATABASES["default"]["NAME"]).resolve().parent


def caminho_credenciais() -> Path:
    return pasta_dados() / "secrets" / "firebase-admin.json"


def pasta_simulada() -> Path:
    return pasta_dados() / "backups_firebase_simulado"


# ---------- Credenciais ----------
def credenciais_info() -> dict | None:
    p = caminho_credenciais()
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return {"project_id": d.get("project_id", "—"), "client_email": d.get("client_email", "—")}


def salvar_credenciais(conteudo: bytes) -> dict:
    try:
        d = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ValueError("Arquivo inválido: envie o JSON da conta de serviço baixado do console do Firebase.")
    faltando = [k for k in ("project_id", "private_key", "client_email") if not d.get(k)]
    if d.get("type") != "service_account" or faltando:
        raise ValueError("O JSON não é uma conta de serviço do Firebase (Configurações → Contas de serviço → Gerar nova chave privada).")
    from firebase_admin import credentials

    try:
        credentials.Certificate(d)
    except ValueError as exc:
        raise ValueError(f"Chave privada inválida no JSON: {exc}")
    p = caminho_credenciais()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(conteudo)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    _resetar_app()
    return {"project_id": d["project_id"], "client_email": d["client_email"]}


def remover_credenciais() -> None:
    caminho_credenciais().unlink(missing_ok=True)
    _resetar_app()


def _resetar_app() -> None:
    global _app, _app_chave
    if _app is not None:
        import firebase_admin

        try:
            firebase_admin.delete_app(_app)
        except ValueError:
            pass
    _app, _app_chave = None, None


def _obter_app(bucket: str):
    global _app, _app_chave
    import firebase_admin
    from firebase_admin import credentials

    p = caminho_credenciais()
    if not p.exists():
        raise RuntimeError("Credenciais do Firebase não enviadas. Faça upload do JSON da conta de serviço.")
    if not bucket:
        raise RuntimeError("Nome do bucket do Storage não configurado (ex.: seu-projeto.appspot.com).")
    chave = (p.stat().st_mtime, bucket)
    if _app is None or _app_chave != chave:
        _resetar_app()
        _app = firebase_admin.initialize_app(
            credentials.Certificate(str(p)), {"storageBucket": bucket}, name="samu192"
        )
        _app_chave = chave
    return _app


# ---------- Snapshot ----------
def gerar_snapshot() -> dict:
    medicamentos = []
    for m in models.Medicamento.objects.select_related("tipo", "forma").prefetch_related("lotes"):
        lotes = [{
            "codigo": l.codigo, "validade": l.validade.isoformat(), "quantidade": l.quantidade,
            "estoque": l.nivel_estoque_label, "validade_nivel": l.nivel_validade_label,
            "dias": l.dias_para_validade,
        } for l in m.lotes.all()]
        medicamentos.append({
            "nome": m.nome_exibicao, "tipo": m.tipo.nome, "forma": m.forma.nome,
            "total": sum(l["quantidade"] for l in lotes), "lotes": lotes,
        })
    veiculos = [{
        "codigo": v.codigo_id, "modelo": v.modelo, "ano": v.ano,
        "tipo": v.get_tipo_display(), "status": v.get_status_display(),
    } for v in models.Veiculo.objects.all()]
    return {
        "gerado_em": timezone.now().isoformat(),
        "kpis": {
            "medicamentos": len(medicamentos),
            "lotes": sum(len(m["lotes"]) for m in medicamentos),
            "unidades": sum(m["total"] for m in medicamentos),
            "veiculos": len(veiculos),
            "funcionarios": models.Funcionario.objects.count(),
        },
        "medicamentos": medicamentos,
        "veiculos": veiculos,
    }


def _copiar_banco_gz(destino: Path) -> None:
    copia = destino.with_suffix("")
    origem = sqlite3.connect(str(settings.DATABASES["default"]["NAME"]))
    alvo = sqlite3.connect(str(copia))
    with alvo:
        origem.backup(alvo)
    origem.close()
    alvo.close()
    with open(copia, "rb") as f_in, gzip.open(destino, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def _enviar_simulado(gz: Path, snapshot: dict) -> str:
    pasta = pasta_simulada()
    pasta.mkdir(parents=True, exist_ok=True)
    final = pasta / gz.name
    shutil.copy2(gz, final)
    (pasta / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    for antigo in sorted(pasta.glob("samu192-*.sqlite3.gz"))[:-MANTER_SIMULADOS]:
        antigo.unlink(missing_ok=True)
    return str(final)


def _enviar_firebase(bucket: str, gz: Path, snapshot: dict) -> str:
    from firebase_admin import firestore, storage

    app = _obter_app(bucket)
    caminho = f"samu192/backups/{gz.name}"
    storage.bucket(app=app).blob(caminho).upload_from_filename(str(gz), content_type="application/gzip")
    firestore.client(app=app).collection("samu192").document("snapshot").set(snapshot)
    return f"gs://{bucket}/{caminho}"


# ---------- Operações públicas ----------
def enviar_backup(origem: str, usuario=None, forcar_simulado: bool = False):
    """Executa um backup. Retorna o registro BackupFirebase ou None se já houver outro em andamento."""
    if not _lock.acquire(blocking=False):
        return None
    try:
        cfg = models.Configuracao.obter()
        modo = "SIMULADO" if (forcar_simulado or cfg.firebase_simulado) else "REAL"
        registro = models.BackupFirebase(origem=origem, modo=modo, usuario=usuario)
        try:
            nome = f"samu192-{timezone.localtime().strftime('%Y%m%d-%H%M%S')}.sqlite3.gz"
            snapshot = gerar_snapshot()
            with tempfile.TemporaryDirectory() as tmp:
                gz = Path(tmp) / nome
                _copiar_banco_gz(gz)
                registro.tamanho_bytes = gz.stat().st_size
                if modo == "SIMULADO":
                    registro.destino = _enviar_simulado(gz, snapshot)
                else:
                    registro.destino = _enviar_firebase(cfg.firebase_bucket, gz, snapshot)
            registro.status = "SUCESSO"
            registro.mensagem = (f"{snapshot['kpis']['medicamentos']} medicamentos, "
                                 f"{snapshot['kpis']['lotes']} lotes e {snapshot['kpis']['veiculos']} veículos.")
            cfg.firebase_ultimo_backup = timezone.now()
            cfg.save(update_fields=["firebase_ultimo_backup"])
        except Exception as exc:  # erro de rede/credencial vira registro no histórico
            registro.status = "ERRO"
            registro.mensagem = (str(exc) or exc.__class__.__name__)[:500]
        registro.save()
        return registro
    finally:
        _lock.release()


def testar_conexao() -> str:
    cfg = models.Configuracao.obter()
    if cfg.firebase_simulado:
        pasta = pasta_simulada()
        pasta.mkdir(parents=True, exist_ok=True)
        teste = pasta / ".teste"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        return f"Modo simulado OK — os backups serão gravados em {pasta}"
    from firebase_admin import firestore, storage

    app = _obter_app(cfg.firebase_bucket)
    storage.bucket(app=app).blob("samu192/_teste.txt").upload_from_string("ok")
    firestore.client(app=app).collection("samu192").document("_teste").set({"ok": True, "em": timezone.now().isoformat()})
    return f"Conectado ao projeto {credenciais_info()['project_id']} — Storage e Firestore OK."


def proximo_backup(cfg):
    if not cfg.firebase_auto:
        return None
    if not cfg.firebase_ultimo_backup:
        return timezone.now()
    return cfg.firebase_ultimo_backup + timedelta(hours=cfg.firebase_intervalo_horas)


def _backup_em_thread(origem: str, usuario_id: int | None) -> None:
    try:
        usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
        enviar_backup(origem, usuario)
    finally:
        close_old_connections()


def sincronizar_ao_logar(user) -> bool:
    cfg = models.Configuracao.obter()
    if not cfg.firebase_sync_login:
        return False
    ultimo = cfg.firebase_ultimo_backup
    if ultimo and timezone.now() - ultimo < timedelta(minutes=INTERVALO_LOGIN_MIN):
        return False
    threading.Thread(target=_backup_em_thread, args=("LOGIN", user.pk), daemon=True).start()
    return True


def _loop_agendador() -> None:
    ultima_falha = 0.0
    while True:
        time.sleep(60)
        try:
            cfg = models.Configuracao.obter()
            prox = proximo_backup(cfg)
            if prox and prox <= timezone.now() and time.time() - ultima_falha > PAUSA_APOS_FALHA_S:
                r = enviar_backup("AUTOMATICO")
                if r is not None and r.status == "ERRO":
                    ultima_falha = time.time()
        except Exception:
            pass
        finally:
            close_old_connections()


def iniciar_agendador() -> None:
    global _agendador_iniciado
    if _agendador_iniciado or os.environ.get("SAMU_SEM_AGENDADOR") == "1":
        return
    _agendador_iniciado = True
    threading.Thread(target=_loop_agendador, name="samu-firebase-agendador", daemon=True).start()
