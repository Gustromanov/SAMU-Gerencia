from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core import firebase_sync, models


class Command(BaseCommand):
    help = "Envia backup do banco + snapshot do estoque para o Firebase (ou para a pasta simulada)."

    def add_arguments(self, parser):
        parser.add_argument("--se-vencido", action="store_true",
                            help="Só envia se o intervalo configurado no painel já passou (ideal p/ cron/Agendador).")
        parser.add_argument("--simulado", action="store_true", help="Força o modo simulado nesta execução.")
        parser.add_argument("--testar", action="store_true", help="Apenas testa a conexão/configuração.")

    def handle(self, *args, **opts):
        if opts["testar"]:
            try:
                self.stdout.write(self.style.SUCCESS(firebase_sync.testar_conexao()))
            except Exception as exc:
                raise CommandError(f"Falha no teste: {exc}")
            return

        cfg = models.Configuracao.obter()
        ultimo = cfg.firebase_ultimo_backup
        if opts["se_vencido"] and ultimo and timezone.now() - ultimo < timedelta(hours=cfg.firebase_intervalo_horas):
            self.stdout.write(f"Backup em dia (último: {timezone.localtime(ultimo):%d/%m/%Y %H:%M}). Nada a fazer.")
            return

        r = firebase_sync.enviar_backup("TERMINAL", forcar_simulado=opts["simulado"])
        if r is None:
            raise CommandError("Já existe um backup em andamento.")
        if r.status == "ERRO":
            raise CommandError(f"Falha no backup: {r.mensagem}")
        self.stdout.write(self.style.SUCCESS(f"Backup OK ({r.get_modo_display()}) → {r.destino}"))
