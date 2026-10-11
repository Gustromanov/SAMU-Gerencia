from django.contrib import admin
from . import models


@admin.register(models.TipoMedicamento)
class TipoMedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug"); prepopulated_fields = {"slug": ("nome",)}


@admin.register(models.FormaMedicamento)
class FormaMedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug"); prepopulated_fields = {"slug": ("nome",)}


class LoteInline(admin.TabularInline):
    model = models.Lote; extra = 0


@admin.register(models.Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "metragem", "tipo", "forma", "quantidade_total", "total_lotes")
    list_filter = ("tipo", "forma"); search_fields = ("nome", "metragem", "complemento")
    inlines = [LoteInline]


@admin.register(models.Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "medicamento", "quantidade", "validade", "situacao")
    list_filter = ("situacao",); search_fields = ("codigo", "medicamento__nome")


@admin.register(models.Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "funcao", "email")
    list_filter = ("funcao",); search_fields = ("nome", "cpf", "email")


@admin.register(models.Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("codigo_id", "modelo", "ano", "tipo", "status")
    list_filter = ("status", "tipo")


@admin.register(models.Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "lote", "quantidade", "usuario", "horario")
    list_filter = ("tipo",)


@admin.register(models.Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "funcao", "telefone")


@admin.register(models.Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ("estoque_baixo", "estoque_alto", "validade_proximo", "validade_configurada")
