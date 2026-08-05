from django.contrib import admin
from . import models


@admin.register(models.TipoMedicamento)
class TipoMedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(models.FormaMedicamento)
class FormaMedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}


class LoteInline(admin.TabularInline):
    model = models.Lote
    extra = 0


@admin.register(models.Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "forma", "quantidade_total", "total_lotes")
    list_filter = ("tipo", "forma")
    search_fields = ("nome", "complemento")
    inlines = [LoteInline]


@admin.register(models.Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "medicamento", "quantidade", "validade", "situacao")
    list_filter = ("situacao", "validade")
    search_fields = ("codigo", "medicamento__nome")


@admin.register(models.Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "funcao", "email", "telefone")
    list_filter = ("funcao",)
    search_fields = ("nome", "cpf", "email")


@admin.register(models.Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("codigo_id", "modelo", "ano", "status")
    list_filter = ("status", "ano")
    search_fields = ("codigo_id", "modelo")


@admin.register(models.Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "lote", "quantidade", "funcionario", "horario")
    list_filter = ("tipo", "horario")
    search_fields = ("lote__codigo", "lote__medicamento__nome", "funcionario__nome")


@admin.register(models.Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("user", "cargo", "telefone")
