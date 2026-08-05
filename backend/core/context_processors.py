"""Context processors globais (dados fixos para o layout)."""
from django.urls import reverse, NoReverseMatch


def sidebar_context(request):
    itens = [
        {"nome": "Medicamentos", "url": "medicamentos_lista", "icone": "pill"},
        {"nome": "Funcionários", "url": "funcionarios_lista", "icone": "users"},
        {"nome": "Veículos", "url": "veiculos_lista", "icone": "ambulance"},
        {"nome": "Relatório", "url": "relatorio", "icone": "chart"},
        {"nome": "Perfil", "url": "perfil", "icone": "user"},
    ]
    processados = []
    for item in itens:
        try:
            item = {**item, "href": reverse(item["url"])}
        except NoReverseMatch:
            item = {**item, "href": "#"}
        processados.append(item)
    return {"sidebar_itens": processados}
