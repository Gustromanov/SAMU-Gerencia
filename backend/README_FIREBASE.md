# SAMU 192 · Sincronização com Firebase

> Como subir o banco SQLite do SAMU 192 para o Firebase e manter todos os dispositivos sincronizados.
> Instruções detalhadas tanto pelo **site do Firebase** quanto pelo **terminal**.

---

## 📑 Sumário
1. [Visão geral da estratégia](#-visão-geral-da-estratégia)
2. [Pré-requisitos](#-pré-requisitos)
3. [Criar o projeto no Firebase](#-criar-o-projeto-no-firebase)
4. [Opção A — Sync via Firebase Storage (snapshot do SQLite)](#-opção-a--sync-via-firebase-storage-snapshot-do-sqlite)
5. [Opção B — Migrar para Firestore (NoSQL em tempo real)](#-opção-b--migrar-para-firestore-nosql-em-tempo-real)
6. [Rodar no Windows](#-rodar-no-windows)
7. [Rodar no Linux](#-rodar-no-linux)
8. [Automação periódica](#-automação-periódica)
9. [Troubleshooting](#-troubleshooting)

---

## 🎯 Visão geral da estratégia

O SAMU 192 nasceu **monolítico com SQLite** (um único arquivo `db.sqlite3`). Para sincronizar entre dispositivos existem duas abordagens:

| Opção | Como funciona | Quando usar |
|-------|---------------|-------------|
| **A — Snapshot em Storage** | A cada ação relevante, o arquivo `db.sqlite3` é enviado para o Firebase Storage. Outros dispositivos baixam a versão mais recente antes de abrir. | Pequena unidade (até 50 operações/dia). Simples e confiável. |
| **B — Firestore em tempo real** | Cada modelo é espelhado em uma coleção Firestore. Sync é instantâneo entre dispositivos. | Múltiplos usuários simultâneos em dispositivos diferentes. |

> ⭐ **Recomendado para o SAMU local**: **Opção A** combinada com modo rede local (um PC servidor + outros clientes na Wi-Fi).

---

## 🎯 Pré-requisitos

- Conta Google (gratuita).
- Python 3.10+ já instalado (ver `README_INSTALL.md`).
- Terminal (PowerShell no Windows, bash no Linux/Mac).

---

## 🔥 Criar o projeto no Firebase

### 1. Pelo site (recomendado para quem é leigo)

1. Acesse https://console.firebase.google.com/ e faça login.
2. Clique em **Adicionar projeto** → nome **`samu-192-estoque`** → próximo → desabilite o Analytics se não precisar → Criar.
3. No menu lateral, clique em **Build → Storage** → **Começar** → selecione o modo "test" por 30 dias (o acesso é liberado para esse período) → escolha a região `southamerica-east1` (São Paulo).
4. (Opcional) **Build → Firestore Database** → Criar banco → modo "test" → região `southamerica-east1`.

### 2. Baixar a chave de serviço (API)
1. Menu lateral → ⚙ **Configurações do projeto** → aba **Contas de serviço**.
2. Clique em **Gerar nova chave privada** → confirma → baixa `samu-192-estoque-firebase-adminsdk-xxxxx.json`.
3. Guarde esse arquivo em `backend/firebase-key.json`. **NUNCA** envie ao Git público.
4. Adicione `firebase-key.json` ao `.gitignore`.

### 3. (Alternativa) Pelo CLI Firebase
```bash
npm install -g firebase-tools
firebase login
firebase projects:create samu-192-estoque
```

---

## 🅰️ Opção A — Sync via Firebase Storage (snapshot do SQLite)

### Instalar o SDK
```bash
cd backend
source .venv/bin/activate                 # ou Windows: .\.venv\Scripts\Activate.ps1
pip install firebase-admin==6.5.0
```

### Script `firebase_sync.py`
Crie `backend/firebase_sync.py`:
```python
"""
Sincroniza db.sqlite3 com Firebase Storage.
Uso:
    python firebase_sync.py upload   # envia o banco local
    python firebase_sync.py download # baixa o banco remoto
"""
import os, sys
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, storage

BASE = Path(__file__).resolve().parent
cred = credentials.Certificate(str(BASE / "firebase-key.json"))
firebase_admin.initialize_app(cred, {"storageBucket": "samu-192-estoque.appspot.com"})

bucket = storage.bucket()
blob = bucket.blob("backups/db.sqlite3")
local = BASE / "db.sqlite3"

cmd = sys.argv[1] if len(sys.argv) > 1 else "upload"
if cmd == "upload":
    blob.upload_from_filename(str(local))
    print("✓ Enviado para Firebase Storage.")
elif cmd == "download":
    blob.download_to_filename(str(local))
    print("✓ Banco local atualizado a partir do Firebase.")
else:
    print("Uso: python firebase_sync.py [upload|download]")
```

> Troque `samu-192-estoque.appspot.com` pelo nome real do bucket (ver aba Storage no console Firebase).

### Fluxo de uso diário
1. **Ao iniciar o dia**: `python firebase_sync.py download` (pega última versão).
2. Trabalha normalmente no sistema.
3. **Ao fechar**: `python firebase_sync.py upload` (envia alterações).

### Automatizar no `main.py`
Edite `backend/main.py` logo após `_prepare_database()`:
```python
try:
    import firebase_sync  # noqa
    firebase_sync.blob.download_to_filename(str(Path(__file__).parent / "db.sqlite3"))
    print("[SAMU] Sincronizado com Firebase.")
except Exception as e:
    print(f"[SAMU] Modo offline (Firebase não disponível): {e}")
```

E crie um hook de upload ao fechar a janela:
```python
import atexit
atexit.register(lambda: __import__("firebase_sync").blob.upload_from_filename("db.sqlite3"))
```

---

## 🅱️ Opção B — Migrar para Firestore (NoSQL em tempo real)

Esta opção **substitui** o SQLite por Firestore. Requer refatorar o `models.py` para usar `firebase_admin.firestore`.

### Instalar
```bash
pip install firebase-admin==6.5.0 django-firebase-storage
```

### Criar `backend/firebase_init.py`
```python
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path

cred = credentials.Certificate(str(Path(__file__).parent / "firebase-key.json"))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()
```

### Criar adapters para cada modelo
Exemplo para `Medicamento`:
```python
# core/firestore_adapters.py
from firebase_init import db

def medicamento_salvar(m):
    db.collection("medicamentos").document(str(m.id)).set({
        "nome": m.nome, "metragem": m.metragem,
        "tipo": m.tipo.nome, "forma": m.forma.nome,
        "complemento": m.complemento,
        "atualizado_em": m.atualizado_em.isoformat(),
    })

def medicamento_apagar(id):
    db.collection("medicamentos").document(str(id)).delete()
```

### Hook via signals do Django
```python
# core/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Medicamento
from .firestore_adapters import medicamento_salvar, medicamento_apagar

@receiver(post_save, sender=Medicamento)
def _s(sender, instance, **kwargs):
    medicamento_salvar(instance)

@receiver(post_delete, sender=Medicamento)
def _d(sender, instance, **kwargs):
    medicamento_apagar(instance.id)
```

Registre no `apps.py`:
```python
# core/apps.py
from django.apps import AppConfig
class CoreConfig(AppConfig):
    name = "core"
    def ready(self):
        from . import signals  # noqa
```

### Regras de segurança (console Firebase → Firestore → Regras)
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      // Em produção, substitua por autenticação real
      allow read, write: if true;
    }
  }
}
```

---

## 🪟 Rodar no Windows

```powershell
cd C:\SAMU192\backend
.\.venv\Scripts\Activate.ps1
pip install firebase-admin==6.5.0

# Enviar backup
python firebase_sync.py upload

# Baixar última versão
python firebase_sync.py download
```

Agendar backup diário às 22h:
1. Abra o **Agendador de Tarefas** do Windows.
2. Criar Tarefa Básica → "SAMU Firebase upload" → Diário → 22:00.
3. Ação: Iniciar programa → `C:\SAMU192\backend\.venv\Scripts\python.exe` com argumento `firebase_sync.py upload` e diretório `C:\SAMU192\backend`.

---

## 🐧 Rodar no Linux

```bash
cd /opt/samu192/backend
source .venv/bin/activate
pip install firebase-admin==6.5.0

python firebase_sync.py upload
python firebase_sync.py download
```

Agendar via cron:
```bash
crontab -e
# backup diário às 22h
0 22 * * * /opt/samu192/backend/.venv/bin/python /opt/samu192/backend/firebase_sync.py upload
```

---

## 🔁 Automação periódica

### Watcher (sincroniza quando o DB muda)
```bash
pip install watchdog
```

Crie `backend/firebase_watch.py`:
```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import firebase_sync

class H(FileSystemEventHandler):
    def on_modified(self, e):
        if e.src_path.endswith("db.sqlite3"):
            firebase_sync.blob.upload_from_filename(e.src_path)
            print("[Sync] Enviado.")

o = Observer()
o.schedule(H(), path=".", recursive=False)
o.start()
try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    o.stop()
o.join()
```

Rode em background:
- **Windows**: `start /B python firebase_watch.py`
- **Linux**: `nohup python firebase_watch.py &`

---

## 🩹 Troubleshooting

**`[Errno 2] No such file: firebase-key.json`**
Baixe a chave privada e salve em `backend/firebase-key.json`.

**`Permission denied` ao fazer upload**
Verifique as regras de Storage no console: devem estar em modo test ou com autenticação configurada.

**Conflito entre dois dispositivos editando ao mesmo tempo**
Com Opção A, o último `upload` ganha. Para evitar: use modo rede local (um servidor + clientes) **ou** migre para Opção B (Firestore em tempo real).

**Backup grande / lento**
O SQLite comprime bem com gzip. Modifique `firebase_sync.py` para enviar `.sqlite3.gz` em vez de puro.

---

## ✅ Backup Firebase já integrado ao sistema (v1.1)

> As opções A/B acima são referência. A partir da v1.1 **não precisa escrever código**: tudo está em **Perfil → Painel do Administrador → Backup Firebase**.

### O que é enviado
| Destino | Conteúdo |
|---|---|
| Storage `samu192/backups/samu192-AAAAMMDD-HHMMSS.sqlite3.gz` | Cópia consistente do `db.sqlite3` (API de backup do SQLite) compactada |
| Firestore `samu192/snapshot` | Resumo em JSON: medicamentos + lotes + validade + níveis, veículos e KPIs (lido pelo app Android) |

### Passo a passo (5 min)
1. **Console Firebase** → crie o projeto → ative **Firestore Database** (modo produção) e **Storage**.
2. **Configurações do projeto → Contas de serviço → Gerar nova chave privada** → baixa um `.json`.
3. No SAMU 192 (admin): **Perfil → Backup Firebase**
   - Envie o `.json` em *Chave da conta de serviço* (fica em `backend/secrets/`, fora do Git).
   - Preencha o *Bucket* (aparece no topo da página Storage: `meu-projeto.appspot.com` ou `meu-projeto.firebasestorage.app`).
   - **Desmarque "Modo simulado"** → **Salvar configurações** → **Testar conexão**.
4. Clique **Enviar backup agora**. O histórico mostra data, origem, tamanho e destino `gs://…`.
5. Publique as regras de `firebase/firestore.rules` e `firebase/storage.rules` (Console → Regras).

### Modo simulado (padrão)
Sem credenciais, os backups vão para `backend/backups_firebase_simulado/` (mantém os 10 últimos + `snapshot.json`). Serve para testar todo o fluxo sem internet.

### Formas de disparar o backup
| Gatilho | Como |
|---|---|
| Manual | Botão **Enviar backup agora** |
| Automático | Marque *Backup automático* + intervalo em horas (roda enquanto o sistema estiver aberto) |
| Ao fazer login | *Sincronizar ao fazer login* — qualquer login (PC ou APK) envia, no máx. a cada 10 min |
| Terminal | `python manage.py firebase_backup` (`--se-vencido`, `--simulado`, `--testar`) |
| Executável | `SAMU192.exe --backup-firebase` (só envia se o intervalo venceu) |

### Agendar no sistema operacional (mesmo com o app fechado)
```bat
:: Windows — clique com o botão direito → Executar como administrador
backend\agendar_backup_windows.bat
:: remover:  schtasks /Delete /TN "SAMU192 Backup Firebase" /F
```
```bash
# Linux — adiciona ao crontab (de hora em hora, respeita o intervalo do painel)
bash backend/agendar_backup_linux.sh
# remover:  crontab -l | grep -v '# SAMU192' | crontab -
```

### Restaurar a partir do Firebase
Console → Storage → `samu192/backups/` → baixe o `.gz` → descompacte (7-Zip no Windows, `gunzip` no Linux) → **Perfil → Banco de dados → Restaurar** com o `.sqlite3`.

### App Android lendo o Firebase
1. Console → **Authentication → Método de login → E-mail/senha → Ativar** → aba **Usuários → Adicionar usuário** (um por profissional).
2. Console → **Configurações do projeto → Seus apps → Web (`</>`)** → registre o app → copie o bloco `firebaseConfig`.
3. No celular: **Consulta offline (Firebase)** → cole o `firebaseConfig` → entre com o e-mail/senha → o app baixa o `samu192/snapshot` e guarda uma cópia para ver mesmo sem internet.

### Erros comuns
| Mensagem | Solução |
|---|---|
| `Credenciais do Firebase não enviadas` | Envie o `.json` ou volte ao modo simulado |
| `Chave privada inválida no JSON` | Baixe uma nova chave; não edite o arquivo |
| `404 … bucket does not exist` | Bucket errado ou Storage não ativado |
| `403 … permission` | A conta de serviço precisa do papel *Firebase Admin* (padrão da chave gerada) |
| App Android: `Sem permissão para ler os dados` | Publique `firebase/firestore.rules` e confirme o login |

