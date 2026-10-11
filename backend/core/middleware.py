from . import firebase_sync


class AgendadorFirebaseMiddleware:
    """Inicia (uma vez por processo) o agendador de backup automático do Firebase."""

    def __init__(self, get_response):
        self.get_response = get_response
        firebase_sync.iniciar_agendador()

    def __call__(self, request):
        return self.get_response(request)
