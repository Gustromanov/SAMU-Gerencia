"""Views do sistema SAMU 192."""
from __future__ import annotations

import os
import shutil
import socket
import tempfile
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db import connection, transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import RedirectView, TemplateView

from . import exportacao
from . import forms as core_forms
from . import models
from .permissions import RoleRequiredMixin, perfil_do


DIAS_SEMANA_PT = [
    "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
    "Sexta-feira", "Sábado", "Domingo",
]


def _destino_apos_login(user) -> str:
    """Rota inicial baseada na função do usuário."""
    perfil = perfil_do(user)
    if not perfil:
        return reverse("medicamentos_lista")
    return reverse(perfil.home_url_name)


# ---------- Auth ----------
class RootRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs) -> str:
        if self.request.user.is_authenticated:
            return _destino_apos_login(self.request.user)
        return reverse("login")


class LoginView(DjangoLoginView):
    template_name = "core/login.html"
    authentication_form = core_forms.LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = form.cleaned_data.get("remember_me", True)
        if remember:
            self.request.session.set_expiry(60 * 60 * 24 * 30)  # 30 dias
        else:
            self.request.session.set_expiry(0)  # até fechar o navegador
        # Garante que exista um Perfil para este usuário.
        models.Perfil.objects.get_or_create(
            user=self.request.user,
            defaults={"funcao": "ADMINISTRADOR" if self.request.user.is_superuser else "AUXILIAR"},
        )
        return response

    def get_success_url(self) -> str:
        return _destino_apos_login(self.request.user)


class LogoutView(View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        logout(request)
        return redirect("login")


class RegistrarView(View):
    template_name = "core/registrar.html"

    def get(self, request):
        return render(request, self.template_name, {"form": core_forms.RegistroForm()})

    def post(self, request):
        form = core_forms.RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if form.cleaned_data.get("remember_me", True):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao SAMU 192.")
            return redirect(_destino_apos_login(user))
        return render(request, self.template_name, {"form": form})


# ---------- Medicamentos (agrupado por nome) ----------
class MedicamentosListaView(RoleRequiredMixin, TemplateView):
    allowed_roles = ("ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO")
    template_name = "core/medicamentos/lista.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        tipos_sel = self.request.GET.getlist("tipo")
        formas_sel = self.request.GET.getlist("forma")
        niveis_sel = self.request.GET.getlist("nivel")
        validades_sel = self.request.GET.getlist("validade")
        lotes_sel = self.request.GET.getlist("lote")

        # Buscamos primeiro Medicamentos (identidades) e agrupamos por nome.
        meds_qs = models.Medicamento.objects.select_related("tipo", "forma").prefetch_related("lotes")
        if q:
            meds_qs = meds_qs.filter(
                Q(nome__icontains=q) | Q(metragem__icontains=q) | Q(complemento__icontains=q)
                | Q(lotes__codigo__icontains=q)
            ).distinct()
        if tipos_sel:
            meds_qs = meds_qs.filter(tipo_id__in=tipos_sel)
        if formas_sel:
            meds_qs = meds_qs.filter(forma_id__in=formas_sel)

        medicamentos = list(meds_qs)

        # Filtros de nível/validade/lote operam nos lotes.
        def medicamento_passa(med):
            lotes = list(med.lotes.all())
            if lotes_sel:
                lotes = [l for l in lotes if str(l.id) in lotes_sel]
                if not lotes:
                    return False
            if niveis_sel:
                lotes_f = [l for l in lotes if l.nivel_estoque in niveis_sel]
                if not lotes_f:
                    return False
                lotes = lotes_f
            if validades_sel:
                lotes_f = [l for l in lotes if l.nivel_validade in validades_sel]
                if not lotes_f:
                    return False
                lotes = lotes_f
            med.lotes_filtrados = sorted(lotes, key=lambda l: l.validade)
            return True

        medicamentos = [m for m in medicamentos if medicamento_passa(m)]

        # Agrupa por nome (base, sem metragem) para a setinha expansível.
        grupos: dict[str, list[models.Medicamento]] = defaultdict(list)
        for m in medicamentos:
            if not hasattr(m, "lotes_filtrados"):
                m.lotes_filtrados = sorted(m.lotes.all(), key=lambda l: l.validade)
            grupos[m.nome].append(m)

        # Monta lista: cada "cabeça" é o primeiro medicamento daquele nome.
        linhas = []
        for nome, lista in sorted(grupos.items(), key=lambda x: x[0]):
            principal = lista[0]
            variantes = lista[1:]  # exibidas dentro da setinha
            linhas.append({"principal": principal, "variantes": variantes, "total_variantes": len(variantes)})

        # KPIs
        todos_lotes = list(models.Lote.objects.select_related("medicamento").all())
        total_medicamentos = models.Medicamento.objects.count()
        total_lotes = len(todos_lotes)
        total_baixo = sum(1 for l in todos_lotes if l.nivel_estoque == "BAIXO")
        total_muito_baixo = sum(1 for l in todos_lotes if l.nivel_estoque == "MUITO_BAIXO")
        vencendo = sum(1 for l in todos_lotes if l.nivel_validade in {"VENCIDO", "MUITO_PROXIMO"})

        perfil = perfil_do(self.request.user)

        ctx.update(
            {
                "linhas": linhas,
                "q": q,
                "filtro_tipos": tipos_sel,
                "filtro_formas": formas_sel,
                "filtro_niveis": niveis_sel,
                "filtro_validades": validades_sel,
                "filtro_lotes": lotes_sel,
                "tipos": models.TipoMedicamento.objects.all(),
                "formas": models.FormaMedicamento.objects.all(),
                "todos_lotes_opts": models.Lote.objects.select_related("medicamento").order_by("codigo"),
                "kpis": {
                    "medicamentos": total_medicamentos,
                    "lotes": total_lotes,
                    "baixo": total_baixo,
                    "muito_baixo": total_muito_baixo,
                    "vencendo": vencendo,
                },
                "form_mov": core_forms.MovimentacaoForm(),
                "pagina_ativa": "medicamentos",
                "pode_deletar": perfil.pode_deletar_medicamentos if perfil else False,
                "pode_editar": perfil.pode_editar_medicamentos if perfil else False,
                "pode_mostrar_setinha": True,
            }
        )
        return ctx


class MedicamentoFormView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO")
    template_name = "core/medicamentos/form.html"

    def _load(self, pk):
        return get_object_or_404(models.Medicamento, pk=pk) if pk else None

    def get(self, request, pk=None):
        medicamento = self._load(pk)
        form = core_forms.MedicamentoForm(instance=medicamento)
        lote_form = core_forms.LoteForm() if medicamento is None else None
        return render(request, self.template_name, {
            "form": form, "lote_form": lote_form, "medicamento": medicamento, "pagina_ativa": "medicamentos",
        })

    def post(self, request, pk=None):
        medicamento = self._load(pk)
        form = core_forms.MedicamentoForm(request.POST, instance=medicamento)
        criar_lote = medicamento is None
        lote_form = core_forms.LoteForm(request.POST) if criar_lote else None

        if form.is_valid() and (not criar_lote or lote_form.is_valid()):
            medicamento = form.save()
            if criar_lote:
                lote = lote_form.save(commit=False)
                lote.medicamento = medicamento
                lote.save()
                if lote.quantidade > 0:
                    models.Movimentacao.objects.create(
                        tipo="ENTRADA", lote=lote, quantidade=lote.quantidade,
                        origem="Cadastro inicial",
                        funcionario=getattr(request.user, "funcionario", None),
                        usuario=request.user,
                    )
            messages.success(request, "Medicamento salvo com sucesso.")
            return redirect("medicamentos_lista")
        return render(request, self.template_name, {
            "form": form, "lote_form": lote_form, "medicamento": medicamento, "pagina_ativa": "medicamentos",
        })


class MedicamentoExcluirView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request, pk):
        medicamento = get_object_or_404(models.Medicamento, pk=pk)
        quantos = request.POST.get("quantos_lotes")
        total = medicamento.lotes.count()
        if total <= 1 or not quantos:
            medicamento.delete()
            messages.success(request, "Medicamento removido do estoque.")
            return redirect("medicamentos_lista")
        try:
            n = max(1, min(int(quantos), total))
        except (TypeError, ValueError):
            messages.error(request, "Quantidade de lotes inválida.")
            return redirect("medicamentos_lista")
        lotes = list(medicamento.lotes.order_by("validade")[:n])
        for lote in lotes:
            lote.delete()
        restante = medicamento.lotes.count()
        if restante == 0:
            medicamento.delete()
            messages.success(request, f"{n} lote(s) removido(s). Medicamento sem lotes: removido do estoque.")
        else:
            messages.success(request, f"{n} lote(s) removido(s). Restam {restante} lote(s).")
        return redirect("medicamentos_lista")


class LoteFormView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO")
    template_name = "core/medicamentos/lote_form.html"

    def get(self, request, pk):
        if "novo" in request.path:
            medicamento = get_object_or_404(models.Medicamento, pk=pk)
            form = core_forms.LoteForm()
            lote = None
        else:
            lote = get_object_or_404(models.Lote, pk=pk)
            medicamento = lote.medicamento
            form = core_forms.LoteForm(instance=lote)
        return render(request, self.template_name, {
            "form": form, "medicamento": medicamento, "lote": lote, "pagina_ativa": "medicamentos",
        })

    def post(self, request, pk):
        if "novo" in request.path:
            medicamento = get_object_or_404(models.Medicamento, pk=pk)
            form = core_forms.LoteForm(request.POST)
            lote = None
        else:
            lote = get_object_or_404(models.Lote, pk=pk)
            medicamento = lote.medicamento
            form = core_forms.LoteForm(request.POST, instance=lote)
        if form.is_valid():
            novo = form.save(commit=False)
            novo.medicamento = medicamento
            novo.save()
            messages.success(request, "Lote salvo com sucesso.")
            return redirect("medicamentos_lista")
        return render(request, self.template_name, {
            "form": form, "medicamento": medicamento, "lote": lote, "pagina_ativa": "medicamentos",
        })


class LoteExcluirView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request, pk):
        lote = get_object_or_404(models.Lote, pk=pk)
        medicamento = lote.medicamento
        lote.delete()
        if medicamento.lotes.count() == 0:
            medicamento.delete()
            messages.success(request, "Lote removido. Medicamento também foi removido (sem lotes).")
        else:
            messages.success(request, "Lote removido do estoque.")
        return redirect("medicamentos_lista")


class MovimentarView(RoleRequiredMixin, View):
    """ENTRADA/SAÍDA com validações rigorosas."""

    allowed_roles = ("ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO")

    def post(self, request):
        form = core_forms.MovimentacaoForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Verifique os dados da movimentação: " + "; ".join(
                [f"{k}: {', '.join(v)}" for k, v in form.errors.items()]
            ))
            return redirect("medicamentos_lista")

        data = form.cleaned_data
        query = data["medicamento_query"].strip()
        tipo = data["tipo_movimentacao"]
        qtd = int(data["quantidade"])
        tipo_med = data.get("tipo_medicamento")
        forma_med = data.get("forma_medicamento")
        origem_destino = data.get("origem_destino", "")
        lote_codigo = data["lote_codigo"].strip()

        # Localiza o medicamento
        med_qs = models.Medicamento.objects.select_related("tipo", "forma")
        if query.isdigit():
            med_qs = med_qs.filter(Q(id=int(query)) | Q(nome__icontains=query))
        else:
            med_qs = med_qs.filter(nome__icontains=query)
        if tipo_med:
            med_qs = med_qs.filter(tipo=tipo_med)
        if forma_med:
            med_qs = med_qs.filter(forma=forma_med)

        candidatos = list(med_qs)
        if not candidatos:
            messages.error(request, "Medicamento não encontrado. Cadastre-o antes de registrar movimentação.")
            return redirect("medicamentos_lista")

        if (tipo_med is None or forma_med is None) and len(candidatos) > 1:
            # Pega o último cadastrado quando usuário não desambiguou.
            candidatos.sort(key=lambda m: m.criado_em, reverse=True)

        medicamento = candidatos[0]

        # Localiza o lote
        lote = medicamento.lotes.filter(codigo__iexact=lote_codigo).first()
        if not lote:
            if medicamento.lotes.exists() and tipo_med is None and forma_med is None:
                # usuário informou código de lote inexistente → erro claro
                messages.error(
                    request,
                    f"O lote '{lote_codigo}' não está cadastrado para {medicamento.nome_exibicao}. "
                    "Cadastre o lote antes de registrar a movimentação.",
                )
                return redirect("medicamentos_lista")
            # Se nunca houve nenhum lote, cria.
            if not medicamento.lotes.exists():
                lote = models.Lote.objects.create(
                    medicamento=medicamento, codigo=lote_codigo or "AVULSO-1",
                    validade=timezone.now().date() + timedelta(days=365),
                    quantidade=0, situacao="RECEBIDO",
                )
            else:
                messages.error(
                    request,
                    f"O lote '{lote_codigo}' não está cadastrado para {medicamento.nome_exibicao}.",
                )
                return redirect("medicamentos_lista")

        funcionario = getattr(request.user, "funcionario", None)
        if tipo == "ENTRADA":
            lote.quantidade += qtd
            lote.save(update_fields=["quantidade", "atualizado_em"])
            models.Movimentacao.objects.create(
                tipo="ENTRADA", lote=lote, quantidade=qtd, origem=origem_destino,
                funcionario=funcionario, usuario=request.user,
            )
            messages.success(request, f"Entrada de {qtd}× {medicamento.nome_exibicao} registrada no lote {lote.codigo}.")
            return redirect("medicamentos_lista")

        # SAÍDA
        if lote.quantidade < qtd:
            messages.error(
                request,
                f"Estoque insuficiente no lote {lote.codigo}: há {lote.quantidade} unidade(s), mas a saída pede {qtd}.",
            )
            return redirect("medicamentos_lista")
        lote.quantidade -= qtd
        lote.save(update_fields=["quantidade", "atualizado_em"])
        models.Movimentacao.objects.create(
            tipo="SAIDA", lote=lote, quantidade=qtd, destino=origem_destino,
            funcionario=funcionario, usuario=request.user,
        )
        messages.success(request, f"Saída de {qtd}× {medicamento.nome_exibicao} registrada no lote {lote.codigo}.")
        return redirect("medicamentos_lista")


# ---------- Funcionários ----------
class FuncionariosListaView(RoleRequiredMixin, TemplateView):
    allowed_roles = ("ADMINISTRADOR",)
    template_name = "core/funcionarios/lista.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        funcao = self.request.GET.get("funcao") or ""
        qs = models.Funcionario.objects.all()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(email__icontains=q))
        if funcao:
            qs = qs.filter(funcao=funcao)
        ctx.update({"funcionarios": qs, "q": q, "filtro_funcao": funcao,
                    "funcoes": models.Funcionario.FUNCAO_CHOICES, "pagina_ativa": "funcionarios"})
        return ctx


class FuncionarioFormView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)
    template_name = "core/funcionarios/form.html"

    def get(self, request, pk=None):
        instancia = get_object_or_404(models.Funcionario, pk=pk) if pk else None
        return render(request, self.template_name, {"form": core_forms.FuncionarioForm(instance=instancia),
                                                      "funcionario": instancia, "pagina_ativa": "funcionarios"})

    def post(self, request, pk=None):
        instancia = get_object_or_404(models.Funcionario, pk=pk) if pk else None
        form = core_forms.FuncionarioForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionário salvo com sucesso.")
            return redirect("funcionarios_lista")
        return render(request, self.template_name, {"form": form, "funcionario": instancia, "pagina_ativa": "funcionarios"})


class FuncionarioExcluirView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request, pk):
        funcionario = get_object_or_404(models.Funcionario, pk=pk)
        funcionario.delete()
        messages.success(request, "Funcionário removido.")
        return redirect("funcionarios_lista")


# ---------- Veículos ----------
class VeiculosListaView(RoleRequiredMixin, TemplateView):
    allowed_roles = ("ADMINISTRADOR", "MOTORISTA")
    template_name = "core/veiculos/lista.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status") or ""
        tipo = self.request.GET.get("tipo") or ""
        qs = models.Veiculo.objects.all()
        if q:
            qs = qs.filter(Q(codigo_id__icontains=q) | Q(modelo__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if tipo:
            qs = qs.filter(tipo=tipo)
        perfil = perfil_do(self.request.user)
        ctx.update({
            "veiculos": qs, "q": q, "filtro_status": status, "filtro_tipo": tipo,
            "status_choices": models.Veiculo.STATUS_CHOICES,
            "tipo_choices": models.Veiculo.TIPO_CHOICES,
            "pagina_ativa": "veiculos",
            "pode_deletar": perfil.pode_deletar_veiculos if perfil else False,
        })
        return ctx


class VeiculoFormView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR", "MOTORISTA")
    template_name = "core/veiculos/form.html"

    def get(self, request, pk=None):
        instancia = get_object_or_404(models.Veiculo, pk=pk) if pk else None
        return render(request, self.template_name, {"form": core_forms.VeiculoForm(instance=instancia),
                                                      "veiculo": instancia, "pagina_ativa": "veiculos"})

    def post(self, request, pk=None):
        instancia = get_object_or_404(models.Veiculo, pk=pk) if pk else None
        form = core_forms.VeiculoForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo salvo com sucesso.")
            return redirect("veiculos_lista")
        return render(request, self.template_name, {"form": form, "veiculo": instancia, "pagina_ativa": "veiculos"})


class VeiculoExcluirView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request, pk):
        veiculo = get_object_or_404(models.Veiculo, pk=pk)
        veiculo.delete()
        messages.success(request, "Veículo removido.")
        return redirect("veiculos_lista")


# ---------- Relatório ----------
class RelatorioView(LoginRequiredMixin, TemplateView):
    template_name = "core/relatorio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cfg = models.Configuracao.obter()
        perfil = perfil_do(self.request.user)
        lotes = list(models.Lote.objects.select_related("medicamento").all())

        baixo = sorted([l for l in lotes if l.nivel_estoque == "BAIXO"], key=lambda l: l.quantidade)
        muito_baixo = sorted([l for l in lotes if l.nivel_estoque == "MUITO_BAIXO"], key=lambda l: l.quantidade)
        vencendo = sorted(
            [l for l in lotes if l.nivel_validade in {"VENCIDO", "MUITO_PROXIMO"}],
            key=lambda l: l.dias_para_validade,
        )
        controlados = sorted(
            [l for l in lotes if l.nivel_validade == "CONTROLADO"], key=lambda l: l.dias_para_validade
        )

        # Interseção: lotes com 2+ dessas características
        def grupos(l):
            s = set()
            if l.nivel_estoque in {"BAIXO", "MUITO_BAIXO"}:
                s.add("estoque")
            if l.nivel_validade in {"VENCIDO", "MUITO_PROXIMO"}:
                s.add("vencendo")
            if l.nivel_validade == "CONTROLADO":
                s.add("controlado")
            return s

        criticos = [l for l in lotes if len(grupos(l)) >= 2]
        criticos.sort(key=lambda l: (-len(grupos(l)), l.dias_para_validade))

        ctx.update({
            "kpis": {
                "medicamentos": models.Medicamento.objects.count(),
                "lotes": len(lotes),
                "funcionarios": models.Funcionario.objects.count(),
                "veiculos": models.Veiculo.objects.count(),
                "estoque_total": sum(l.quantidade for l in lotes),
            },
            "baixo": baixo,
            "muito_baixo": muito_baixo,
            "vencendo": vencendo,
            "controlados": controlados,
            "criticos": criticos,
            "cfg": cfg,
            "mostra_veiculos": perfil.pode_ver_veiculos if perfil else True,
            "mostra_medicamentos": perfil.pode_ver_medicamentos if perfil else True,
            "pode_exportar": perfil.pode_exportar if perfil else False,
            "pagina_ativa": "relatorio",
            "intervalo_padrao": cfg.intervalo_dias_padrao,
        })
        return ctx


class RelatorioJson(LoginRequiredMixin, View):
    """Dados para gráficos (Chart.js) do relatório, com suporte a múltiplas pesquisas."""

    def get(self, request):
        cfg = models.Configuracao.obter()
        pesquisa = request.GET.get("pesquisa", "tipo")
        intervalo = int(request.GET.get("dias", cfg.intervalo_dias_padrao) or cfg.intervalo_dias_padrao)

        labels: list[str] = []
        valores: list[int] = []

        if pesquisa == "tipo":
            d = (models.Lote.objects.values("medicamento__tipo__nome")
                 .annotate(total=Sum("quantidade")).order_by("-total"))
            labels = [r["medicamento__tipo__nome"] or "—" for r in d]
            valores = [r["total"] or 0 for r in d]
        elif pesquisa == "forma":
            d = (models.Lote.objects.values("medicamento__forma__nome")
                 .annotate(total=Sum("quantidade")).order_by("-total"))
            labels = [r["medicamento__forma__nome"] or "—" for r in d]
            valores = [r["total"] or 0 for r in d]
        elif pesquisa == "validade":
            if cfg.validade_configurada:
                faixas = ["VENCIDO", "MUITO_PROXIMO", "PROXIMO", "CONTROLADO", "DISTANTE"]
                rotulos = ["Vencido", "Muito próximo", "Próximo", "Controlado", "Distante"]
                lotes = list(models.Lote.objects.all())
                labels = rotulos
                valores = [sum(l.quantidade for l in lotes if l.nivel_validade == f) for f in faixas]
            else:
                labels, valores = [], []
        elif pesquisa == "movimentacao":
            desde = timezone.now() - timedelta(days=intervalo)
            d = (models.Movimentacao.objects.filter(horario__gte=desde)
                 .values("usuario__first_name", "usuario__username")
                 .annotate(total=Count("id")).order_by("-total")[:10])
            labels = [(r["usuario__first_name"] or r["usuario__username"] or "—") for r in d]
            valores = [r["total"] for r in d]
        elif pesquisa == "lotes":
            d = (models.Lote.objects.values("codigo")
                 .annotate(total=Sum("quantidade")).order_by("-total")[:20])
            labels = [r["codigo"] for r in d]
            valores = [r["total"] or 0 for r in d]
        elif pesquisa == "situacao":
            labels = ["Recebidos", "Entregues", "Doados"]
            d = models.Lote.objects.values("situacao").annotate(total=Sum("quantidade"))
            mapa = {r["situacao"]: r["total"] or 0 for r in d}
            valores = [mapa.get("RECEBIDO", 0), mapa.get("LOTEADO", 0), mapa.get("DOADO", 0)]
        elif pesquisa == "veic_status":
            labels = ["Normal", "Em manutenção", "Inativo"]
            d = models.Veiculo.objects.values("status").annotate(total=Count("id"))
            mapa = {r["status"]: r["total"] for r in d}
            valores = [mapa.get("NORMAL", 0), mapa.get("MANUTENCAO", 0), mapa.get("INATIVO", 0)]
        elif pesquisa == "veic_tipo":
            labels = ["Van / Ambulância", "Carro", "Motolância"]
            d = models.Veiculo.objects.values("tipo").annotate(total=Count("id"))
            mapa = {r["tipo"]: r["total"] for r in d}
            valores = [mapa.get("VAN", 0), mapa.get("CARRO", 0), mapa.get("MOTO", 0)]

        total = sum(valores)
        percentuais = [round((v / total * 100), 1) if total else 0 for v in valores]
        return JsonResponse({"labels": labels, "valores": valores, "percentuais": percentuais, "total": total})


# ---------- Perfil / Painel do admin ----------
class PerfilView(LoginRequiredMixin, View):
    template_name = "core/perfil.html"

    def get(self, request):
        perfil, _ = models.Perfil.objects.get_or_create(user=request.user)
        form = core_forms.PerfilForm(instance=perfil)
        contas = models.Perfil.objects.select_related("user") if perfil.is_admin else None
        cfg_form = core_forms.ConfiguracaoForm(instance=models.Configuracao.obter()) if perfil.is_admin else None
        ips = _detectar_ips() if perfil.is_admin else []
        return render(request, self.template_name, {
            "form": form, "perfil": perfil, "contas": contas, "cfg_form": cfg_form,
            "ips_rede": ips, "pagina_ativa": "perfil",
        })

    def post(self, request):
        perfil, _ = models.Perfil.objects.get_or_create(user=request.user)
        form = core_forms.PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado.")
            return redirect("perfil")
        contas = models.Perfil.objects.select_related("user") if perfil.is_admin else None
        cfg_form = core_forms.ConfiguracaoForm(instance=models.Configuracao.obter()) if perfil.is_admin else None
        ips = _detectar_ips() if perfil.is_admin else []
        return render(request, self.template_name, {
            "form": form, "perfil": perfil, "contas": contas, "cfg_form": cfg_form,
            "ips_rede": ips, "pagina_ativa": "perfil",
        })


class EditarContaView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)
    template_name = "core/conta_form.html"

    def get(self, request, pk):
        perfil = get_object_or_404(models.Perfil, pk=pk)
        return render(request, self.template_name, {"form": core_forms.EditarContaForm(instance=perfil),
                                                     "conta": perfil, "pagina_ativa": "perfil"})

    def post(self, request, pk):
        perfil = get_object_or_404(models.Perfil, pk=pk)
        form = core_forms.EditarContaForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Conta atualizada.")
            return redirect("perfil")
        return render(request, self.template_name, {"form": form, "conta": perfil, "pagina_ativa": "perfil"})


class ExcluirContaView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request, pk):
        perfil = get_object_or_404(models.Perfil, pk=pk)
        if perfil.user_id == request.user.id:
            messages.error(request, "Você não pode excluir a si mesmo. Peça para outro admin.")
            return redirect("perfil")
        perfil.user.delete()
        messages.success(request, "Conta excluída.")
        return redirect("perfil")


class ConfiguracaoView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request):
        cfg = models.Configuracao.obter()
        form = core_forms.ConfiguracaoForm(request.POST, instance=cfg)
        if form.is_valid():
            form.save()
            messages.success(request, "Definições salvas. Intervalos de estoque/validade atualizados.")
        else:
            messages.error(request, "Erro ao salvar definições: " + "; ".join(
                [f"{k}: {', '.join(v)}" for k, v in form.errors.items()]))
        return redirect("perfil")


# ---------- Backup / Restaurar / Apagar BD ----------
def _db_path() -> Path:
    return Path(settings.DATABASES["default"]["NAME"])


class BackupDBView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def get(self, request):
        caminho = _db_path()
        if not caminho.exists():
            messages.error(request, "Arquivo de banco não encontrado.")
            return redirect("perfil")
        connection.close()
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        resp = FileResponse(open(caminho, "rb"), as_attachment=True,
                            filename=f"samu192-backup-{stamp}.sqlite3")
        return resp


class RestaurarDBView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request):
        arquivo = request.FILES.get("backup")
        if not arquivo:
            messages.error(request, "Nenhum arquivo enviado.")
            return redirect("perfil")
        # Grava em arquivo temporário e sobrescreve o DB atual.
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3")
        for chunk in arquivo.chunks():
            tmp.write(chunk)
        tmp.close()
        destino = _db_path()
        connection.close()
        shutil.copy2(tmp.name, destino)
        os.unlink(tmp.name)
        messages.success(request, "Banco de dados restaurado com sucesso. Reautentique-se.")
        return redirect("logout")


class ApagarDBView(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def post(self, request):
        confirmacao = request.POST.get("confirmacao", "")
        if confirmacao != "APAGAR":
            messages.error(request, "Digite 'APAGAR' para confirmar a exclusão total do banco.")
            return redirect("perfil")
        with transaction.atomic():
            models.Movimentacao.objects.all().delete()
            models.Lote.objects.all().delete()
            models.Medicamento.objects.all().delete()
            models.Funcionario.objects.all().delete()
            models.Veiculo.objects.all().delete()
        messages.success(request, "Todos os dados operacionais foram apagados. Usuários e configurações preservados.")
        return redirect("perfil")


# ---------- APIs JSON ----------
class BuscaMedicamentosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Medicamento.objects.select_related("tipo", "forma")
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(metragem__icontains=q) | Q(complemento__icontains=q))
        qs = qs[:15]
        return JsonResponse({"resultados": [{
            "id": m.id, "nome": m.nome, "nome_exibicao": m.nome_exibicao, "metragem": m.metragem,
            "tipo": m.tipo.nome, "tipo_id": m.tipo_id, "forma": m.forma.nome, "forma_id": m.forma_id,
            "complemento": m.complemento, "quantidade_total": m.quantidade_total,
        } for m in qs]})


class BuscaLotesJson(LoginRequiredMixin, View):
    """Autocomplete de lotes, opcionalmente filtrado por nome do medicamento."""

    def get(self, request):
        q = request.GET.get("q", "").strip()
        medicamento_nome = request.GET.get("medicamento", "").strip()
        qs = models.Lote.objects.select_related("medicamento")
        if medicamento_nome:
            qs = qs.filter(medicamento__nome__icontains=medicamento_nome)
        if q:
            qs = qs.filter(codigo__icontains=q)
        qs = qs[:15]
        return JsonResponse({"resultados": [{
            "id": l.id, "codigo": l.codigo, "quantidade": l.quantidade,
            "validade": l.validade.strftime("%d/%m/%Y"),
            "medicamento": l.medicamento.nome_exibicao,
        } for l in qs]})


class BuscaFuncionariosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Funcionario.objects.all()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(email__icontains=q))
        return JsonResponse({"resultados": [{
            "id": f.id, "nome": f.nome, "cpf": f.cpf, "funcao": f.get_funcao_display(),
        } for f in qs[:15]]})


class HistoricoFuncionarioJson(LoginRequiredMixin, View):
    def get(self, request, pk):
        funcionario = get_object_or_404(models.Funcionario, pk=pk)
        movimentacoes = (funcionario.movimentacoes
                         .select_related("lote", "lote__medicamento").order_by("-horario"))
        primeiro = funcionario.nome.split()[0] if funcionario.nome else "Funcionário"
        pronome = "Dr(a)." if funcionario.funcao in {"MEDICO"} else ""
        registros = []
        for m in movimentacoes:
            local_dt = timezone.localtime(m.horario)
            dia = DIAS_SEMANA_PT[local_dt.weekday()]
            acao = "a entrada" if m.tipo == "ENTRADA" else "a saída"
            prefix = f"{pronome} {primeiro}".strip()
            descricao = (
                f"{prefix} realizou {acao} de {m.lote.medicamento.nome_exibicao} "
                f"em {m.quantidade} unidade{'s' if m.quantidade != 1 else ''} "
                f"— {dia}, {local_dt.strftime('%d/%m/%Y')} às {local_dt.strftime('%H:%M')}."
            )
            registros.append({
                "id": m.id, "tipo": m.tipo, "descricao": descricao,
                "lote_codigo": m.lote.codigo, "quantidade": m.quantidade,
                "horario_pt": f"{dia}, {local_dt.strftime('%d/%m/%Y às %H:%M')}",
            })
        return JsonResponse({
            "funcionario": {"id": funcionario.id, "nome": funcionario.nome, "total": len(registros)},
            "registros": registros,
        })


class BuscaVeiculosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Veiculo.objects.all()
        if q:
            qs = qs.filter(Q(codigo_id__icontains=q) | Q(modelo__icontains=q))
        return JsonResponse({"resultados": [{
            "id": v.id, "codigo": v.codigo_id, "modelo": v.modelo,
            "status": v.get_status_display(), "tipo": v.get_tipo_display(),
        } for v in qs[:15]]})


class HealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


# ---------- Exportações ----------
class RelatorioExportarPdf(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def get(self, request):
        conteudo = exportacao.gerar_pdf()
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        resp = HttpResponse(conteudo, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="samu192-relatorio-{stamp}.pdf"'
        return resp


class RelatorioExportarXlsx(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def get(self, request):
        conteudo = exportacao.gerar_xlsx()
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        resp = HttpResponse(conteudo, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="samu192-relatorio-{stamp}.xlsx"'
        return resp


# ---------- Modo Rede Local ----------
def _detectar_ips() -> list[str]:
    """Retorna IPs locais da máquina (ignora loopback)."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" not in ip and not ip.startswith("127."):
                ips.add(ip)
    except Exception:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except Exception:
        pass
    return sorted(ips) or ["127.0.0.1"]


class RedeLocalJson(RoleRequiredMixin, View):
    allowed_roles = ("ADMINISTRADOR",)

    def get(self, request):
        porta = request.GET.get("porta", "8765")
        ips = _detectar_ips()
        links = [f"http://{ip}:{porta}/" for ip in ips]
        return JsonResponse({"ips": ips, "links": links, "porta": porta})
