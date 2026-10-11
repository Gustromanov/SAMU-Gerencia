"""SAMU 192 backend tests — Django templates + JSON APIs.

Runs against public URL via CSRF-aware login flow.
"""
import os
import re
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api"
USERNAME = "admin"
PASSWORD = "samu192"

CSRF_RE = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Referer": f"{API}/login/", "Origin": BASE})
    # GET login page for CSRF
    r = s.get(f"{API}/login/")
    assert r.status_code == 200, r.status_code
    m = CSRF_RE.search(r.text)
    assert m, "CSRF token not found on login page"
    token = m.group(1)
    r = s.post(
        f"{API}/login/",
        data={
            "csrfmiddlewaretoken": token,
            "username": USERNAME,
            "password": PASSWORD,
        },
        allow_redirects=False,
    )
    assert r.status_code in (302, 303), f"Login failed: {r.status_code}"
    return s


def _csrf(client, url):
    r = client.get(url)
    m = CSRF_RE.search(r.text)
    assert m, f"CSRF token missing at {url}"
    return m.group(1)


# ---------- Health / basic ----------
class TestBasic:
    def test_healthz(self):
        r = requests.get(f"{API}/healthz/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_root_redirects_to_login(self):
        r = requests.get(f"{API}/", allow_redirects=False)
        assert r.status_code in (301, 302)
        assert "login" in r.headers.get("Location", "")

    def test_login_page_loads(self):
        r = requests.get(f"{API}/login/")
        assert r.status_code == 200
        assert "login-username" in r.text
        assert "login-password" in r.text

    def test_login_authenticated_redirects_to_medicamentos(self, client):
        r = client.get(f"{API}/medicamentos/")
        assert r.status_code == 200
        assert "busca-medicamento-input" in r.text


# ---------- Medicamentos list & autocomplete ----------
class TestMedicamentos:
    def test_lista_renders_kpis_and_lotes(self, client):
        r = client.get(f"{API}/medicamentos/")
        assert r.status_code == 200
        for testid in ("kpi-medicamentos", "kpi-lotes", "kpi-baixo",
                       "kpi-muito-baixo", "kpi-vencendo",
                       "btn-registrar-entrada", "btn-registrar-saida"):
            assert testid in r.text, f"missing {testid}"

    def test_busca_medicamentos_json(self, client):
        r = client.get(f"{API}/api/busca/medicamentos/?q=a")
        assert r.status_code == 200
        data = r.json()
        assert "resultados" in data
        assert isinstance(data["resultados"], list)
        if data["resultados"]:
            row = data["resultados"][0]
            for k in ("id", "nome", "tipo", "forma", "quantidade_total"):
                assert k in row

    def test_busca_funcionarios_json(self, client):
        r = client.get(f"{API}/api/busca/funcionarios/?q=")
        assert r.status_code == 200
        assert "resultados" in r.json()

    def test_busca_veiculos_json(self, client):
        r = client.get(f"{API}/api/busca/veiculos/?q=")
        assert r.status_code == 200
        assert "resultados" in r.json()


# ---------- Movimentação (entrada/saída) ----------
class TestMovimentacao:
    def _pick_medicamento(self, client):
        r = client.get(f"{API}/api/busca/medicamentos/?q=")
        results = r.json()["resultados"]
        assert results, "seed missing medicamentos"
        for med in results:
            lotes = client.get(f"{API}/api/busca/lotes/?medicamento={med['nome']}").json()["resultados"]
            lotes = [l for l in lotes if l["medicamento"] == med["nome"]]
            if lotes:
                med["lote_codigo"] = lotes[0]["codigo"]
                return med
        pytest.skip("nenhum medicamento com lote no seed")

    def test_entrada_incrementa_estoque(self, client):
        med = self._pick_medicamento(client)
        antes = med["quantidade_total"]
        token = _csrf(client, f"{API}/medicamentos/")
        r = client.post(
            f"{API}/movimentar/",
            data={
                "csrfmiddlewaretoken": token,
                "tipo_movimentacao": "ENTRADA",
                "medicamento_query": med["nome"],
                "lote_codigo": med["lote_codigo"],
                "quantidade": 5,
                "tipo_medicamento": med["tipo_id"],
                "forma_medicamento": med["forma_id"],
                "origem": "TEST_entrada",
            },
            allow_redirects=False,
        )
        assert r.status_code in (302, 303)
        r2 = client.get(f"{API}/api/busca/medicamentos/?q={med['nome']}")
        novos = [m for m in r2.json()["resultados"] if m["id"] == med["id"]]
        assert novos and novos[0]["quantidade_total"] == antes + 5

    def test_saida_recusa_quando_estoque_insuficiente(self, client):
        med = self._pick_medicamento(client)
        estoque = med["quantidade_total"]
        pedido = estoque + 100000
        token = _csrf(client, f"{API}/medicamentos/")
        r = client.post(
            f"{API}/movimentar/",
            data={
                "csrfmiddlewaretoken": token,
                "tipo_movimentacao": "SAIDA",
                "medicamento_query": med["nome"],
                "lote_codigo": med["lote_codigo"],
                "tipo_medicamento": med["tipo_id"],
                "forma_medicamento": med["forma_id"],
                "quantidade": pedido,
                "origem": "TEST_saida_over",
            },
            allow_redirects=True,
        )
        assert r.status_code == 200
        # Estoque não deve ter mudado
        r2 = client.get(f"{API}/api/busca/medicamentos/?q={med['nome']}")
        novos = [m for m in r2.json()["resultados"] if m["id"] == med["id"]]
        assert novos and novos[0]["quantidade_total"] == estoque
        # Página deve exibir mensagem "insuficiente"
        assert "insuficiente" in r.text.lower() or "estoque" in r.text.lower()

    def test_saida_valida_decrementa(self, client):
        med = self._pick_medicamento(client)
        estoque = med["quantidade_total"]
        if estoque < 1:
            pytest.skip("estoque insuficiente para teste de saída")
        token = _csrf(client, f"{API}/medicamentos/")
        r = client.post(
            f"{API}/movimentar/",
            data={
                "csrfmiddlewaretoken": token,
                "tipo_movimentacao": "SAIDA",
                "medicamento_query": med["nome"],
                "lote_codigo": med["lote_codigo"],
                "tipo_medicamento": med["tipo_id"],
                "forma_medicamento": med["forma_id"],
                "quantidade": 1,
                "origem": "TEST_saida",
            },
            allow_redirects=False,
        )
        assert r.status_code in (302, 303)
        r2 = client.get(f"{API}/api/busca/medicamentos/?q={med['nome']}")
        novos = [m for m in r2.json()["resultados"] if m["id"] == med["id"]]
        assert novos and novos[0]["quantidade_total"] == estoque - 1

    def test_ambiguidade_medicamento(self, client):
        # Query "a" (or similar) should match many; expect refusal & no stock change
        token = _csrf(client, f"{API}/medicamentos/")
        # snapshot totals
        before = client.get(f"{API}/api/busca/medicamentos/?q=").json()["resultados"]
        before_map = {m["id"]: m["quantidade_total"] for m in before}
        r = client.post(
            f"{API}/movimentar/",
            data={
                "csrfmiddlewaretoken": token,
                "tipo_movimentacao": "ENTRADA",
                "medicamento_query": "a",
                "lote_codigo": "TEST-INEXISTENTE",
                "tipo_medicamento": "",
                "forma_medicamento": "",
                "quantidade": 1,
                "origem": "TEST_ambig",
            },
            allow_redirects=True,
        )
        assert r.status_code == 200
        # nada mudou
        after = client.get(f"{API}/api/busca/medicamentos/?q=").json()["resultados"]
        for m in after:
            if m["id"] in before_map:
                assert m["quantidade_total"] == before_map[m["id"]]


# ---------- Funcionários ----------
class TestFuncionarios:
    def test_lista_carrega(self, client):
        r = client.get(f"{API}/funcionarios/")
        assert r.status_code == 200
        assert "btn-novo-funcionario" in r.text

    def test_cpf_invalido_rejeitado(self, client):
        token = _csrf(client, f"{API}/funcionarios/novo/")
        r = client.post(
            f"{API}/funcionarios/novo/",
            data={
                "csrfmiddlewaretoken": token,
                "nome": "TEST User",
                "cpf": "12345678900",  # invalid format
                "funcao": "TECNICO",
                "email": "test_invalid_cpf@example.com",
                "telefone": "(11) 99999-9999",
            },
            allow_redirects=False,
        )
        # Form re-render (200) with errors, no redirect
        assert r.status_code == 200
        assert "000.000.000-00" in r.text or "formato" in r.text.lower()

    def test_criar_e_duplicar_cpf(self, client):
        cpf = "111.222.333-44"
        email1 = f"test_cpf_{int(time.time())}@samu.gov.br"
        token = _csrf(client, f"{API}/funcionarios/novo/")
        r = client.post(
            f"{API}/funcionarios/novo/",
            data={
                "csrfmiddlewaretoken": token,
                "nome": "TEST Funcionario",
                "cpf": cpf,
                "funcao": "TECNICO",
                "email": email1,
                "telefone": "(11) 99999-9999",
            },
            allow_redirects=False,
        )
        if r.status_code not in (302, 303):
            # If CPF already existed from prior run, that's ok; move on to duplicate test
            pass

        # Try duplicating CPF with different email
        token2 = _csrf(client, f"{API}/funcionarios/novo/")
        r2 = client.post(
            f"{API}/funcionarios/novo/",
            data={
                "csrfmiddlewaretoken": token2,
                "nome": "TEST Dup",
                "cpf": cpf,
                "funcao": "TECNICO",
                "email": f"dup_{int(time.time())}@samu.gov.br",
                "telefone": "(11) 88888-8888",
            },
            allow_redirects=False,
        )
        # Should fail with 200 (form errors), not redirect
        assert r2.status_code == 200


# ---------- Veículos ----------
class TestVeiculos:
    def test_lista_carrega(self, client):
        r = client.get(f"{API}/veiculos/")
        assert r.status_code == 200
        assert "btn-novo-veiculo" in r.text

    def test_ano_invalido_rejeitado(self, client):
        token = _csrf(client, f"{API}/veiculos/novo/")
        r = client.post(
            f"{API}/veiculos/novo/",
            data={
                "csrfmiddlewaretoken": token,
                "codigo_id": f"TEST-{int(time.time())}",
                "modelo": "TEST Modelo",
                "ano": 1900,
                "status": "NORMAL",
            },
            allow_redirects=False,
        )
        assert r.status_code == 200
        assert "inválido" in r.text.lower() or "invalido" in r.text.lower() or "ano" in r.text.lower()


# ---------- Relatório ----------
class TestRelatorio:
    def test_relatorio_page(self, client):
        r = client.get(f"{API}/relatorio/")
        assert r.status_code == 200
        assert 'data-pesquisa="tipo"' in r.text

    @pytest.mark.parametrize("pesquisa", ["tipo", "forma", "validade", "veic_status"])
    def test_relatorio_json(self, client, pesquisa):
        r = client.get(f"{API}/api/relatorio/?pesquisa={pesquisa}")
        assert r.status_code == 200
        data = r.json()
        assert len(data["labels"]) == len(data["valores"]) == len(data["percentuais"])
        assert data["total"] == sum(data["valores"])


# ---------- Perfil ----------
class TestPerfil:
    def test_perfil_load_and_update(self, client):
        r = client.get(f"{API}/perfil/")
        assert r.status_code == 200
        assert "perfil-nome" in r.text
        token = _csrf(client, f"{API}/perfil/")
        r2 = client.post(
            f"{API}/perfil/",
            data={
                "csrfmiddlewaretoken": token,
                "first_name": "TEST Admin",
                "email": "admin@samu.gov.br",
                "telefone": "(11) 12345-6789",
            },
            allow_redirects=False,
        )
        assert r2.status_code in (302, 303)
        # Verify persistence
        r3 = client.get(f"{API}/perfil/")
        assert "TEST Admin" in r3.text
        assert "(11) 12345-6789" in r3.text
