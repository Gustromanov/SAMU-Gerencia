# SAMU 192 · Sistema de Estoque, Medicamentos e Logística

## Problem statement (original)
Sistema fullstack em PT-BR para o SAMU local, cadastros e gerenciamento de:
- **Medicamentos** com lote, validade, nome, tipo, forma, complemento, situação, quantidade, nível de estoque (normal/baixo/muito baixo)
- **Funcionários** com CPF, nome, função, contato (email/telefone), histórico
- **Veículos** com id, modelo, ano, status (manutenção/normal/inativo)
- Lista principal com barra de pesquisa + autocomplete, KPIs, filtros
- Botões "Registrar entrada" e "Registrar saída" (modal com 4 campos)
- Relatório com gráfico de barras (por tipo/forma/validade), rosca por status de veículo, listas de estoque baixo/muito baixo/vencendo
- Perfil do usuário editável
- Paleta oficial SAMU (branco/cinza/laranja/vermelho/preto/verde/amarelo)
- Sem bugs: rejeita saída maior que estoque; valida entradas em todos os cadastros

## Escolhas do usuário
- **Stack:** Django 5 + SQLite + Tailwind (CDN) + Chart.js — empacotável desktop via pywebview (main.py)
- **Auth:** login simples email/senha (Django auth)
- **Veículos:** apenas id, modelo, ano, status (sem placa/base/KM)
- **Seed:** dados de exemplo populados (~30 medicamentos, 10 funcionários, 8 veículos)
- **Perfil:** editável

## Arquitetura
- Django ASGI servido pelo supervisor via uvicorn (`server:app` → `samu.asgi`).
- Todas as rotas sob prefixo `/api/` (FORCE_SCRIPT_NAME) para compatibilidade com o ingress.
- Frontend React apenas redireciona `/` para `/api/`.
- Banco SQLite em `/app/backend/db.sqlite3`.
- **main.py** (pywebview) empacota app desktop offline (usa WSGI local em 127.0.0.1:8765).

## Modelo de domínio (Django ORM)
- `TipoMedicamento`, `FormaMedicamento` (lookups)
- `Medicamento` (nome + tipo + forma únicos) → `Lote` (código, validade, quantidade, situação)
- `Funcionario` (CPF único, função, email, telefone)
- `Veiculo` (código_id, modelo, ano, status)
- `Movimentacao` (ENTRADA/SAIDA, lote, funcionário, quantidade, origem/destino, horário) — histórico completo
- `Perfil` (extensão User com telefone/cargo/bio)

## O que foi implementado (05/08/2026)
- Login/logout/registro com CSRF (trusted origins configurados para preview + emergentcf.cloud)
- Lista de medicamentos com KPIs, autocomplete JSON, filtros (tipo/forma/nível), tabela com badges de estoque, ações edit/delete
- Modal "Registrar entrada/saída" com 4 campos, FEFO na saída, rejeição por estoque insuficiente, mensagem de desambiguação se múltiplos matches
- CRUD completo de Medicamento + Lote (regra de exclusão: se 1 lote apaga tudo; se >1 lote pede quantos)
- CRUD de Funcionário (validação CPF formato + duplicidade), com histórico de movimentações
- CRUD de Veículo (validação de ano 1980-2100)
- Relatório com KPIs + gráfico de barras Chart.js (filtros tipo/forma/validade) + rosca de frota + listas de alertas
- Perfil editável (nome, email, telefone, cargo, bio)
- Seed com 32 medicamentos, 44 lotes, 10 funcionários, 8 veículos, 35 movimentações
- Testes automatizados 22/22 (pytest) e testes frontend Playwright — 100% passaram

## Update 05/08/2026 · Exportação e empacotamento desktop
- **Exportar PDF** do relatório (ReportLab) — dashboard operacional em uma página
- **Exportar XLSX** (openpyxl) — 5 abas: Resumo, Lotes, Distribuições, Funcionários, Veículos
- Botões na tela Relatório: `Baixar planilha (.xlsx)` e `Baixar PDF`
- **PyInstaller spec** (`backend/samu192.spec`) + script `backend/build_desktop.sh` empacotam o app como executável nativo (.exe / .app / binário Linux)
- `main.py` atualizado: suporta modo frozen (PyInstaller), banco persistente ao lado do executável, porta livre automática
- README completo em `/app/backend/README.md`

## Backlog / Próximas melhorias possíveis
- Substituir Tailwind CDN por build production (PostCSS)
- Validação de dígitos verificadores do CPF
- Exportação PDF/CSV de relatórios
- Alertas por e-mail para validades vencendo (SendGrid)
- Log de auditoria detalhado por usuário
- App mobile / PWA
