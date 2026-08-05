#!/usr/bin/env bash
# ============================================================================
# SAMU 192 · Build desktop (PyInstaller + pywebview)
# ============================================================================
# Este script empacota o sistema como um app desktop nativo (.exe/.app/binário)
# usando o `samu192.spec`. Rode ISSO NO SEU COMPUTADOR (Windows, macOS ou Linux).
#
# ➜ Windows:  bash build_desktop.sh  (em Git Bash / WSL) — produz dist/SAMU192/SAMU192.exe
# ➜ macOS:    bash build_desktop.sh                       — produz dist/SAMU 192.app
# ➜ Linux:    bash build_desktop.sh                       — produz dist/SAMU192/SAMU192
#
# Requisitos:
#   Python 3.10+ instalado localmente.
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")"

echo "🔧 Preparando ambiente virtual .venv-desktop..."
python -m venv .venv-desktop
# shellcheck source=/dev/null
source .venv-desktop/bin/activate 2>/dev/null || source .venv-desktop/Scripts/activate

echo "📦 Instalando dependências..."
python -m pip install --upgrade pip
python -m pip install \
  "django==5.1.4" \
  "whitenoise==6.8.2" \
  "openpyxl==3.1.5" \
  "reportlab==4.2.5" \
  "pywebview>=5.1" \
  "pyinstaller>=6.10"

echo "🗄️  Rodando migrações locais..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

echo "🏗️  Empacotando com PyInstaller..."
pyinstaller samu192.spec --clean --noconfirm

echo ""
echo "✅ Build concluído!"
echo "   Windows/Linux: dist/SAMU192/SAMU192(.exe)"
echo "   macOS:         dist/SAMU 192.app"
echo ""
echo "🚀 Para rodar sem empacotar (dev):  python main.py"
