# 📜 Superprompt de Recriação — SAMU 192

> Este arquivo contém **tudo** que foi pedido para construir o sistema, organizado como se fosse um único prompt gigante para recriação do zero.
> Nada é resumido. Útil para reproduzir o sistema em outra ferramenta ou passar para outro desenvolvedor.

---

## 🎯 Objetivo geral

Construir um sistema **fullstack monolítico em português brasileiro** que sirva ao SAMU local de Guanambi/BA para gerenciar estoque de medicamentos, lotes, funcionários e frota de veículos. O sistema deve rodar como **aplicativo desktop nativo** (Windows, macOS, Linux) e também permitir empacotamento como **app Android**, com suporte a **rede local** para múltiplos dispositivos acessarem o **mesmo banco de dados** em tempo real. A arquitetura é um **monolito** com Django + SQLite + Tailwind, sem microsserviços.

---

## 🖥️ Stack obrigatória
- **Backend:** Python 3.10+ com Django 5.1.4 (ORM, templates, auth).
- **Banco:** SQLite (arquivo único `db.sqlite3`).
- **Frontend:** Django Templates + Tailwind CSS (via CDN) + Chart.js (via CDN) + Lucide Icons.
- **Desktop:** pywebview para janela nativa, PyInstaller para empacotar.
- **Static files:** Whitenoise.
- **Exportação:** openpyxl (XLSX), ReportLab (PDF).
- **Sync remoto opcional:** Firebase Admin SDK (Storage ou Firestore).

---

## 👥 Papéis e permissões

| Papel | Páginas visíveis | Pode criar | Pode editar | Pode excluir |
|-------|------------------|-----------|-------------|--------------|
| **Administrador** | TODAS | TUDO | TUDO | TUDO |
| **Motorista** | Perfil, Veículos, Relatório (dashboards de frota apenas) | Veículos | Veículos | Nada |
| **Auxiliar** | Perfil, Medicamentos, Relatório (dashboards de med) | Medicamentos / lotes / entradas / saídas | Medicamentos | Nada |
| **Enfermeiro** | igual Auxiliar | igual Auxiliar | igual Auxiliar | Nada |

- Todas as ações são registradas em `Movimentacao` com o `User` logado.
- Apenas o admin vê o histórico completo de **todos** os usuários na seção Funcionários.
- Apenas o admin exporta PDF/XLSX.
- Admin não pode excluir a si mesmo.

---

## 📊 Modelo de dados (Django ORM)

### `TipoMedicamento`
- `nome` (único), `slug` (único)
- Valores padrão: Analgésico, Antibiótico, Anti-inflamatório, Antiviral, Antifúngico, Antidepressivo, Antihipertensivo, Vacina, Outro.

### `FormaMedicamento`
- `nome` (único), `slug` (único)
- Valores padrão: Comprimido, Cápsula, Drágea, Pílula, Gotas, Xarope, Ampola, Frasco-ampola, Pomada, Pastilha, Outro.

### `Configuracao` (singleton, 1 registro só)
- `estoque_muito_baixo`, `estoque_baixo`, `estoque_alto` (inteiros)
- `validade_muito_proximo`, `validade_proximo`, `validade_controlado` (dias)
- `diretorio_downloads` (string), `intervalo_dias_padrao` (int, default 30)
- `validade_configurada` (bool — se false, filtros de validade ficam vazios)

### `Medicamento`
- `nome` (ex.: "Adrenalina")
- `metragem` (ex.: "1mg/mL", "500mg")
- `tipo` FK → TipoMedicamento
- `forma` FK → FormaMedicamento
- `complemento` (opcional, aparece abaixo do nome na lista)
- `criado_em`, `atualizado_em`
- **Único**: (nome, metragem, tipo, forma)

### `Lote`
- `medicamento` FK
- `codigo` (string, ex.: "L2025-A1")
- `validade` (DateField)
- `quantidade` (int ≥ 0)
- `situacao` ∈ {RECEBIDO, LOTEADO, DOADO}
- `@property nivel_estoque` → MUITO_BAIXO / BAIXO / NORMAL / ALTO (compara com `Configuracao`)
- `@property nivel_validade` → VENCIDO / MUITO_PROXIMO / PROXIMO / CONTROLADO / DISTANTE / NAO_DEFINIDO
- `@property dias_para_validade` (negativo quando vencido)
- `@property mostra_dias_restantes` (True para Vencido/MuitoPróximo/Próximo)
- **Único**: (medicamento, codigo)

### `Funcionario`
- `cpf`, `nome`, `funcao` (choices: MEDICO, ENFERMEIRO, TECNICO, MOTORISTA, FARMACEUTICO, ADMINISTRATIVO, COORDENADOR, AUXILIAR, OUTRO)
- `email` (único), `telefone`
- `usuario` OneToOne com User (opcional, para ligar login a profissional)
- `@property iniciais` para avatar

### `Veiculo`
- `codigo_id` (gerado automaticamente baseado no tipo: USB-01, MOTO-02, USA-03)
- `modelo`, `ano`, `tipo` ∈ {VAN, CARRO, MOTO}
- `status` ∈ {NORMAL, MANUTENCAO, INATIVO}

### `Movimentacao`
- `tipo` ∈ {ENTRADA, SAIDA}
- `lote` FK, `funcionario` FK (opcional), `usuario` FK User (opcional)
- `quantidade`, `origem`, `destino`, `observacao`, `horario`

### `Perfil`
- OneToOne com User
- `funcao` ∈ {ADMINISTRADOR, MOTORISTA, AUXILIAR, ENFERMEIRO}
- `telefone`, `data_nascimento`
- Propriedades `is_admin`, `pode_*` para RBAC
- `home_url_name` retorna rota inicial por papel

---

## 🎨 Paleta de cores (teoria das cores · harmonia)
- Branco `#FFFFFF`, cinza-claro `#F5F5F5`, cinza-escuro `#525252`, preto `#171717`.
- Laranja-escuro `#C2410C`, laranja-claro `#FDBA74`, laranja-pálido `#FFEDD5`.
- Vermelho-escuro `#7F1D1D`, vermelho-claro `#DC2626`, vermelho-pálido `#FEF2F2`.
- Verde (ok) `#16A34A` com `#DCFCE7` pálido.
- Amarelo (alerta) `#FBBF24`.

Fontes: **Bricolage Grotesque** (display), **Inter Tight** (texto), **JetBrains Mono** (código).

---

## 🧱 Páginas e seções

### 1. Login (`/login/`)
- Split screen: hero vermelho com "Salvar vidas começa no estoque." + formulário.
- Campos: usuário, senha, checkbox "Lembrar desta sessão".
- Erros em caixa vermelha, toasts para mensagens.

### 2. Registro (`/registrar/`)
- Campos obrigatórios: nome completo, data de nascimento, e-mail (único), telefone, função (dropdown com 4 opções), senha (mín 8, letras + números), confirmar senha.
- Checkbox "Lembrar desta sessão".

### 3. Medicamentos (`/medicamentos/`) — home padrão
- **5 KPIs** no topo com tooltips explicativos:
  - Medicamentos / Lotes / Baixo / Muito baixo / Validade.
- **Barra de busca** com autocomplete (sugestões em tempo real).
- **Filtros combináveis** em pills: Tipo, Forma, Nível (Muito baixo/Baixo/Normal/Alto), Validade (Vencido/Muito próximo/Próximo/Controlado/Distante), Lotes (multi-select).
- **Tabela agrupada por nome**: cada linha tem setinha `>` que, ao clicar, abre com animação **"pergaminho"** (scaleY + fade) uma seção com:
  - Variantes do mesmo nome (metragem/tipo/forma diferentes).
  - Lotes do medicamento com validade, quantidade, nível.
- Colunas: setinha, Nome, Metragem, Tipo, Forma, Lotes, Qtd. total, Status principal + ações (editar/excluir).
- Botões no topo (para quem pode editar): **Registrar entrada** (verde), **Registrar saída** (laranja), **Novo medicamento** (vermelho).

### 4. Novo/editar medicamento (`/medicamentos/novo/`)
- Campos: nome, metragem (ml/mg/mcg/%), tipo, forma, complemento (opcional).
- Ao criar novo: também mostra formulário do primeiro lote (código, validade, quantidade, situação).
- Autocomplete de códigos de lote baseado no nome do medicamento (sugere lotes já cadastrados).

### 5. Modal de Entrada/Saída
- Campos: Medicamento (autocomplete, obrigatório), Lote (autocomplete filtrado pelo med, obrigatório), Quantidade, Tipo e Forma (sem a palavra "desambiguação" — se vazios, pega o último cadastrado do mesmo nome), Origem/Destino (opcional).
- Validação crítica:
  - Saída > estoque → erro vermelho.
  - Lote inexistente → mensagem orientando cadastro.
  - Primeira movimentação do sistema: tipo, forma e lote **obrigatórios**.
- Após sucesso: toast verde no topo.

### 6. Funcionários (`/funcionarios/`) — apenas admin
- Barra de busca + filtro por função.
- Tabela: setinha `>`, avatar com iniciais, nome, CPF, função (badge), contato, ações.
- **Setinha abre histórico detalhado** (via fetch `/api/api/funcionarios/<id>/historico/`) com animação pergaminho:
  - Linha do tempo com cada manipulação: "Dr(a). Camila realizou a entrada de Adrenalina 1mg/mL em 15 unidades — Quarta-feira, 22/08/2026 às 19:45."
  - Ordem: mais recente primeiro.
  - Se não houver histórico: "Este funcionário ainda não possui histórico de manipulações."

### 7. Veículos (`/veiculos/`)
- Barra de busca + filtros por tipo (Van/Carro/Moto) e status.
- Tabela: setinha `>` (abre detalhes), ID gerado automaticamente, modelo, ano, tipo (badge), status (badge colorido), ações.
- Motorista pode criar/editar; apenas admin pode excluir.

### 8. Relatório (`/relatorio/`)
- Botões (admin apenas): **Anexar local** (escolhe pasta via `showDirectoryPicker`), **Baixar planilha (.xlsx)**, **Baixar PDF**.
- 5 KPIs no topo.
- **Dashboards de Medicamentos** (apenas se usuário tem permissão):
  1. Quantidade total por tipo (todos os tipos).
  2. Quantidade total por forma.
  3. Quantidade total por classificação de validade (Vencido/Muito próximo/Próximo/Controlado/Distante). Vazio se o admin ainda não configurou.
  4. Distribuição por situação (Recebidos/Entregues/Doados).
  5. Movimentação por usuário no intervalo configurável (padrão 30 dias). Campo numérico para alterar.
  6. Lotes com maior quantidade (top 20).
- **Dashboards de Frota** (admin + motorista):
  1. Veículos por status.
  2. Veículos por tipo.
- Cada gráfico tem **toggle** entre barras, pizza, rosca. Mostra **valor nominal + percentual** na legenda/tooltip.
- Cada card tem **título descritivo** e **descrição em até 3 linhas** explicando o que o gráfico mostra.
- **3 listas de alertas** (ordenadas do mais crítico ao menos):
  1. Vencidos / Muito próximos (do mais vencido ao menos).
  2. Estoque baixo / Muito baixo.
  3. Controlados.
- **4ª lista destacada em vermelho**: lotes que compartilham **2+** características críticas (ex.: baixo E vencendo).

### 9. Perfil + Painel do admin (`/perfil/`)
- Card lateral com avatar (iniciais) + nome + função + contatos.
- Formulário: nome completo, e-mail, telefone, data de nascimento. **Removido** o campo bio.
- Se usuário é admin, exibe o **Painel do Administrador** com:

**Subseção CONTAS**
- Tabela com todos os usuários cadastrados: nome, usuário, e-mail, função (badge), telefone, ações (editar / excluir).
- Editar: formulário em `/perfil/contas/<id>/editar/` permite trocar nome, e-mail, função, telefone, data nascimento e redefinir senha.
- Excluir: confirmação JS. Admin não pode excluir a si mesmo.

**Subseção DEFINIÇÕES**
- Campos para intervalos de estoque: muito baixo, baixo, alto (`estoque_muito_baixo < estoque_baixo < estoque_alto`).
- Campos para intervalos de validade: muito próximo, próximo, controlado (dias).
- Intervalo padrão para dashboards de movimentação (default 30 dias).
- Diretório padrão de downloads (texto livre).
- Validação: estoques crescentes, dias crescentes.

**Subseção MODO REDE LOCAL**
- Botão "Gerar link da rede local".
- Ao clicar: chama `/api/api/rede-local/` que retorna IPs locais da máquina (via `socket.gethostbyname_ex` + conexão UDP 8.8.8.8).
- Mostra lista de links `http://IP:8765/`. Cada um com botão **Copiar** (navigator.clipboard) e **Abrir** (link em nova aba).

**Subseção BANCO DE DADOS**
- Botão **Baixar backup** (.sqlite3): servidor fecha conexão, envia o arquivo via `FileResponse` com nome `samu192-backup-YYYYMMDD-HHMM.sqlite3`.
- Formulário **Restaurar**: upload de .sqlite3/.db + confirmação JS. Grava em tempfile, sobrescreve `db.sqlite3`, força logout.
- Formulário **Apagar dados**: usuário digita "APAGAR" para confirmar. Apaga Movimentacao → Lote → Medicamento → Funcionario → Veiculo. Preserva usuários e configuração.

---

## 🦶 Footer

Em todas as páginas, no rodapé:
- Logo SAMU + "Salvar vidas começa no estoque. Sistema oficial da unidade local do SAMU."
- "Este sistema foi desenvolvido por **Gustavo Batista**, todos os direitos reservados."
- "Cidade de Guanambi · CEP 46430-000 · 2026"
- Contato: `contato.profissional.gustavo@outlook.com`

Fundo: gradiente vermelho `from-samu-dark via-samu to-orange-deep` com textura noise. Linha divisória com "© 2026 · Gustavo Batista · SAMU 192 · v1.0".

---

## 🎨 Ícone oficial

Arquivo SVG `static/core/samu-logo.svg`:
- Fundo quadrado arredondado com gradiente vermelho.
- Estrela da Vida (6 pontas) em branco.
- Círculo central vermelho-escuro com cruz branca.
- Texto "SAMU 192" abaixo.

Arquivo `static/core/favicon.svg` (versão compacta sem texto).

Ao empacotar com PyInstaller, gerar `.ico` (Windows) ou `.icns` (macOS):
```bash
pip install cairosvg pillow
python -c "import cairosvg; cairosvg.svg2png(url='static/core/samu-logo.svg', write_to='samu.png', output_width=256, output_height=256)"
python -c "from PIL import Image; Image.open('samu.png').save('samu.ico', sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])"
```

E apontar no `samu192.spec`: `icon='samu.ico'`.

---

## 🏗️ Arquitetura técnica

### Estrutura de pastas
```
backend/
├── manage.py
├── main.py              # pywebview launcher (desktop)
├── server.py            # ASGI entrypoint (uvicorn)
├── samu192.spec         # PyInstaller spec
├── build_desktop.sh     # build script
├── db.sqlite3           # banco local
├── samu/                # projeto Django (settings/urls/asgi/wsgi)
├── core/                # app principal
│   ├── models.py        # 10 models
│   ├── views.py         # ~30 views
│   ├── forms.py         # forms com validação
│   ├── permissions.py   # RoleRequiredMixin, @role_required
│   ├── context_processors.py # sidebar role-aware
│   ├── exportacao.py    # PDF + XLSX
│   ├── admin.py
│   ├── urls.py
│   └── management/commands/seed_samu.py
├── templates/core/      # HTML
├── static/core/         # SVGs, (opcional) JS/CSS offline
├── README.md            # principal
├── README_INSTALL.md    # instalação detalhada
├── README_FIREBASE.md   # sync remoto
├── README_DEBUG.md      # erros possíveis
├── README_CRONOGRAMA.md # cronograma do projeto
└── README_PROMPT.md     # este arquivo
```

### Permissões via `RoleRequiredMixin`
Toda view sensível herda de `RoleRequiredMixin` e define `allowed_roles = ("ADMINISTRADOR", "AUXILIAR", ...)`.

### URL layout
Todas rotas sob `/api/` para compatibilidade com ingress na nuvem; no modo desktop local, `FORCE_SCRIPT_NAME` é removido.

---

## 🔄 Rede local

- `main.py` levanta o Django em `0.0.0.0:8765` quando usado como servidor; em desktop, usa `127.0.0.1`.
- Para expor na rede: `python manage.py runserver 0.0.0.0:8765`.
- O botão **Gerar link da rede local** no painel admin facilita a divulgação.
- Firewall precisa liberar a porta 8765 TCP (comandos documentados no README_INSTALL).
- Todos os dispositivos acessam o **mesmo banco** → consistência garantida.

---

## 📱 App Android

Opção A (recomendada): wrapper **Capacitor** apontando `server.url` para o IP do servidor local da unidade.
Opção B: **Chaquopy** com Django embarcado no APK (totalmente offline no celular).

---

## 🔥 Sync com Firebase (opcional)

Documentado em `README_FIREBASE.md`:
- **Opção A** (snapshot em Storage): `firebase_sync.py` com `upload` / `download`.
- **Opção B** (Firestore em tempo real): signals Django replicam cada save/delete.

---

## 🧪 Testes
- 22 testes pytest cobrindo CRUDs, movimentações, permissões, exportação, autocomplete.
- Casos de borda testados: saída > estoque, CPF inválido, auto-exclusão, admin único.

---

## ⚡ Casos de borda cobertos

| Cenário | Comportamento esperado |
|---------|------------------------|
| Saída de quantidade maior que o estoque do lote | Erro vermelho explicativo, estoque não muda |
| Tentar movimentar lote inexistente | Mensagem orientando cadastro antes |
| Duplicar medicamento (mesmo nome+metragem+tipo+forma) | IntegrityError prevenido no form |
| CPF em formato errado | Validação no clean do form |
| Admin tenta excluir a si próprio | Mensagem bloqueando |
| Dois dispositivos editam ao mesmo tempo (modo rede local) | SQLite serializa escritas, mas consulte README_DEBUG |
| Arquivo de restauração corrompido | `connection.close()` antes, tentativa de abrir no login após restaurar |
| Chart.js ou Lucide offline | Interface degrada visualmente mas não quebra |
| Validade não configurada pelo admin | Dashboard de validade fica vazio com mensagem |

---

## 📋 Checklist final de recriação

- [ ] 10 models com relacionamentos corretos.
- [ ] 4 papéis com sidebar filtrada por `context_processor`.
- [ ] Autocomplete em busca + nova entrada/saída + lote.
- [ ] Setinha expansível em medicamentos (variantes) e funcionários (histórico pergaminho).
- [ ] Modal entrada/saída com 4+ campos, validação rigorosa.
- [ ] 6 dashboards de medicamento + 2 de frota, com toggle de tipo de gráfico e valores nominais+%.
- [ ] 4 listas de alertas no relatório.
- [ ] Exportação PDF + XLSX (admin only) com histórico completo.
- [ ] Painel admin: Contas CRUD, Definições, Rede local, Backup/Restore/Apagar.
- [ ] Footer com dados do dev em todas as páginas.
- [ ] Favicon + logo SVG.
- [ ] 6 READMEs completos.
- [ ] PyInstaller + build script.
- [ ] Modo rede local funcionando end-to-end.

---

**Guanambi/BA, 2026.**
**Gustavo Batista** · contato.profissional.gustavo@outlook.com
