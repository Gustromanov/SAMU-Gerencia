"""Phase 3 — Firebase backup (simulado), correções de segurança e saúde (healthz)."""
import json
import os
import re
import subprocess
import time
from pathlib import Path

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"
BACKEND = Path("/app/backend")
PASTA_SIM = BACKEND / "backups_firebase_simulado"
PY = "/root/.venv/bin/python"

CREDS = {
    "admin": ("admin", "samu192"),
    "motorista": ("motorista.demo", "motorista123"),
    "auxiliar": ("auxiliar.demo", "auxiliar123"),
    "enfermeiro": ("enfermeiro.demo", "enfermeiro123"),
}


def _csrf(client, url):
    r = client.get(url)
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    assert m, f"CSRF não encontrado em {url}"
    return m.group(1)


def _login(user_key):
    s = requests.Session()
    token = _csrf(s, f"{API}/login/")
    user, pw = CREDS[user_key]
    r = s.post(
        f"{API}/login/",
        data={"csrfmiddlewaretoken": token, "username": user, "password": pw},
        headers={"Referer": f"{API}/login/"},
        allow_redirects=False,
    )
    assert r.status_code in (302, 303), f"login {user} falhou: {r.status_code}"
    return s


@pytest.fixture(scope="module")
def admin_client():
    return _login("admin")


@pytest.fixture(scope="module")
def motorista_client():
    return _login("motorista")


@pytest.fixture(scope="module")
def auxiliar_client():
    return _login("auxiliar")


# -------------------- Health --------------------
class TestHealth:
    def test_healthz_ok(self):
        r = requests.get(f"{API}/healthz/")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert data.get("app") == "samu192"
        assert r.headers.get("Access-Control-Allow-Origin") == "*"


# -------------------- Perfil card --------------------
class TestPainelFirebase:
    def test_card_render_admin(self, admin_client):
        r = admin_client.get(f"{API}/perfil/")
        assert r.status_code == 200
        html = r.text
        # Card and all required data-testids
        for tid in [
            "painel-firebase", "fb-modo-badge", "fb-status-credenciais",
            "fb-status-ultimo", "fb-status-proximo", "fb-form",
            "fb-credenciais", "fb-bucket", "fb-simulado", "fb-sync-login",
            "fb-auto", "fb-intervalo", "fb-salvar",
            "fb-enviar-agora", "fb-testar", "fb-historico",
        ]:
            assert f'data-testid="{tid}"' in html, f"missing testid={tid}"
        # Badge default = modo simulado
        assert "Modo simulado" in html

    def test_card_not_rendered_for_motorista(self, motorista_client):
        r = motorista_client.get(f"{API}/perfil/")
        assert r.status_code == 200
        assert 'data-testid="painel-firebase"' not in r.text


# -------------------- Firebase actions --------------------
class TestFirebaseAcoes:
    def _post(self, client, data=None, files=None):
        token = _csrf(client, f"{API}/perfil/")
        payload = {"csrfmiddlewaretoken": token}
        if data:
            payload.update(data)
        return client.post(
            f"{API}/perfil/firebase/", data=payload, files=files,
            headers={"Referer": f"{API}/perfil/"}, allow_redirects=False,
        )

    def test_enviar_agora_simulado(self, admin_client):
        n_antes = len(list(PASTA_SIM.glob("samu192-*.sqlite3.gz"))) if PASTA_SIM.exists() else 0
        r = self._post(admin_client, {"acao": "enviar"})
        assert r.status_code in (302, 303)
        time.sleep(1.5)
        pagina = admin_client.get(f"{API}/perfil/").text
        assert "Backup enviado" in pagina or "Simulado" in pagina
        # histórico tem linha com destino .sqlite3.gz
        assert ".sqlite3.gz" in pagina
        files_after = sorted(PASTA_SIM.glob("samu192-*.sqlite3.gz"))
        assert len(files_after) >= n_antes
        # snapshot.json valido
        snap = json.loads((PASTA_SIM / "snapshot.json").read_text(encoding="utf-8"))
        for k in ("gerado_em", "kpis", "medicamentos", "veiculos"):
            assert k in snap, f"snapshot ausente chave {k}"

    def test_testar_simulado(self, admin_client):
        r = self._post(admin_client, {"acao": "testar"})
        assert r.status_code in (302, 303)
        pagina = admin_client.get(f"{API}/perfil/").text
        assert "Modo simulado OK" in pagina

    def test_salvar_configuracoes_ok(self, admin_client):
        r = self._post(admin_client, {
            "acao": "salvar",
            "firebase_simulado": "on",
            "firebase_sync_login": "on",
            "firebase_auto": "on",
            "firebase_intervalo_horas": "6",
            "firebase_bucket": "gs://meu-proj.appspot.com/",
        })
        assert r.status_code in (302, 303)
        pagina = admin_client.get(f"{API}/perfil/").text
        # bucket foi normalizado — buscar no HTML pelo value do input
        m = re.search(r'name="firebase_bucket"[^>]*value="([^"]*)"', pagina)
        assert m, "input firebase_bucket não encontrado"
        assert m.group(1) == "meu-proj.appspot.com", f"bucket não normalizado: {m.group(1)!r}"
        # próximo backup renderizado
        assert "fb-status-proximo" in pagina

    @pytest.mark.parametrize("intervalo", ["0", "999"])
    def test_salvar_intervalo_invalido(self, admin_client, intervalo):
        r = self._post(admin_client, {
            "acao": "salvar",
            "firebase_simulado": "on",
            "firebase_intervalo_horas": intervalo,
            "firebase_bucket": "meu-proj.appspot.com",
        })
        assert r.status_code in (302, 303)
        pagina = admin_client.get(f"{API}/perfil/").text
        # Precisa haver alguma mensagem de erro associada ao intervalo
        assert ("intervalo" in pagina.lower()) or ("inválid" in pagina.lower()) or ("erro" in pagina.lower())

    def test_upload_credencial_invalida(self, admin_client):
        # Monta multipart com JSON inválido
        token = _csrf(admin_client, f"{API}/perfil/")
        files = {"firebase_credenciais": ("fake.json", b'{"a":1}', "application/json")}
        data = {
            "csrfmiddlewaretoken": token,
            "acao": "salvar",
            "firebase_simulado": "on",
            "firebase_intervalo_horas": "6",
            "firebase_bucket": "meu-proj.appspot.com",
        }
        r = admin_client.post(
            f"{API}/perfil/firebase/", data=data, files=files,
            headers={"Referer": f"{API}/perfil/"}, allow_redirects=False,
        )
        assert r.status_code in (302, 303)
        pagina = admin_client.get(f"{API}/perfil/").text
        assert "conta de serviço" in pagina.lower() or "service" in pagina.lower() or "inválid" in pagina.lower()

    def test_enviar_agora_sem_credenciais_e_sem_simulado(self, admin_client):
        # Desmarca simulado (sem credenciais no sistema)
        r = self._post(admin_client, {
            "acao": "salvar",
            "firebase_intervalo_horas": "6",
            "firebase_bucket": "meu-proj.appspot.com",
        })  # omitir firebase_simulado = desmarcado
        assert r.status_code in (302, 303)
        r = self._post(admin_client, {"acao": "enviar"})
        assert r.status_code in (302, 303)
        pagina = admin_client.get(f"{API}/perfil/").text
        assert ("Credenciais do Firebase não enviadas" in pagina) or ("não enviadas" in pagina.lower())
        # linha ERRO no histórico
        assert "Erro" in pagina or "ERRO" in pagina
        # Restaurar: voltar simulado = on
        r = self._post(admin_client, {
            "acao": "salvar",
            "firebase_simulado": "on",
            "firebase_sync_login": "on",
            "firebase_intervalo_horas": "24",
            "firebase_bucket": "meu-proj.appspot.com",
        })
        assert r.status_code in (302, 303)

    def test_firebase_post_forbidden_motorista(self, motorista_client):
        token = _csrf(motorista_client, f"{API}/perfil/")
        r = motorista_client.post(
            f"{API}/perfil/firebase/",
            data={"csrfmiddlewaretoken": token, "acao": "testar"},
            headers={"Referer": f"{API}/perfil/"}, allow_redirects=False,
        )
        assert r.status_code == 403

    def test_firebase_post_forbidden_auxiliar(self, auxiliar_client):
        token = _csrf(auxiliar_client, f"{API}/perfil/")
        r = auxiliar_client.post(
            f"{API}/perfil/firebase/",
            data={"csrfmiddlewaretoken": token, "acao": "testar"},
            headers={"Referer": f"{API}/perfil/"}, allow_redirects=False,
        )
        assert r.status_code == 403


# -------------------- Sync ao logar --------------------
class TestSyncLogin:
    def test_sync_ao_logar(self, admin_client):
        # garantir simulado+sync_login ligados + bucket ok
        token = _csrf(admin_client, f"{API}/perfil/")
        admin_client.post(
            f"{API}/perfil/firebase/", data={
                "csrfmiddlewaretoken": token, "acao": "salvar",
                "firebase_simulado": "on", "firebase_sync_login": "on",
                "firebase_intervalo_horas": "24",
                "firebase_bucket": "meu-proj.appspot.com",
            }, headers={"Referer": f"{API}/perfil/"}, allow_redirects=False,
        )
        # força último backup antigo
        subprocess.run([
            PY, "manage.py", "shell", "-c",
            "from core.models import Configuracao as C; from django.utils import timezone;"
            "from datetime import timedelta; c=C.obter();"
            "c.firebase_ultimo_backup=timezone.now()-timedelta(hours=2); c.save()",
        ], cwd=str(BACKEND), check=True, capture_output=True)
        # novo login (nova sessão) qualquer usuário dispara sync
        _login("motorista")
        time.sleep(3)
        # Confere no histórico via admin
        pagina = admin_client.get(f"{API}/perfil/").text
        assert "Ao fazer login" in pagina or "LOGIN" in pagina.upper()


# -------------------- CLI --------------------
class TestFirebaseCLI:
    def _run(self, *args):
        return subprocess.run(
            [PY, "manage.py", "firebase_backup", *args],
            cwd=str(BACKEND), capture_output=True, text=True, timeout=60,
        )

    def test_cli_simulado(self):
        r = self._run("--simulado")
        assert r.returncode == 0, r.stderr
        assert "Backup OK" in r.stdout and ("Simulado" in r.stdout or "simulado" in r.stdout.lower())

    def test_cli_se_vencido_em_dia(self):
        # Após test_cli_simulado o último backup é recente
        r = self._run("--se-vencido")
        assert r.returncode == 0, r.stderr
        assert "Backup em dia" in r.stdout

    def test_cli_testar(self):
        r = self._run("--testar")
        assert r.returncode == 0, r.stderr
        assert "simulado OK" in r.stdout or "Simulado" in r.stdout


# -------------------- Correções de segurança --------------------
class TestSecurityFixes:
    def test_historico_funcionario_admin_only(self, admin_client, motorista_client, auxiliar_client):
        # Admin: 200 em algum pk existente
        r = admin_client.get(f"{API}/api/funcionarios/1/historico/")
        assert r.status_code == 200
        r = motorista_client.get(f"{API}/api/funcionarios/1/historico/")
        assert r.status_code == 403, r.status_code
        r = auxiliar_client.get(f"{API}/api/funcionarios/1/historico/")
        assert r.status_code == 403, r.status_code

    def test_relatorio_filtrado_por_papel(self, admin_client, motorista_client, auxiliar_client):
        # Admin pode ambos
        assert admin_client.get(f"{API}/api/relatorio/?pesquisa=tipo").status_code == 200
        assert admin_client.get(f"{API}/api/relatorio/?pesquisa=veic_status").status_code == 200
        # Motorista: tipo → 403; veic_status → 200
        assert motorista_client.get(f"{API}/api/relatorio/?pesquisa=tipo").status_code == 403
        assert motorista_client.get(f"{API}/api/relatorio/?pesquisa=veic_status").status_code == 200
        # Auxiliar: veic_status → 403; tipo → 200
        assert auxiliar_client.get(f"{API}/api/relatorio/?pesquisa=veic_status").status_code == 403
        assert auxiliar_client.get(f"{API}/api/relatorio/?pesquisa=tipo").status_code == 200

    def test_restaurar_db_arquivo_invalido(self, admin_client):
        token = _csrf(admin_client, f"{API}/perfil/")
        # arquivo texto renomeado
        files = {"backup": ("fake.sqlite3", b"this is not a sqlite database", "application/octet-stream")}
        r = admin_client.post(
            f"{API}/perfil/db/restaurar/",
            data={"csrfmiddlewaretoken": token},
            files=files,
            headers={"Referer": f"{API}/perfil/"},
            allow_redirects=False,
        )
        assert r.status_code in (302, 303, 400)
        pagina = admin_client.get(f"{API}/perfil/").text
        assert "inválid" in pagina.lower() or "SQLite" in pagina
        # banco ainda responde
        r2 = admin_client.get(f"{API}/perfil/")
        assert r2.status_code == 200


# -------------------- Regressão URLs --------------------
class TestRegressaoUrls:
    def test_funcionarios_page(self, admin_client):
        r = admin_client.get(f"{API}/funcionarios/")
        assert r.status_code == 200
        # histórico endpoint referenciado
        assert "/historico/" in r.text

    def test_relatorio_canvases_admin(self, admin_client):
        r = admin_client.get(f"{API}/relatorio/")
        assert r.status_code == 200
        canvases = r.text.count("<canvas")
        assert canvases >= 6, f"esperava >=6 canvases, achei {canvases}"

    def test_medicamento_excluir_action(self, admin_client):
        r = admin_client.get(f"{API}/medicamentos/")
        assert r.status_code == 200
        # action aponta para /medicamentos/<id>/excluir/
        assert re.search(r"/medicamentos/\d+/excluir/|/medicamentos/0/excluir/", r.text)
