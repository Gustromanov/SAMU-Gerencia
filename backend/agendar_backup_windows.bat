@echo off
REM ============================================================================
REM SAMU 192 - Agenda o backup Firebase no Agendador de Tarefas do Windows.
REM Roda de hora em hora, mas so envia quando o intervalo definido no painel
REM (Perfil > Backup Firebase) ja passou. Funciona com o .exe ou com o codigo-fonte.
REM Remover: schtasks /Delete /TN "SAMU192 Backup Firebase" /F
REM ============================================================================
setlocal
cd /d "%~dp0"

if exist "%~dp0SAMU192.exe" (
    set "ALVO=\"%~dp0SAMU192.exe\" --backup-firebase"
    goto :agendar
)

set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"
set "ALVO=\"%PY%\" \"%~dp0manage.py\" firebase_backup --se-vencido"

:agendar
schtasks /Create /F /SC HOURLY /TN "SAMU192 Backup Firebase" /TR "%ALVO%" || goto :erro
echo.
echo [OK] Tarefa "SAMU192 Backup Firebase" criada (verifica a cada hora).
echo      Ver/editar: Agendador de Tarefas ^> Biblioteca ^> SAMU192 Backup Firebase
pause
exit /b 0

:erro
echo [ERRO] Nao foi possivel criar a tarefa. Execute este arquivo como Administrador.
pause
exit /b 1
