# SAMU 192 · Guia completo de instalação nativa

> Para pessoas totalmente leigas: **copie e cole** os comandos exatamente como estão.

---

## 📑 Sumário
1. [O que é o SAMU 192](#-o-que-é-o-samu-192)
2. [Pré-requisitos](#-pré-requisitos)
3. [Instalação no Windows 10/11](#-instalação-no-windows-1011)
4. [Instalação no macOS](#-instalação-no-macos)
5. [Instalação no Linux (Ubuntu/Debian/Fedora/Arch)](#-instalação-no-linux)
6. [Como usar o sistema](#-como-usar-o-sistema)
7. [Compilar como app desktop nativo (.exe / .app / binário)](#-compilar-como-app-desktop-nativo-exe--app--binário)
8. [Compilar como app nativo Android (.apk)](#-compilar-como-app-nativo-android-apk)
9. [Suporte à rede local](#-suporte-à-rede-local)
10. [Backup, restauração e atualização](#-backup-restauração-e-atualização)

---

## 📦 O que é o SAMU 192

- Sistema web **monolítico** em Django + SQLite.
- Gerencia **medicamentos**, **lotes**, **funcionários**, **veículos**, **movimentações** e **relatórios**.
- Funciona offline (desktop) ou em rede local.
- Interface em português brasileiro.
- Suporta **4 papéis**: Administrador, Motorista, Auxiliar, Enfermeiro.

---

## 🎯 Pré-requisitos

- **Python 3.10 ou superior.** Teste no terminal: `python --version`
- Conexão à internet **apenas** na primeira instalação (para baixar bibliotecas).
- Espaço em disco: **~350 MB** com o ambiente completo.

---

## 🪟 Instalação no Windows 10/11

### 1. Instalar o Python
1. Baixe em https://www.python.org/downloads/windows/
2. Rode o instalador e **marque** `Add python.exe to PATH`.
3. Clique em **Install Now**.
4. Reinicie o PowerShell e teste: `python --version`.

### 2. Baixar o código
Extraia o `.zip` do projeto em `C:\SAMU192\` ou clone com git:
```powershell
git clone https://seu-repositorio.git C:\SAMU192
```

### 3. Preparar ambiente
```powershell
cd C:\SAMU192\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
> Se der erro de execução de scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Instalar dependências
```powershell
python -m pip install --upgrade pip
python -m pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 pywebview
```

### 5. Preparar banco e dados
```powershell
python manage.py migrate
python manage.py seed_samu
```

### 6. Rodar o app
```powershell
python main.py
```
Uma janela nativa abre. Login: **admin / samu192**.

### 7. Atalho no desktop
1. Clique com o botão direito → Novo → Atalho
2. Destino: `cmd /c "cd /d C:\SAMU192\backend && .\.venv\Scripts\python.exe main.py"`
3. Nome: **SAMU 192**

---

## 🍎 Instalação no macOS

### 1. Instalar Python via Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11
```

### 2. Baixar código e preparar
```bash
mkdir -p ~/SAMU192 && cd ~/SAMU192
# (extrair ZIP aqui ou git clone)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 pywebview
python manage.py migrate
python manage.py seed_samu
```

### 3. Rodar
```bash
python main.py
```

---

## 🐧 Instalação no Linux

### 1. Instalar dependências de sistema
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
    python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
    libcairo2-dev libgirepository1.0-dev
```

**Fedora:**
```bash
sudo dnf install -y python3 python3-virtualenv python3-pip \
    python3-gobject webkit2gtk4.1 cairo-gobject-devel gobject-introspection-devel
```

**Arch:**
```bash
sudo pacman -S --needed python python-virtualenv python-pip python-gobject webkit2gtk gobject-introspection
```

### 2. Projeto
```bash
sudo mkdir -p /opt/samu192 && sudo chown "$USER":"$USER" /opt/samu192
# extraia ou clone em /opt/samu192
cd /opt/samu192/backend
python3 -m venv .venv && source .venv/bin/activate
pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 "pywebview[gtk]"
python manage.py migrate
python manage.py seed_samu
python main.py
```

### 3. Atalho no menu de aplicativos
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

---

## 🖱️ Como usar o sistema

### Primeiro acesso
Entre com `admin / samu192`. **Mude a senha** em Perfil.

### Papéis
Ao criar uma conta nova em `/registrar/`, escolha a função. Cada papel vê páginas diferentes.

### Fluxo típico (admin)
1. **Definições** (Perfil → Painel do admin → Definições): configure intervalos de estoque e validade.
2. **Novo medicamento**: Medicamentos → Novo. Preencha nome, metragem, tipo, forma. Cadastre o primeiro lote.
3. **Registrar entrada/saída**: botões verdes/laranja no topo. Informe medicamento, lote, quantidade.
4. **Relatório**: veja gráficos e alertas. Exporte PDF ou XLSX.
5. **Backup**: Perfil → Painel do admin → Banco de dados → Baixar backup.

### Funções específicas
- **Motorista**: só vê Veículos e dashboard de frota.
- **Auxiliar/Enfermeiro**: Medicamentos (CRUD exceto excluir) + Relatório.
- **Administrador**: tudo + Funcionários (com histórico expansível) + Painel admin.

### Setinha expansível
- Em **Medicamentos**: a setinha mostra variantes com mesma identidade mas tipo/forma/metragem diferentes.
- Em **Funcionários** (admin): abre o histórico detalhado "Dr(a). Fulano realizou a entrada de X em N un — Quarta, 22/08/2026 às 19:45".
- Em **Veículos** (admin): mostra detalhes (cadastro, atualização).

### Validades
Admin define em Perfil → Definições os limites: Muito próximo (≤X dias), Próximo (≤Y), Controlado (≤Z). Acima disso = Distante. Vencidos aparecem com dias negativos.

---

## 📀 Compilar como app desktop nativo (.exe / .app / binário)

Já vem incluído: `samu192.spec` + `build_desktop.sh`.

```bash
cd backend
source .venv/bin/activate         # ou .\.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller samu192.spec --clean --noconfirm
```

Resultado:
- Windows: `dist/SAMU192/SAMU192.exe`
- macOS: `dist/SAMU 192.app`
- Linux: `dist/SAMU192/SAMU192`

> ⚠️ **Não há cross-build**. Para gerar `.exe` precisa rodar no Windows. Para `.app`, no macOS.

### Ícone oficial
O arquivo `static/core/samu-logo.svg` serve como logo. Para o executável use um `.ico` (Windows) ou `.icns` (macOS). Para gerar:
```bash
# a partir do SVG → PNG → ICO
pip install cairosvg pillow
python -c "import cairosvg; cairosvg.svg2png(url='static/core/samu-logo.svg', write_to='samu-icon.png', output_width=256, output_height=256)"
# Converte PNG para ICO (vários tamanhos)
python -c "from PIL import Image; i=Image.open('samu-icon.png'); i.save('samu.ico', sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])"
```
Depois edite `samu192.spec` e troque `icon=None` por `icon='samu.ico'` (ou `'samu.icns'` no mac).

---

## 📱 Compilar como app nativo Android (.apk)

O código é Django web — para rodar como app Android há duas estratégias:

### Opção A — WebView wrapper (mais simples) via Capacitor
1. Instale Node.js 20+ e Android Studio (com Android SDK 33+ e JDK 17).
2. Crie o wrapper:
   ```bash
   npm init @capacitor/app@latest samu-android
   cd samu-android
   npm install @capacitor/android @capacitor/core
   npx cap add android
   ```
3. Edite `capacitor.config.json`:
   ```json
   {
     "appId": "br.gov.samu.estoque",
     "appName": "SAMU 192",
     "webDir": "www",
     "server": { "url": "http://IP_DO_SERVIDOR:8765", "cleartext": true }
   }
   ```
   Troque `IP_DO_SERVIDOR` pelo IP real da máquina que roda o Django (modo rede local).
4. `npx cap open android` → menu Build → Build APK (ou AAB).
5. Instale o `.apk` gerado em `android/app/build/outputs/apk/release/`.

### Opção B — Chaquopy (Django embutido no APK)
Para rodar Django **dentro do APK** (totalmente offline no celular):
1. Instale Android Studio + Chaquopy plugin.
2. Crie projeto Android com `python-source` apontando para `backend/`.
3. Configure `build.gradle`:
   ```gradle
   plugins { id 'com.chaquo.python' version '15.0.1' }
   python {
       pip { install 'django==5.1.4'; install 'whitenoise'; install 'openpyxl'; install 'reportlab' }
       pyc { src false }
   }
   ```
4. Em `MainActivity.java` inicie o servidor Django em thread background com `WSGIServer` e aponte um `WebView` para `http://127.0.0.1:8765/`.
5. Build → APK.

> 💡 **Recomendado para a maioria dos casos: Opção A** (WebView + servidor na unidade). Isso mantém **um só banco de dados compartilhado** entre todos os celulares/tablets, exatamente o que a unidade quer.

---

## 🌐 Suporte à rede local

Qualquer uma das plataformas (Windows/Mac/Linux/Android) pode acessar **o mesmo banco** desde que:

1. Um PC roda o servidor Django com `python manage.py runserver 0.0.0.0:8765` (ou o app desktop já faz isso).
2. Admin acessa Perfil → Painel do admin → **Modo rede local** → **Gerar link da rede local** → copia o link `http://IP:8765/`.
3. Outros dispositivos (celulares, PCs, tablets) abrem esse link no navegador — todos veem **os mesmos dados em tempo real**.

Se um auxiliar der baixa num celular, o admin em outro PC vê a alteração ao recarregar.

> ⚠️ Para que a janela desktop também aceite conexões de fora, use `python manage.py runserver 0.0.0.0:8765` em vez de `python main.py` (que só abre em 127.0.0.1).

---

## 💾 Backup, restauração e atualização

### Backup
- **Via interface**: Perfil → Painel do admin → Banco de dados → Baixar backup.
- **Via arquivo**: copie `backend/db.sqlite3` para onde quiser.

### Restaurar
- **Via interface**: Perfil → Painel do admin → Banco → selecione o arquivo → Restaurar (confirma sobrescrita).
- **Via arquivo**: substitua `db.sqlite3` pelo backup.

### Backup diário automatizado (Linux)
```bash
crontab -e
# adicione:
0 23 * * * cp /opt/samu192/backend/db.sqlite3 /var/backups/samu-$(date +\%F).sqlite3
```

### Atualização
1. Faça backup do `db.sqlite3`.
2. Baixe novo código.
3. `pip install -r requirements.txt` (se mudou).
4. `python manage.py migrate`.
5. `python main.py`.

Nenhum dado é perdido porque o banco fica separado do código.
