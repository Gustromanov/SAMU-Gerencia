# SAMU 192 · Instalação Nativa (Windows & Linux)

> Sistema de gestão de estoque, medicamentos, funcionários e frota para a unidade **local** do SAMU.
> Roda **100 % offline** na máquina, com banco SQLite persistente e janela nativa (pywebview).

---

## 📑 Sumário

1. [O que você vai instalar](#-o-que-você-vai-instalar)
2. [Pré-requisitos](#-pré-requisitos)
3. [Passo a passo — Windows 10 / 11](#-instalação-no-windows-10--11)
4. [Passo a passo — Linux (Ubuntu / Debian / Fedora / Arch)](#-instalação-no-linux)
5. [Primeiro login e uso](#-primeiro-login-e-uso)
6. [Gerar executável distribuível (.exe / binário)](#-gerar-executável-distribuível-exe--binário)
7. [Rodar como serviço no boot (Linux)](#-rodar-como-serviço-no-boot-linux-opcional)
8. [Backup, restauração e atualização](#-backup-restauração-e-atualização)
9. [Solução de problemas](#-solução-de-problemas-faq)
10. [Comandos úteis](#-comandos-úteis-cheat-sheet)

---

## 📦 O que você vai instalar

| Componente | Versão | O que faz |
|------------|--------|-----------|
| Python | 3.10+ (recomendado 3.11) | Runtime da aplicação |
| Django | 5.1.4 | Framework do sistema |
| SQLite | (embutido no Python) | Banco de dados local |
| pywebview | 5+ | Abre janela desktop nativa |
| ReportLab | 4.2.5 | Gera relatórios em PDF |
| openpyxl | 3.1.5 | Gera relatórios em XLSX |
| Whitenoise | 6.8.2 | Serve arquivos estáticos |
| PyInstaller | 6+ *(opcional)* | Cria o `.exe` / binário |

Espaço em disco: **~350 MB** (com ambiente virtual completo).
Consumo em memória: **~120 MB**.

---

## 🎯 Pré-requisitos

- **Python 3.10 ou superior** (verifique com `python --version`).
- **Acesso à internet** somente durante a instalação (para baixar as bibliotecas). Depois pode rodar 100 % offline.
- Nenhuma outra aplicação usando a porta **8765** (o app procura outra automaticamente se estiver ocupada).

---

## 🪟 Instalação no Windows 10 / 11

### 1. Instalar o Python

1. Baixe **Python 3.11 ou superior** em https://www.python.org/downloads/windows/
2. Rode o instalador e **marque** "Add python.exe to PATH" na primeira tela.
3. Escolha "Install Now".
4. Ao final, abra o **PowerShell** e verifique:
   ```powershell
   python --version
   pip --version
   ```
   Deve mostrar Python 3.11+ e pip 24+.

### 2. Obter o código-fonte

Você tem duas opções:

**Opção A — arquivo ZIP** (mais simples):
1. Baixe/receba o arquivo `.zip` do projeto.
2. Extraia em uma pasta que você escolher — por exemplo `C:\SAMU192\`.

**Opção B — Git** (se souber usar):
```powershell
git clone https://seu-repositorio.git C:\SAMU192
```

### 3. Preparar o ambiente Python

Abra o **PowerShell** na pasta do projeto:

```powershell
cd C:\SAMU192\backend

# Cria ambiente virtual isolado
python -m venv .venv

# Ativa o ambiente
.\.venv\Scripts\Activate.ps1
```

> Se aparecer erro de "execução de scripts desabilitada", rode uma vez como administrador:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Instalar as dependências

```powershell
python -m pip install --upgrade pip
python -m pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 pywebview
```

> Em **Windows 10**, a biblioteca `pywebview` usa o **WebView2** (motor do Edge Chromium).
> Ele já vem instalado em Windows 10 21H2+ e Windows 11. Se não estiver, o próprio
> pywebview aponta para o instalador oficial no primeiro run.

### 5. Preparar o banco e popular dados iniciais

```powershell
python manage.py migrate
python manage.py seed_samu
```

Isso cria:
- `db.sqlite3` — banco local (mantido no diretório `backend/`)
- Usuário administrador: **`admin` / `samu192`**
- 32 medicamentos, 44 lotes, 10 funcionários, 8 veículos, 35 movimentações de exemplo

### 6. Rodar o aplicativo

```powershell
python main.py
```

Uma janela nativa abre com o SAMU 192. **Pronto.** 🎉

Para fechar o app basta fechar a janela. Para reabrir depois:
```powershell
cd C:\SAMU192\backend
.\.venv\Scripts\Activate.ps1
python main.py
```

### 7. (Opcional) Criar atalho no menu iniciar

1. Botão direito na Área de Trabalho → **Novo → Atalho**.
2. Como destino, cole:
   ```
   cmd /c "cd /d C:\SAMU192\backend && .\.venv\Scripts\python.exe main.py"
   ```
3. Nomeie como **SAMU 192**.
4. (Opcional) Botão direito no atalho → **Propriedades → Alterar Ícone** → escolha o `.ico` da sua preferência.

---

## 🐧 Instalação no Linux

Instruções para as principais distribuições. Escolha a sua.

### 1. Instalar Python + libs de sistema

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
    python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
    libcairo2-dev libgirepository1.0-dev
```

**Fedora**
```bash
sudo dnf install -y python3 python3-virtualenv python3-pip \
    python3-gobject webkit2gtk4.1 cairo-gobject-devel \
    gobject-introspection-devel
```

**Arch / Manjaro**
```bash
sudo pacman -S --needed python python-virtualenv python-pip \
    python-gobject webkit2gtk gobject-introspection
```

> Essas libs GTK/WebKit são o que o `pywebview` usa para desenhar a janela desktop no Linux.

### 2. Obter o código-fonte

```bash
# Escolha o diretório de instalação
sudo mkdir -p /opt/samu192
sudo chown "$USER":"$USER" /opt/samu192

# Opção A — ZIP
unzip samu192.zip -d /opt/samu192

# Opção B — Git
git clone https://seu-repositorio.git /opt/samu192
```

### 3. Preparar o ambiente Python

```bash
cd /opt/samu192/backend

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 \
    reportlab==4.2.5 "pywebview[gtk]"
```

### 4. Preparar o banco e popular dados iniciais

```bash
python manage.py migrate
python manage.py seed_samu
```

### 5. Rodar o aplicativo

```bash
python main.py
```

A janela GTK abre com o sistema. Feche a janela para encerrar.

### 6. (Opcional) Atalho no menu de aplicativos

Crie `/usr/share/applications/samu192.desktop`:
```ini
[Desktop Entry]
Name=SAMU 192
Comment=Sistema de estoque e logística
Exec=/opt/samu192/backend/.venv/bin/python /opt/samu192/backend/main.py
Icon=applications-healthcare
Terminal=false
Type=Application
Categories=Office;Utility;
```

Salve e o atalho aparece no menu.

---

## 🔑 Primeiro login e uso

Ao abrir a janela do app pela primeira vez:

- **Usuário:** `admin`
- **Senha:** `samu192`

Mude a senha imediatamente em **Perfil → Salvar alterações** (recomendado antes de usar em produção).

Recursos principais (barra lateral):

| Aba | Para quê |
|-----|----------|
| **Medicamentos** | Lista com filtros, KPIs, autocomplete, botões *Registrar entrada / saída* |
| **Funcionários** | CRUD com CPF, função, histórico de movimentações |
| **Veículos** | Frota com status (Normal / Manutenção / Inativo) |
| **Relatório** | KPIs, gráficos, alertas e **exportação PDF / XLSX** |
| **Perfil** | Editar seus dados |

---

## 📀 Gerar executável distribuível (.exe / binário)

Já vem incluído: `backend/samu192.spec` + `backend/build_desktop.sh`.

### Windows → gera `SAMU192.exe`

Dentro do ambiente virtual ativado (`(.venv)`):

```powershell
pip install pyinstaller
pyinstaller samu192.spec --clean --noconfirm
```

Ao final: **`dist\SAMU192\SAMU192.exe`**
Copie a pasta inteira `dist\SAMU192\` para o computador de destino — é auto-suficiente, não precisa Python instalado.

### Linux → gera binário nativo

Dentro do venv:

```bash
pip install pyinstaller
bash build_desktop.sh
```

Ao final: **`dist/SAMU192/SAMU192`**
Torne executável se necessário: `chmod +x dist/SAMU192/SAMU192`

> ⚠️ **Não é possível cross-build** com PyInstaller.
> Para gerar `.exe`, você **precisa** rodar em Windows.
> Para gerar binário Linux, rode em Linux.

---

## 🔁 Rodar como serviço no boot (Linux, opcional)

Se você quer o SAMU 192 rodando como servidor local acessível a outras máquinas da rede da unidade (`http://ip-da-maquina:8765`), sem janela desktop:

Crie `/etc/systemd/system/samu192.service`:
```ini
[Unit]
Description=SAMU 192 · Sistema de estoque
After=network.target

[Service]
Type=simple
User=samu
WorkingDirectory=/opt/samu192/backend
Environment=DJANGO_SETTINGS_MODULE=samu.settings
ExecStart=/opt/samu192/backend/.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8765
Restart=always

[Install]
WantedBy=multi-user.target
```

Habilite e inicie:
```bash
sudo useradd -r -s /bin/false samu || true
sudo chown -R samu:samu /opt/samu192
sudo systemctl daemon-reload
sudo systemctl enable --now samu192
```

Acesse de qualquer navegador da rede: `http://<ip-do-servidor>:8765/`

> ⚠️ Nesse modo, edite `samu/settings.py` e adicione o IP/domínio em `ALLOWED_HOSTS`.
> Também comente ou remova `FORCE_SCRIPT_NAME = "/api"` para servir na raiz.

---

## 💾 Backup, restauração e atualização

O banco fica em **um único arquivo**: `backend/db.sqlite3`.

### Backup manual

**Windows**
```powershell
Copy-Item C:\SAMU192\backend\db.sqlite3 D:\Backups\samu-$(Get-Date -Format yyyyMMdd).sqlite3
```

**Linux**
```bash
cp /opt/samu192/backend/db.sqlite3 ~/backups/samu-$(date +%F).sqlite3
```

### Backup agendado (Linux, cron diário às 23h)

```bash
crontab -e
# adicione a linha:
0 23 * * * cp /opt/samu192/backend/db.sqlite3 /var/backups/samu-$(date +\%F).sqlite3
```

### Restaurar

Basta substituir `db.sqlite3` pelo arquivo de backup e reiniciar o app.

### Atualizar o código

1. Faça backup do `db.sqlite3` (sempre).
2. Substitua os arquivos do projeto.
3. Ative o venv, rode `pip install -r <lista_atualizada>` se houver novas libs.
4. Aplique migrações: `python manage.py migrate`.
5. Rode `python main.py`.

Nenhum dado é perdido porque o banco fica separado do código.

---

## 🛠 Solução de problemas (FAQ)

**"`python` não é reconhecido" (Windows)**
Você não marcou "Add to PATH" na instalação. Reinstale o Python marcando essa opção, ou use `py` em vez de `python`.

**"Set-ExecutionPolicy" bloqueando o venv no PowerShell**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Janela desktop não abre no Linux ("cannot import name 'gi'")**
Faltam as libs GTK/WebKit. Rode novamente o `apt install`/`dnf install` da seção 1.

**Porta 8765 ocupada**
O `main.py` já tenta uma porta livre automaticamente. Se persistir, mate o processo antigo:
```bash
ss -tulpn | grep 8765
kill <PID>
```

**Preciso resetar o banco / dados de teste**
```bash
rm db.sqlite3
python manage.py migrate
python manage.py seed_samu
```

**Esqueci a senha do admin**
```bash
python manage.py changepassword admin
```

**Quero criar outro usuário administrador**
```bash
python manage.py createsuperuser
```

**PyInstaller reclama de módulos ocultos**
O `samu192.spec` já lista os principais. Se um novo módulo faltar, adicione-o em `hiddenimports=[...]` e rebuilde com `pyinstaller samu192.spec --clean`.

**Como saber se o sistema está funcionando?**
Abra `http://127.0.0.1:8765/api/healthz/` (no modo web) — deve responder `{"status":"ok"}`.

---

## 📜 Comandos úteis (cheat sheet)

Ative o ambiente virtual antes de tudo:
- Windows: `.venv\Scripts\Activate.ps1`
- Linux: `source .venv/bin/activate`

| Ação | Comando |
|------|---------|
| Rodar o app desktop | `python main.py` |
| Rodar somente servidor (sem janela) | `python -m uvicorn server:app --host 0.0.0.0 --port 8765` |
| Aplicar migrações | `python manage.py migrate` |
| Popular dados de exemplo | `python manage.py seed_samu` |
| Criar superusuário | `python manage.py createsuperuser` |
| Alterar senha | `python manage.py changepassword <usuario>` |
| Rodar admin Django | acesse `/api/admin/` no navegador |
| Rodar testes | `pytest tests/ -v` |
| Empacotar executável | `pyinstaller samu192.spec --clean` |
| Coletar arquivos estáticos | `python manage.py collectstatic --noinput` |

---

## 📞 Ajuda

- Logs de erro aparecem no terminal onde você rodou `python main.py`.
- Todos os dados operacionais (medicamentos, funcionários, veículos, movimentações) estão em `db.sqlite3`. É seguro copiar/mover esse arquivo entre máquinas da mesma versão do sistema.
- Para reportar problemas, anexe o log do terminal + a versão do Python (`python --version`) + sistema operacional.

---

**Salvar vidas começa no estoque. 🚑**
