# SAMU 192 · Sistema de Estoque, Medicamentos e Logística

Sistema **fullstack em português brasileiro** para gerenciamento de estoque, medicamentos, funcionários e frota da unidade local do SAMU. Roda como aplicação web e também como **aplicativo desktop nativo** (Windows / macOS / Linux) via PyInstaller + pywebview.

---

## 🚀 Stack

- **Backend:** Python 3.11 + Django 5 + SQLite (ORM com integridade referencial)
- **Frontend:** Django Templates + Tailwind (CDN) + Chart.js + Lucide Icons
- **Exportação de relatórios:** openpyxl (XLSX) + ReportLab (PDF)
- **Desktop:** pywebview + PyInstaller (gera `.exe` / `.app` / binário Linux)

## 🧭 Estrutura

```
backend/
├── manage.py                  # utilitário Django
├── main.py                    # entrada do app desktop (pywebview)
├── build_desktop.sh           # empacotamento PyInstaller
├── samu192.spec               # spec do PyInstaller
├── server.py                  # ASGI para uvicorn (preview web)
├── db.sqlite3                 # banco local (criado no 1º run)
├── samu/                      # settings/urls/asgi/wsgi
└── core/
    ├── models.py              # Medicamento, Lote, Funcionario, Veiculo, Movimentacao, Perfil
    ├── forms.py               # ModelForms + validações
    ├── views.py               # CRUD + movimentações + relatórios
    ├── exportacao.py          # gera PDF e XLSX do relatório
    ├── urls.py
    ├── admin.py
    ├── context_processors.py  # sidebar dinâmica
    ├── management/commands/seed_samu.py
    └── migrations/
templates/core/                # HTML (base, login, medicamentos, funcionarios, veiculos, relatorio, perfil)
static/                        # CSS/JS locais (opcional; usa CDN)
```

## 🖥️ Rodar em modo web (preview / servidor)

Já está configurado no supervisor — ASGI via uvicorn em `server:app`. URL:
`https://<seu-dominio>/api/`

Login padrão: **admin / samu192**

## 🖱️ Rodar em modo desktop (local)

```bash
cd backend
pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 pywebview
python main.py
```

Uma janela nativa abre com o sistema apontando para `http://127.0.0.1:8765/`. O banco SQLite fica em `db.sqlite3` no mesmo diretório.

## 📦 Empacotar como executável (.exe / .app / binário)

```bash
cd backend
bash build_desktop.sh
```

Ao final:
- **Windows:** `dist/SAMU192/SAMU192.exe`
- **macOS:** `dist/SAMU 192.app` (arraste para a pasta Aplicativos)
- **Linux:** `dist/SAMU192/SAMU192`

O executável já embarca templates, static, migrations e todas as libs. Distribua a pasta inteira `dist/SAMU192/` — ela é auto-suficiente.

> ⚠️ **Importante:** PyInstaller gera o executável para o SO em que ele foi rodado. Para gerar `.exe`, execute em Windows; para `.app`, em macOS; para Linux, em Linux.

## 📊 Relatórios

Na tela **Relatório**:
- Botão **Baixar PDF** — dashboard operacional em uma página, com KPIs, alertas e distribuição por tipo (ReportLab)
- Botão **Baixar planilha (.xlsx)** — 5 abas: Resumo, Lotes, Distribuições, Funcionários, Veículos (openpyxl)

## 🌱 Reseed do banco

```bash
python manage.py seed_samu
```

## 🔐 Auth

Login com usuário + senha (Django auth). Sessão persistente por 30 dias. CSRF configurado para os domínios de preview e produção.

## 🧪 Testes automatizados

Cobertura de 22 testes pytest em `tests/test_samu_api.py`. Rode com:
```bash
pytest backend/tests/ -v
```
