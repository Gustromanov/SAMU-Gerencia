#!/usr/bin/env bash
# ============================================================================
# SAMU 192 · Build desktop (PyInstaller + pywebview) — Linux / macOS / Git Bash
# ============================================================================
#   Linux:   bash build_desktop.sh   → dist/SAMU192/SAMU192
#   macOS:   bash build_desktop.sh   → dist/SAMU 192.app
#   Windows: prefira build_windows.bat (duplo clique) → dist\SAMU192\SAMU192.exe
#
# Requisitos: Python 3.10+.  Linux: sudo apt install libcairo2 libegl1 libxkbcommon-x11-0 libxcb-cursor0
# Sem build cruzado: gere o .exe no Windows e o binário Linux no Linux
# (ou use o GitHub Actions: .github/workflows/build-desktop.yml).
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "🔧 Preparando ambiente virtual .venv-desktop..."
python3 -m venv .venv-desktop 2>/dev/null || python -m venv .venv-desktop
# shellcheck source=/dev/null
source .venv-desktop/bin/activate 2>/dev/null || source .venv-desktop/Scripts/activate

echo "📦 Instalando dependências..."
python -m pip install --upgrade pip
python -m pip install \
  "django==5.1.4" "whitenoise==6.8.2" "openpyxl==3.1.5" "reportlab==4.2.5" \
  "firebase-admin>=6.5" "pillow" "pyinstaller>=6.10"
if [[ "$(uname -s)" == "Linux" ]]; then
  python -m pip install "pywebview[qt]>=5.1"   # Linux usa Qt WebEngine
else
  python -m pip install "pywebview>=5.1"
fi

if [[ ! -f assets/icons/samu192.ico ]]; then
  echo "🎨 Gerando ícones a partir do SVG oficial..."
  python -m pip install cairosvg && python gerar_icones.py || echo "⚠️  cairosvg indisponível — build seguirá sem ícone novo"
else
  echo "🎨 Ícones já existem em assets/icons (rode 'python gerar_icones.py' para regerar)"
fi

echo "🗄️  Rodando migrações locais..."
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

echo "🏗️  Empacotando com PyInstaller..."
pyinstaller samu192.spec --clean --noconfirm

echo ""
echo "✅ Build concluído!"
echo "   Linux:  dist/SAMU192/SAMU192"
echo "   macOS:  dist/SAMU 192.app"
echo ""
echo "🚀 Rodar sem empacotar (dev):  python main.py"
echo "☁️  Backup agendado:            bash agendar_backup_linux.sh"
