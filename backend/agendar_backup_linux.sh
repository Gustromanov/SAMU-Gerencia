#!/usr/bin/env bash
# SAMU 192 · Agenda o backup Firebase no cron (verifica de hora em hora; só envia
# quando o intervalo definido no painel já passou). Funciona com o binário ou o código-fonte.
# Remover:  crontab -l | grep -v '# SAMU192' | crontab -
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -x "$DIR/SAMU192" ]]; then
  CMD="\"$DIR/SAMU192\" --backup-firebase"
else
  PY="$DIR/.venv/bin/python"
  [[ -x "$PY" ]] || PY="$(command -v python3)"
  CMD="cd \"$DIR\" && \"$PY\" manage.py firebase_backup --se-vencido"
fi

LINHA="0 * * * * $CMD >> \"$DIR/firebase_backup.log\" 2>&1 # SAMU192"
( crontab -l 2>/dev/null | grep -v '# SAMU192' || true; echo "$LINHA" ) | crontab -

echo "✅ Backup agendado (de hora em hora):"
echo "   $LINHA"
echo "📄 Log: $DIR/firebase_backup.log"
