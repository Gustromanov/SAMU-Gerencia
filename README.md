# SAMU 192 · Sistema de Estoque, Medicamentos e Logística

> Sistema full-stack **monolítico** em português brasileiro para gerenciamento de estoque de medicamentos, lotes, funcionários e frota da unidade local do SAMU.
> Roda **100 % offline** (modo desktop) e também em **rede local** (acesso via navegador por qualquer dispositivo da mesma Wi-Fi).

**Desenvolvido por:** Gustavo Batista · Guanambi/BA · 2026
**Contato:** contato.profissional.gustavo@outlook.com

---

## 📸 O que é

- **Monolito** Django 5 + SQLite + Tailwind.
- **Login com funções**: Administrador, Motorista, Auxiliar, Enfermeiro — cada um vê o que pode usar.
- **Agrupamento inteligente** de medicamentos pelo nome (setinha abre variantes com metragem/forma diferentes).
- **Histórico de manipulações** por funcionário (abre como pergaminho com animação).
- **Dashboards** com gráficos de barras / pizza / rosca, valores nominais **e percentuais**.
- **Exportação** PDF e XLSX (apenas admin), com tabelas completas, data de cadastro, dias restantes e histórico de todos os usuários.
- **Painel do admin**: contas, definições de intervalos, backup/restaurar/apagar BD, modo rede local.
- **Pronto para empacotamento desktop** (Windows / macOS / Linux) e **app Android**.

**Capturas de tela** vivem no diretório `screenshots/` (gere em `/api/medicamentos/`, `/api/relatorio/`, `/api/perfil/`).

---

## 🧭 Papéis e permissões

| Papel | Páginas | Pode criar | Pode editar | Pode excluir |
|-------|---------|------------|-------------|--------------|
| **Administrador** | Tudo | Tudo | Tudo | Tudo |
| **Motorista** | Perfil, Veículos, Relatório (apenas dashboards de veículos) | Veículos | Veículos | — |
| **Auxiliar** | Perfil, Medicamentos, Relatório (dashboards de med.) | Medicamentos / entrada / saída | Medicamentos | — |
| **Enfermeiro** | igual Auxiliar | igual Auxiliar | igual Auxiliar | — |

Todo movimento é gravado com usuário + data/hora → o admin vê **tudo** na seção Funcionários → setinha.

---

## 🚀 Instalação rápida (modo web, dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate       # Linux/macOS
# .\.venv\Scripts\Activate.ps1                           # Windows PowerShell
pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 pywebview
python manage.py migrate
python manage.py seed_samu          # dados demo + usuários
python manage.py runserver 0.0.0.0:8765
```

Abra `http://127.0.0.1:8765/`.

Usuários criados:

| Usuário | Senha | Função |
|---------|-------|--------|
| `admin` | `samu192` | Administrador |
| `motorista.demo` | `motorista123` | Motorista |
| `auxiliar.demo` | `auxiliar123` | Auxiliar |
| `enfermeiro.demo` | `enfermeiro123` | Enfermeiro |

---

## 🖥️ Instalação nativa passo a passo

Veja o guia específico detalhado:
- **Windows / macOS / Linux + Android** → [`backend/README_INSTALL.md`](backend/README_INSTALL.md)
- **Depuração e erros comuns** → [`backend/README_DEBUG.md`](backend/README_DEBUG.md)
- **Sincronizar banco com Firebase** → [`backend/README_FIREBASE.md`](backend/README_FIREBASE.md)
- **Cronograma de desenvolvimento (relatório acadêmico)** → [`backend/README_CRONOGRAMA.md`](backend/README_CRONOGRAMA.md)
- **Superprompt de recriação completa** → [`backend/README_PROMPT.md`](backend/README_PROMPT.md)

---

## 🧪 Testes

```bash
cd backend
pytest tests/ -v
```

---


## 📦 Executáveis, Firebase e Android (v1.1)
| O quê | Onde |
|---|---|
| `.exe` Windows / binário Linux com ícone oficial | `backend/build_windows.bat`, `backend/build_desktop.sh` ou GitHub Actions `build-desktop.yml` |
| Backup Firebase (painel, automático, no login, terminal) | Perfil → Backup Firebase · `README_FIREBASE.md` |
| App Android (IP do servidor + consulta offline Firebase) | `android-app/` · GitHub Actions `android-apk.yml` |
| Regras de segurança Firebase | `firebase/firestore.rules`, `firebase/storage.rules` |


## 🤝 Contribuindo

1. Faça um fork + branch.
2. Rode `python manage.py test` antes do PR.
3. Mantenha a arquitetura monolítica — não quebre em microsserviços.

---

## 📜 Licença

Todos os direitos reservados · Gustavo Batista · 2026.
