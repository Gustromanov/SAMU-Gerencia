# SAMU 192 · PRD · Versão final

## Contexto
Monolito Django 5 + SQLite + Tailwind para gestão de estoque, medicamentos, funcionários e frota do SAMU local de Guanambi/BA. Desenvolvido por Gustavo Batista, 2026.

## Papéis e permissões
- **Administrador**: tudo + painel admin (Contas, Definições, Rede local, Backup/Restore/Apagar DB).
- **Motorista**: Perfil, Veículos (CRUD exceto excluir), Relatório (apenas dashboards de frota).
- **Auxiliar/Enfermeiro**: Perfil, Medicamentos (CRUD exceto excluir), Relatório (apenas dashboards de medicamentos).
- Todas movimentações logadas com usuário + funcionário.
- Apenas admin exporta PDF/XLSX e vê histórico de todos.

## Modelo de dados (10 entidades)
TipoMedicamento, FormaMedicamento, Configuracao (singleton), Medicamento (nome+metragem+tipo+forma únicos), Lote (medicamento+codigo únicos), Funcionario, Veiculo (codigo_id auto), Movimentacao, Perfil (OneToOne User), User (Django).

## Features entregues (versão final)
- **Autenticação**: login + registro com nome completo, nascimento, email, telefone, função, senha (mín 8 letras+números), remember me.
- **Medicamentos**: lista agrupada por nome com setinha expansível (variantes + lotes), filtros combináveis (tipo, forma, nível, validade, lote), autocomplete, KPIs com tooltips, modal entrada/saída com 4 campos (medicamento, lote, quantidade obrigatórios + tipo/forma/origem opcionais), FEFO automático, erro em estoque insuficiente.
- **Funcionários** (admin): setinha abre histórico detalhado estilo pergaminho ("Dr(a). Camila realizou a entrada de Adrenalina em 15 un — Quarta, 22/10/2026 às 19:45"), ordenado do mais recente, com animação scaleY+fade.
- **Veículos**: tipo (Van/Carro/Moto), ID gerado automaticamente, filtros, setinha abre detalhes.
- **Relatório**: 6 dashboards de medicamento + 2 de frota, toggle Barras/Pizza/Rosca, valores nominais+%, 3 listas de alertas (vencendo, baixo estoque, controlados) + 4ª lista com interseção, intervalo configurável para movimentação.
- **Exportação**: PDF (ReportLab) e XLSX (openpyxl, 7 abas) só admin, com histórico de todos usuários + data cadastro + dias restantes. Botão "Anexar local" via showDirectoryPicker.
- **Painel admin**: Contas CRUD, Definições (intervalos estoque/validade), Modo rede local (detecta IPs + copiar), Backup/Restaurar/Apagar BD.
- **Footer**: tema vermelho em todas páginas com dados do dev (Gustavo Batista, Guanambi, contato.profissional.gustavo@outlook.com).
- **Ícone**: SVG SAMU customizado como favicon e no sidebar/login.

## READMEs entregues
1. `/app/README.md` — principal GitHub (visão geral, instalação rápida, links).
2. `/app/backend/README_INSTALL.md` — passo a passo Windows/macOS/Linux + Android + desktop empacotado + rede local + backup.
3. `/app/backend/README_FIREBASE.md` — sync BD com Firebase (Storage e Firestore) via UI do console e terminal, Win/Linux.
4. `/app/backend/README_DEBUG.md` — todos erros possíveis categorizados em 12 seções com causa+solução.
5. `/app/backend/README_CRONOGRAMA.md` — relatório detalhado 15/09–13/11 com obstáculos realistas de estudante jr.
6. `/app/backend/README_PROMPT.md` — superprompt gigante para recriação total do zero.

## Suporte à rede local
- `python manage.py runserver 0.0.0.0:8765` ou `main.py` (desktop local).
- Admin gera link `http://IP:8765/` via botão no painel; outros dispositivos (celulares/tablets/PCs na mesma Wi-Fi) acessam o mesmo banco.
- Documentação de app Android via Capacitor (WebView wrapper) ou Chaquopy (Django embutido).

## Casos de borda cobertos
- Saída > estoque → erro.
- Lote inexistente → orienta cadastro.
- Admin não exclui a si mesmo.
- Duplicação de medicamento (nome+metragem+tipo+forma) → prevenida.
- CPF formato inválido → erro no form.
- Validade não configurada → gráficos exibem placeholder.
- Restaurar BD → fecha conexão antes + força logout.

## Testes
- 22 pytest + testes manuais via curl em todas rotas.
- Todas 4 contas de role testadas: admin (200 em tudo), motorista (403 em med/func), auxiliar (403 em veículos/func), enfermeiro (igual auxiliar).
- Exportação PDF/XLSX validada via HTTPS (headers corretos, bytes válidos).

## Nota sobre `.emergent`
Pasta `.emergent/` é da plataforma Emergent (deploy/preview). **Renomear quebra o deploy.** Em instalação local você pode ignorar/remover; nos READMEs isso é explicado.

## v1.1 (Out/2026) — Build nativo, Firebase, Android
- **Ícones oficiais** gerados do SVG (`backend/gerar_icones.py`): `assets/icons/samu192.ico/.icns/.png` + `android-app/assets/` (icon/splash). Spec usa automaticamente.
- **Build**: `build_windows.bat`, `build_desktop.sh` (Linux usa pywebview[qt]), workflow `.github/workflows/build-desktop.yml` (artifacts Windows .zip / Linux .tar.gz; release em tags v*).
- **main.py**: servidor multi-thread em 0.0.0.0 (SAMU_HOST), `--backup-firebase`, login persistente (private_mode=False), ícone da janela.
- **Backup Firebase** (`core/firebase_sync.py`): Storage `samu192/backups/*.sqlite3.gz` + Firestore `samu192/snapshot`. Modo SIMULADO padrão (`backend/backups_firebase_simulado/`). Painel admin (upload JSON service account → `backend/secrets/`, bucket, testar, enviar agora, auto a cada N h, sync ao login máx. 10 min, histórico `BackupFirebase`). CLI `manage.py firebase_backup [--se-vencido|--simulado|--testar]`. Agendadores: `agendar_backup_windows.bat` (schtasks), `agendar_backup_linux.sh` (cron). Agendador em thread via `core.middleware.AgendadorFirebaseMiddleware`.
- **Android** `android-app/` (Capacitor 6): tela IP/porta do servidor (salva, auto-reconecta, testa `/healthz/` com CORS), consulta offline via Firebase Auth + Firestore (cache local). Workflow `.github/workflows/android-apk.yml` gera APK debug.
- Regras: `firebase/firestore.rules`, `firebase/storage.rules`.
- **Correções**: requirements.txt agora contém Django etc.; URLs `/api/api/...` fixas nos templates → `{% url %}` (desktop/rede local); `FORCE_SCRIPT_NAME` via env `SAMU_SCRIPT_NAME` (server.py define `/api` no preview); histórico de funcionário só admin; `RelatorioJson` filtrado por papel; restaurar BD valida header SQLite.
- Testes: iteration_2 (fase 2 100%), iteration_3 (Firebase simulado 22/22); suíte total 74 passed / 3 skipped.

## Backlog
- P1: Validar workflows do GitHub Actions no primeiro push (não executáveis no preview).
- P1: Testar Firebase real quando o usuário enviar credenciais.
- P2: Restaurar backup direto do Firebase pelo painel (hoje: baixar no console + Restaurar).
- P2: APK assinado (release) para Play Store.
