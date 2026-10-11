# SAMU 192 · Guia de depuração (todos os erros possíveis)

> Lista completa de erros conhecidos, suas causas prováveis e como resolver.

---

## 📑 Índice rápido

- [1. Erros de instalação](#1-erros-de-instalação)
- [2. Erros de servidor Django](#2-erros-de-servidor-django)
- [3. Erros de banco de dados](#3-erros-de-banco-de-dados)
- [4. Erros de login/CSRF](#4-erros-de-logincsrf)
- [5. Erros de interface](#5-erros-de-interface)
- [6. Erros de permissão](#6-erros-de-permissão-funçãorole)
- [7. Erros de movimentação (entrada/saída)](#7-erros-de-movimentação-entradasaída)
- [8. Erros de relatório / gráficos](#8-erros-de-relatório--gráficos)
- [9. Erros de exportação (PDF/XLSX)](#9-erros-de-exportação-pdfxlsx)
- [10. Erros de rede local / pywebview](#10-erros-de-rede-local--pywebview)
- [11. Erros do PyInstaller (empacotamento)](#11-erros-do-pyinstaller-empacotamento)
- [12. Erros do Firebase](#12-erros-do-firebase)

---

## 1. Erros de instalação

### `'python' is not recognized as an internal or external command` (Windows)
**Causa:** Python não está no PATH.
**Solução:** Reinstale o Python marcando `Add python.exe to PATH`, ou use `py` em vez de `python`.

### `Set-ExecutionPolicy ... cannot be loaded because running scripts is disabled`
**Causa:** PowerShell bloqueia execução do script de ativação do venv.
**Solução:** `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (uma vez).

### `error: Microsoft Visual C++ 14.0 or greater is required`
**Causa:** Alguma dep. com extensão C precisa de compilador no Windows.
**Solução:** Baixar "Build Tools for Visual Studio" ou usar `pip install --only-binary=:all: <pacote>`.

### `cannot import name 'gi'` (Linux)
**Causa:** Falta `python3-gi`.
**Solução:** `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1`.

### `ERROR: Could not install packages due to an EnvironmentError: ... Permission denied`
**Causa:** Está instalando no Python de sistema sem venv.
**Solução:** Ative o `.venv` antes de rodar `pip install`.

---

## 2. Erros de servidor Django

### `Error: That port is already in use.`
**Causa:** Outra instância do Django já roda na porta 8765/8001.
**Solução:**
- Linux: `ss -tulpn | grep 8765` → `kill <PID>`.
- Windows: `netstat -ano | findstr 8765` → `taskkill /PID <PID> /F`.
- Ou rode em outra porta: `python manage.py runserver 0.0.0.0:8766`.

### `AttributeError: 'Request' object has no attribute 'user'`
**Causa:** `AuthenticationMiddleware` fora de ordem.
**Solução:** Certifique que `django.contrib.auth.middleware.AuthenticationMiddleware` está depois do `SessionMiddleware` em `MIDDLEWARE`.

### `ASGI 'lifespan' protocol appears unsupported.`
**Causa:** uvicorn espera eventos de lifespan que Django não implementa.
**Solução:** Apenas um warning, **ignorar**. Não é erro.

### `TemplateDoesNotExist: core/base.html`
**Causa:** `TEMPLATES.DIRS` não aponta para a pasta correta.
**Solução:** confira `settings.py`: `"DIRS": [BASE_DIR / "templates"]`.

---

## 3. Erros de banco de dados

### `django.db.utils.OperationalError: no such table: core_medicamento`
**Causa:** Migrations não aplicadas.
**Solução:** `python manage.py migrate`.

### `django.db.utils.IntegrityError: UNIQUE constraint failed: core_medicamento.nome, core_medicamento.metragem, core_medicamento.tipo_id, core_medicamento.forma_id`
**Causa:** Tentativa de criar duas vezes o mesmo medicamento com mesma combinação de nome+metragem+tipo+forma.
**Solução:** Edite o existente ou mude a combinação (ex.: outra metragem).

### `django.db.utils.OperationalError: database is locked`
**Causa:** Múltiplos processos escrevendo no SQLite simultaneamente.
**Solução:**
- Feche instâncias duplicadas do app.
- Em alta concorrência, use o modo rede local (um servidor + clientes).
- Em desenvolvimento, defina `OPTIONS: {"timeout": 20}` no DATABASES.

### `sqlite3.DatabaseError: file is not a database`
**Causa:** O arquivo `db.sqlite3` está corrompido.
**Solução:** Restaure o último backup (`.sqlite3`) via Perfil → Painel admin → Restaurar.

### `IntegrityError: NOT NULL constraint failed: core_lote.medicamento_id`
**Causa:** Tentou criar um Lote sem associar a um Medicamento.
**Solução:** Sempre crie o Medicamento primeiro.

---

## 4. Erros de login/CSRF

### `CSRF verification failed. Origin checking failed`
**Causa:** O domínio da origem não está em `CSRF_TRUSTED_ORIGINS` do settings.
**Solução:** Adicione o domínio em `backend/samu/settings.py` → `CSRF_TRUSTED_ORIGINS`.

### `CSRF token missing or incorrect`
**Causa:** Cookie `csrftoken` não está sendo enviado.
**Solução:**
- Garanta `{% csrf_token %}` dentro de todo `<form method="post">`.
- Em requests fetch(), inclua `credentials: 'include'`.

### `Please enter a correct username and password`
**Causa:** Credenciais erradas, ou usuário não tem Perfil.
**Solução:** Confira as credenciais. Se persistir, o seed cria automaticamente: `admin/samu192`.

### Login funciona mas redireciona para `/api/login/` em loop
**Causa:** Cookie de sessão não é mantido.
**Solução:** Confira `SESSION_ENGINE` e `SESSION_COOKIE_AGE` em settings. Teste em modo anônimo.

---

## 5. Erros de interface

### Setinha de expansão não abre
**Causa:** JavaScript do Lucide não carregou OU erro de JS.
**Solução:** Abra o DevTools (F12) → Console. Veja o erro. Normalmente é um `data-testid` mal escrito.

### Ícones aparecem como `<i data-lucide="pill">` em texto
**Causa:** CDN do Lucide bloqueada ou falha de rede.
**Solução:** Verifique conexão. Para offline, baixe `lucide.min.js` em `static/core/` e aponte o `<script src>` para o arquivo local.

### Modal "Registrar entrada" fecha sem registrar
**Causa:** Validação de formulário falhou mas usuário não viu o erro.
**Solução:** Veja a toast no canto superior direito. Também preencha **todos** os campos obrigatórios: Medicamento, Lote, Quantidade.

### Autocomplete não mostra sugestões
**Causa:** Endpoint `/api/api/busca/...` retornando erro.
**Solução:** Teste manualmente: `curl http://127.0.0.1:8765/api/api/busca/medicamentos/?q=adre` com cookies de sessão.

---

## 6. Erros de permissão (função/role)

### "Acesso negado. Esta área está disponível apenas para: ADMINISTRADOR"
**Causa:** Você está logado com conta que não é admin tentando acessar página restrita.
**Solução:** Faça login com admin ou peça para o administrador aprovar seu acesso.

### Motorista vê menu "Medicamentos"
**Causa:** `context_processors.sidebar_context` não filtra corretamente.
**Solução:** Confira `MENU_ITENS` em `core/context_processors.py` — Medicamentos não deve ter "MOTORISTA" nas roles.

### Admin não consegue excluir conta própria
**Causa:** Proteção propositalmente colocada para não deixar o sistema sem admins.
**Solução:** Peça outro admin para excluir sua conta.

---

## 7. Erros de movimentação (entrada/saída)

### "Estoque insuficiente no lote X: há N unidades, mas a saída pede M."
**Causa:** Tentando dar saída de mais do que existe.
**Solução:** Diminua a quantidade ou use outro lote com estoque.

### "O lote 'XYZ' não está cadastrado para Medicamento Z"
**Causa:** Lote informado não existe.
**Solução:** Cadastre o lote (Medicamento → + Novo lote) antes de movimentar.

### "Medicamento não encontrado"
**Causa:** Nome/ID não corresponde a nenhum cadastro.
**Solução:** Cadastre o medicamento primeiro em Medicamentos → Novo medicamento.

### Entrada ou saída não aparece no histórico
**Causa:** Movimentação não foi salva (erro silencioso).
**Solução:** Verifique logs do backend: `tail -f /var/log/supervisor/backend.err.log`.

---

## 8. Erros de relatório / gráficos

### Gráfico "Validade" aparece vazio
**Causa:** Admin ainda não configurou intervalos de validade.
**Solução:** Perfil → Painel do admin → Definições → defina Muito próximo, Próximo, Controlado → Salvar.

### Toggle entre barras/pizza/rosca não funciona
**Causa:** Chart.js CDN bloqueado.
**Solução:** F12 → Console. Se bloqueado, baixe `chart.umd.min.js` para `static/core/`.

### Gráfico de movimentação sem dados
**Causa:** Não há movimentações no intervalo configurado.
**Solução:** Aumente o intervalo de dias no campo acima do gráfico.

---

## 9. Erros de exportação (PDF/XLSX)

### `ModuleNotFoundError: No module named 'openpyxl'`
**Solução:** `pip install openpyxl==3.1.5`.

### `ModuleNotFoundError: No module named 'reportlab'`
**Solução:** `pip install reportlab==4.2.5`.

### Download abre mas o arquivo está vazio ou corrompido
**Causa:** Erro durante geração no servidor.
**Solução:** Veja logs do backend. Normalmente envolve data de validade inválida ou tipo inesperado.

### Botões "Baixar PDF" não aparecem
**Causa:** Você não é admin — apenas admin pode exportar.

---

## 10. Erros de rede local / pywebview

### "Gerar link da rede local" mostra apenas 127.0.0.1
**Causa:** Máquina não tem IP de rede detectável.
**Solução:**
- Linux: `ip addr show`.
- Windows: `ipconfig`.
- Garanta estar conectado à Wi-Fi/rede cabeada.

### Outros PCs não conseguem acessar `http://IP:8765/`
**Causa:** Firewall bloqueando porta 8765 OU servidor rodando em `127.0.0.1` em vez de `0.0.0.0`.
**Solução:**
- Firewall Windows: `netsh advfirewall firewall add rule name="SAMU" dir=in action=allow protocol=TCP localport=8765`.
- Linux: `sudo ufw allow 8765`.
- Rode: `python manage.py runserver 0.0.0.0:8765`.

### pywebview: `cannot import name 'webview'`
**Solução:** `pip install pywebview` (Linux: `pywebview[gtk]`).

### Janela desktop abre em branco
**Causa:** Servidor Django não subiu antes do webview.
**Solução:** No `main.py`, aumente o tempo de `_find_free_port` wait, ou abra manualmente `http://127.0.0.1:8765/`.

---

## 11. Erros do PyInstaller (empacotamento)

### `ModuleNotFoundError` quando o `.exe` roda
**Causa:** Módulo faltando em `hiddenimports` do `samu192.spec`.
**Solução:** Adicione o nome do módulo em `hiddenimports=[...]` e rebuilde: `pyinstaller samu192.spec --clean`.

### `.exe` abre e fecha imediatamente
**Causa:** Erro Python sem terminal visível.
**Solução:** Mude `console=True` no `.spec` para ver mensagens, depois volte para `False`.

### Arquivo gerado é gigante (>300 MB)
**Causa:** PyInstaller empacota tudo.
**Solução:** No `.spec` adicione em `excludes=['tkinter', 'matplotlib', ...]` o que não é necessário.

### Ícone não aparece no `.exe`
**Causa:** Formato incorreto (deve ser `.ico` com múltiplos tamanhos).
**Solução:** Regenere o `.ico` (ver `README_INSTALL.md`).

---

## 12. Erros do Firebase

### `[Errno 2] No such file or directory: 'firebase-key.json'`
**Solução:** Baixe a chave privada do console Firebase (ver `README_FIREBASE.md`) e salve como `backend/firebase-key.json`.

### `google.auth.exceptions.DefaultCredentialsError`
**Causa:** Credenciais mal formatadas.
**Solução:** Re-gere a chave privada no console Firebase.

### `403 Forbidden` ao fazer upload
**Causa:** Regras de Storage não permitem.
**Solução:** No console Firebase → Storage → Regras, use modo "test" por 30 dias para teste.

### Dois dispositivos editando ao mesmo tempo → último grava
**Causa:** Opção A (snapshot) é "last writer wins".
**Solução:** Migre para Firestore (Opção B) ou use modo rede local (um servidor + clientes).

---

## 📞 Suporte

Se nenhum dos itens acima resolver, envie um e-mail para **contato.profissional.gustavo@outlook.com** anexando:
- O log completo do erro (terminal onde rodou o app).
- Sistema operacional + versão do Python.
- Passos que levaram ao erro.

---

## 🧰 Comandos úteis de diagnóstico

```bash
# Logs do Django (uvicorn via supervisor)
tail -f /var/log/supervisor/backend.err.log

# Testar banco diretamente
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM core_medicamento;"

# Resetar completamente (CUIDADO: apaga dados)
rm db.sqlite3
python manage.py migrate
python manage.py seed_samu

# Testar health check
curl http://127.0.0.1:8765/api/healthz/
```
