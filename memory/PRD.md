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

## Backlog
- Build do executável com ícone oficial (gerar `.ico` do SVG).
- APK Android compilado (requer máquina com Android Studio).
- Pipeline Firebase automatizada por watcher em produção.
