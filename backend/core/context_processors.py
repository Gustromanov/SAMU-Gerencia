"""Context processors globais (dados fixos para o layout)."""
from __future__ import annotations

from django.urls import reverse, NoReverseMatch
from .models import Configuracao


# Mapeamento (nome, url_name, ícone, roles permitidos)
MENU_ITENS = [
    ("Medicamentos", "medicamentos_lista", "pill", {"ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO"}),
    ("Funcionários", "funcionarios_lista", "users", {"ADMINISTRADOR"}),
    ("Veículos", "veiculos_lista", "ambulance", {"ADMINISTRADOR", "MOTORISTA"}),
    ("Relatório", "relatorio", "chart", {"ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO", "MOTORISTA"}),
    ("Perfil", "perfil", "user", {"ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO", "MOTORISTA"}),
]


def sidebar_context(request):
    user = request.user
    funcao = "ADMINISTRADOR"
    if getattr(user, "is_authenticated", False):
        perfil = getattr(user, "perfil", None)
        funcao = perfil.funcao if perfil else "ADMINISTRADOR"

    itens = []
    for nome, url_name, icone, roles in MENU_ITENS:
        if funcao not in roles:
            continue
        try:
            href = reverse(url_name)
        except NoReverseMatch:
            href = "#"
        itens.append({"nome": nome, "url": url_name, "icone": icone, "href": href})

    return {
        "sidebar_itens": itens,
        "funcao_atual": funcao,
    }


def configuracao_context(request):
    """Disponibiliza a configuração global para todos os templates."""
    return {"CONFIG": Configuracao.obter()}
