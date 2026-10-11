@echo off
REM ============================================================================
REM SAMU 192 - Build do executavel Windows (duplo clique ou rode no CMD)
REM Resultado: dist\SAMU192\SAMU192.exe  (com icone oficial assets\icons\samu192.ico)
REM Requisito: Python 3.10+ instalado com "Add python.exe to PATH" marcado.
REM ============================================================================
setlocal
cd /d "%~dp0"

echo [SAMU 192] Preparando ambiente .venv-desktop...
if not exist .venv-desktop (
    py -3 -m venv .venv-desktop 2>nul || python -m venv .venv-desktop || goto :erro
)
call .venv-desktop\Scripts\activate.bat || goto :erro

echo [SAMU 192] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install django==5.1.4 whitenoise==6.8.2 openpyxl==3.1.5 reportlab==4.2.5 "firebase-admin>=6.5" pillow "pywebview>=5.1" "pyinstaller>=6.10" || goto :erro

if not exist assets\icons\samu192.ico (
    echo [SAMU 192] Gerando icones a partir do SVG...
    python -m pip install cairosvg && python gerar_icones.py || echo [aviso] cairosvg indisponivel - build sem icone novo
)

echo [SAMU 192] Migrando banco...
python manage.py migrate --noinput || goto :erro
python manage.py collectstatic --noinput

echo [SAMU 192] Empacotando com PyInstaller...
pyinstaller samu192.spec --clean --noconfirm || goto :erro

echo.
echo [OK] Executavel gerado em: %~dp0dist\SAMU192\SAMU192.exe
echo      Copie a pasta dist\SAMU192 inteira para o PC da unidade.
echo      Backup agendado: rode agendar_backup_windows.bat dentro dessa pasta.
pause
exit /b 0

:erro
echo.
echo [ERRO] Falha no build. Consulte README_DEBUG.md (secao PyInstaller).
pause
exit /b 1
