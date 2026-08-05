from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("", views.RootRedirectView.as_view(), name="root"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("registrar/", views.RegistrarView.as_view(), name="registrar"),

    # Medicamentos (lista = home após login)
    path("medicamentos/", views.MedicamentosListaView.as_view(), name="medicamentos_lista"),
    path("medicamentos/novo/", views.MedicamentoFormView.as_view(), name="medicamento_novo"),
    path("medicamentos/<int:pk>/editar/", views.MedicamentoFormView.as_view(), name="medicamento_editar"),
    path("medicamentos/<int:pk>/excluir/", views.MedicamentoExcluirView.as_view(), name="medicamento_excluir"),
    path(
        "medicamentos/<int:pk>/lotes/novo/",
        views.LoteFormView.as_view(),
        name="lote_novo",
    ),
    path(
        "lotes/<int:pk>/editar/",
        views.LoteFormView.as_view(),
        name="lote_editar",
    ),
    path("lotes/<int:pk>/excluir/", views.LoteExcluirView.as_view(), name="lote_excluir"),

    # Movimentações
    path("movimentar/", views.MovimentarView.as_view(), name="movimentar"),

    # Funcionários
    path("funcionarios/", views.FuncionariosListaView.as_view(), name="funcionarios_lista"),
    path("funcionarios/novo/", views.FuncionarioFormView.as_view(), name="funcionario_novo"),
    path(
        "funcionarios/<int:pk>/editar/",
        views.FuncionarioFormView.as_view(),
        name="funcionario_editar",
    ),
    path(
        "funcionarios/<int:pk>/excluir/",
        views.FuncionarioExcluirView.as_view(),
        name="funcionario_excluir",
    ),

    # Veículos
    path("veiculos/", views.VeiculosListaView.as_view(), name="veiculos_lista"),
    path("veiculos/novo/", views.VeiculoFormView.as_view(), name="veiculo_novo"),
    path("veiculos/<int:pk>/editar/", views.VeiculoFormView.as_view(), name="veiculo_editar"),
    path("veiculos/<int:pk>/excluir/", views.VeiculoExcluirView.as_view(), name="veiculo_excluir"),

    # Relatório
    path("relatorio/", views.RelatorioView.as_view(), name="relatorio"),
    path("relatorio/exportar/pdf/", views.RelatorioExportarPdf.as_view(), name="relatorio_pdf"),
    path("relatorio/exportar/xlsx/", views.RelatorioExportarXlsx.as_view(), name="relatorio_xlsx"),

    # Perfil
    path("perfil/", views.PerfilView.as_view(), name="perfil"),

    # APIs JSON (autocomplete)
    path("api/busca/medicamentos/", views.BuscaMedicamentosJson.as_view(), name="api_busca_medicamentos"),
    path("api/busca/funcionarios/", views.BuscaFuncionariosJson.as_view(), name="api_busca_funcionarios"),
    path("api/busca/veiculos/", views.BuscaVeiculosJson.as_view(), name="api_busca_veiculos"),
    path("api/relatorio/", views.RelatorioJson.as_view(), name="api_relatorio"),

    # Health check
    path("healthz/", views.HealthView.as_view(), name="healthz"),
]
