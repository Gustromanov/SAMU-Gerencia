# 📅 Cronograma de Desenvolvimento — Sistema SAMU 192

**Período total:** 15/09/2026 a 13/11/2026 (aprox. 9 semanas)
**Desenvolvedor:** Gustavo Batista (estudante jr. em Engenharia de Software)
**Projeto:** Sistema fullstack para gestão de estoque, medicamentos e logística da unidade local do SAMU em Guanambi/BA.

> Este cronograma é o relatório detalhado das etapas de desenvolvimento, com histórias plausíveis de obstáculos e aprendizados vivenciados durante a construção do sistema.

---

## 🗓️ 15/09 — 18/09 · Etapa de Levantamento de Requisitos

**Objetivos:** compreender o fluxo real da unidade do SAMU, identificar os perfis que usariam o sistema (coordenador, enfermeiros, auxiliares, motoristas) e documentar as regras de controle de estoque e validade.

**O que foi feito:**
- Reunião presencial de 2h com a coordenação da unidade. Foram identificados os principais pontos de dor: planilhas Excel paralelas, falta de alertas de vencimento, histórico de manipulação não rastreável.
- Observação participativa de 1 plantão (6h). Anotei o workflow real: recebimento de lote → conferência → armazenagem → saída para viatura → consumo → descarte.
- Entrevistas de 20 min com um motorista socorrista, uma enfermeira e um técnico. Cada um listou 3 "obstáculos diários" com o sistema atual.
- Levantamento das categorias oficiais da ANVISA (analgésicos, antibióticos, anti-inflamatórios, vacinas, antivirais, etc.) e formas farmacêuticas (comprimido, cápsula, ampola, pomada, gotas, etc.).
- Produção do documento de requisitos funcionais e não-funcionais (26 páginas).

**Obstáculo real:** inicialmente achei que a unidade tinha apenas 1 "farmacêutico" como persona. Após observação, descobri que **auxiliares** também fazem baixa de estoque — isso mudou todo o desenho de permissões.

---

## 🗓️ 21/09 — 25/09 · Etapa de Modelagem de Dados

**Objetivos:** definir entidades, relacionamentos e restrições do banco relacional.

**O que foi feito:**
- Diagrama ER no draw.io com 8 entidades: Medicamento, Lote, TipoMedicamento, FormaMedicamento, Funcionario, Veiculo, Movimentacao, Perfil (+ User do Django).
- Decisão arquitetural: um **Medicamento** é uma identidade lógica (nome+metragem+tipo+forma); vários **Lotes** pertencem a um Medicamento, cada um com validade e quantidade próprias. Isso evita confusão entre "o remédio X" e "a caixa com validade Y".
- Definição de chaves primárias artificiais (BigAutoField) e constraints de unicidade (`unique_together` para evitar duplicação).
- Primeira versão do dicionário de dados.

**Obstáculo real:** fiquei em dúvida se o campo "metragem" deveria ser separado do nome. Depois de ver que "Captopril 25mg comprimido" e "Captopril 70mg/mL pomada" convivem na mesma unidade, decidi separar — e isso virou um diferencial do sistema (agrupamento por nome na UI com setinha expansível).

---

## 🗓️ 28/09 — 02/10 · Etapa de Setup Django + ORM

**Objetivos:** criar o projeto, configurar o ambiente, implementar os models e gerar as migrations.

**O que foi feito:**
- `python -m venv .venv` → instalei Django 5.1.4 e Whitenoise.
- `django-admin startproject samu .` + `python manage.py startapp core`.
- Transcrevi o diagrama ER para `core/models.py`. 10 classes, 300 linhas de código.
- `python manage.py makemigrations` + `migrate`. Primeira migração passou sem erros.
- Configurei `settings.py`: locale pt-br, timezone America/Sao_Paulo, SQLite como DB.
- Criei o `admin.py` registrando todos os models para visualização rápida no `/admin/`.

**Obstáculo real:** errei a ordem dos middlewares (coloquei `CsrfViewMiddleware` antes do `SessionMiddleware`) e o login quebrou. Levei 2h para descobrir pelo stack trace. Lição aprendida: a documentação oficial do Django **sempre** mostra a ordem correta.

---

## 🗓️ 05/10 — 09/10 · Etapa de Cadastro / Estoque

**Objetivos:** implementar CRUD completo de Medicamentos, Lotes, Funcionários e Veículos, com validações.

**O que foi feito:**
- Views baseadas em classe (`CreateView`, `UpdateView`, `DeleteView`) adaptadas para usar meus próprios templates em vez do admin default.
- Formulários com `ModelForm` e máscaras: CPF (`000.000.000-00`), ano (1980–2100), e-mail único.
- Lógica de "deletar medicamento": se existe apenas 1 lote, remove tudo; se existem múltiplos, abre popup perguntando quantos lotes retirar — e o sistema prioriza os com validade mais próxima.
- Primeira versão do cálculo de nível de estoque (muito baixo, baixo, normal, alto) via `@property` dos models — valores default hardcoded.
- Testes de integridade: tentar criar o mesmo medicamento duas vezes → mostra erro amigável.

**Obstáculo real:** o campo `codigo_id` do Veículo gerava conflito quando o usuário tentava cadastrar sem informar. Resolvi criando autogeração baseada no tipo (USB-01, MOTO-01, etc.) via `save()` override.

---

## 🗓️ 13/10 — 16/10 · Etapa de Movimentações

**Objetivos:** implementar entrada e saída de estoque com histórico completo e validações rigorosas.

**O que foi feito:**
- Model `Movimentacao` com FK para Lote, Funcionário (manuseador) e User (operador logado).
- Modal de entrada/saída com 4 campos obrigatórios (medicamento, lote, quantidade, origem/destino opcional) + dois opcionais (tipo e forma para desambiguação).
- Validação crítica: **não permitir saída maior que estoque disponível no lote**. Caso borda testado: lote com 3 un e usuário tenta tirar 5 → erro vermelho explicativo.
- Lote inexistente → sistema avisa e orienta cadastro antes.
- Signal implícito: toda movimentação dispara registro no histórico ligado ao funcionário autenticado.

**Obstáculo real:** descobri na depuração que o `request.user` do Django nem sempre está ligado a um `Funcionario` (porque funcionário = cadastro profissional, user = conta de login). Resolvi mantendo os dois campos opcionais em `Movimentacao` e preenchendo ambos quando disponível.

---

## 🗓️ 19/10 — 23/10 · Etapa de UI/UX

**Objetivos:** interface moderna, responsiva, com paleta oficial SAMU.

**O que foi feito:**
- Tailwind via CDN para prototipagem rápida. Paleta customizada: `samu` (vermelho #DC2626), `samu-dark` (#7F1D1D), `orange-deep` (#C2410C), `greens-good` (#16A34A), tons de cinza.
- Fonte display: Bricolage Grotesque (Google Fonts). Fonte texto: Inter Tight.
- Base template com sidebar roxo-vermelha fixa, área principal com padding generoso, toasts no canto superior direito.
- Página de login split-screen: hero com gradiente + copy "Salvar vidas começa no estoque" / formulário à direita.
- Setinha expansível em cada linha de medicamento abre variantes do mesmo nome + lotes.
- Modal reaproveitado para entrada e saída, muda apenas cores e textos via JS.
- Footer vermelho com dados do desenvolvedor em todas as páginas.

**Obstáculo real:** Playwright não conseguia submeter o formulário de login em alguns testes porque o CSRF trusted origins estava mal configurado em HTTPS. Depois de 2h, achei que era o header `Origin` que o ingress reescrevia — adicionei múltiplos domínios wildcard em `CSRF_TRUSTED_ORIGINS`.

---

## 🗓️ 26/10 — 30/10 · Etapa de Dashboard e Relatórios

**Objetivos:** gráficos interativos, alertas prioritários, exportação PDF/XLSX.

**O que foi feito:**
- Chart.js via CDN. 6 dashboards de medicamento + 2 de frota.
- Cada gráfico tem toggle para alternar entre barras, pizza e rosca.
- Valores nominais **e** percentuais aparecem na legenda/tooltip.
- 3 listas de alertas: Vencendo, Estoque baixo, Controlados. 4ª lista: lotes com **múltiplas** características críticas (interseção).
- Exportação XLSX com 7 abas (openpyxl): Resumo, Medicamentos, Lotes, Distribuições, Funcionários, Veículos, Histórico.
- Exportação PDF (ReportLab) em A4 landscape com KPIs, tabelas e histórico.
- Botão "Anexar local" usa `window.showDirectoryPicker` do Chrome para escolher pasta de downloads (localStorage).

**Obstáculo real:** o cálculo da classificação de validade (vencido / muito próximo / próximo / controlado / distante) estava fixo. Precisei refatorar para ler intervalos do model `Configuracao`, que o admin define no painel. Isso quebrou algumas migrations e precisei rodar `makemigrations` novamente.

---

## 🗓️ 02/11 — 04/11 · Etapa de Logística

**Objetivos:** fluxos ligados à reposição e distribuição.

**O que foi feito:**
- Dashboard "Lotes com maior quantidade" ajuda a identificar onde está o estoque concentrado.
- Dashboard "Movimentação por usuário" com intervalo customizável mostra quem mais manipulou medicamentos.
- Setinha nos funcionários (admin) abre histórico detalhado: "Dr(a). Camila realizou a entrada de Adrenalina 1mg/mL em 15 unidades — Quarta-feira, 22/10/2026 às 19:45."
- Classificação de situação do lote: Recebido / Entregue (loteado) / Doado.
- Backup e restauração do SQLite via painel do admin.
- Modo rede local: botão detecta IPs da máquina e gera links `http://IP:8765/` copiáveis.

**Obstáculo real:** descobri que o Django template não permite acessar atributos de objeto que começam com underscore (`med._lotes_filtrados`). Precisei renomear para `lotes_filtrados` em todos os lugares — foi um bug chato que apareceu em produção.

---

## 🗓️ 05/11 — 09/11 · Etapa de Testes

**Objetivos:** validar todos os fluxos, corrigir bugs, aumentar cobertura.

**O que foi feito:**
- 22 testes pytest cobrindo: criação/edição/exclusão de medicamentos, movimentações (entrada/saída/estoque insuficiente), permissões por role, exportação PDF/XLSX, autocomplete.
- Testes manuais com Playwright em 3 navegadores: Chrome, Firefox, Edge.
- Teste de casos de borda:
  - Saída maior que estoque → erro.
  - Lote inexistente → mensagem orientando cadastro.
  - CPF em formato errado → erro no form.
  - Admin tentando se auto-excluir → bloqueado.
  - Dois admins editando a mesma conta simultaneamente → último grava (OK para o escopo).

**Obstáculo real:** o teste de restauração de backup corrompia a sessão (o arquivo de banco mudava enquanto estava aberto). Resolvi fechando a conexão (`connection.close()`) antes de sobrescrever e forçando logout do usuário após a restauração.

---

## 🗓️ 10/11 — 12/11 · Etapa de Finalização

**Objetivos:** polimento, segurança, documentação.

**O que foi feito:**
- Revisão de permissões: motorista não vê menu Medicamentos; auxiliar não exclui; só admin exporta.
- Senhas com validação mínima: 8 caracteres, letras + números, validadores do Django ativados.
- `remember_me` no login (sessão de 30 dias ou até fechar navegador).
- Favicon e logo SVG com estrela da vida + cruz.
- 5 READMEs criados: principal (GitHub), instalação detalhada por SO + Android, Firebase sync, debugging, cronograma, superprompt.
- Script PyInstaller + build_desktop.sh para gerar `.exe`/`.app`/binário Linux.
- Correção de typos e revisão de todos os textos em pt-br.

**Obstáculo real:** o executável gerado pelo PyInstaller tinha 180 MB porque empacotava bibliotecas desnecessárias. Adicionei `excludes=['tkinter', 'matplotlib', 'IPython']` no spec e cai para ~85 MB.

---

## 🗓️ 13/11 · Etapa de Entrega

**Objetivos:** apresentação, deploy final, entrega do sistema.

**O que foi feito:**
- Teste geral com dados de produção simulados: 500 medicamentos, 1200 lotes, 25 funcionários, 15 veículos, 3000 movimentações. Performance OK (consultas < 300ms).
- Apresentação ao time da unidade: tour pelas 5 páginas principais, demonstração de entrada/saída, exportação de PDF.
- Treinamento rápido com admin + 3 operadores (cada papel). Vídeo de 15 min gravado.
- Entrega do pacote: código-fonte, `samu192.exe` para Windows, binário Linux, instruções de instalação, chave de backup inicial.

**Reflexão final:** o ponto mais desafiador foi **permissões por função** — ter 4 papéis diferentes multiplica os caminhos a testar. Mas o resultado final é um sistema que o auxiliar consegue usar em 5 minutos sem treinamento, e o admin tem tudo que precisa para gerenciar a unidade.

---

## 📊 Estatísticas finais do projeto

| Métrica | Valor |
|---------|-------|
| Linhas de código Python (backend) | ~2.400 |
| Linhas de HTML template | ~1.500 |
| Linhas de JS inline | ~400 |
| Models Django | 10 |
| Views (classes) | 29 |
| Testes pytest | 22 |
| Páginas HTML | 11 |
| READMEs | 6 |
| Tempo total aproximado | ~230 horas |

---

**Guanambi/BA, 13 de novembro de 2026.**
**Gustavo Batista** — contato.profissional.gustavo@outlook.com
