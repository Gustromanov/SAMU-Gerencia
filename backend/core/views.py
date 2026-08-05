"""Views do sistema SAMU 192."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import RedirectView, TemplateView

from . import forms as core_forms
from . import models
from . import exportacao


# ---------- Auth ----------
class RootRedirectView(RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs) -> str:
        if self.request.user.is_authenticated:
            return reverse("medicamentos_lista")
        return reverse("login")


class LoginView(DjangoLoginView):
    template_name = "core/login.html"
    authentication_form = core_forms.LoginForm
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse_lazy("medicamentos_lista")


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
            models.Perfil.objects.get_or_create(user=user, defaults={"cargo": "Operador(a) SAMU"})
            login(request, user)
            messages.success(request, "Conta criada com sucesso! Bem-vindo(a) ao SAMU 192.")
            return redirect("medicamentos_lista")
        return render(request, self.template_name, {"form": form})


# ---------- Medicamentos ----------
class MedicamentosListaView(LoginRequiredMixin, TemplateView):
    template_name = "core/medicamentos/lista.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        tipo_id = self.request.GET.get("tipo") or ""
        forma_id = self.request.GET.get("forma") or ""
        nivel = self.request.GET.get("nivel") or ""

        lotes_qs = (
            models.Lote.objects.select_related("medicamento", "medicamento__tipo", "medicamento__forma")
            .all()
        )
        if q:
            lotes_qs = lotes_qs.filter(
                Q(medicamento__nome__icontains=q)
                | Q(codigo__icontains=q)
                | Q(medicamento__complemento__icontains=q)
            )
        if tipo_id:
            lotes_qs = lotes_qs.filter(medicamento__tipo_id=tipo_id)
        if forma_id:
            lotes_qs = lotes_qs.filter(medicamento__forma_id=forma_id)

        lotes = list(lotes_qs.order_by("medicamento__nome", "validade"))
        if nivel:
            lotes = [l for l in lotes if l.nivel_estoque == nivel]

        total_medicamentos = models.Medicamento.objects.count()
        total_lotes = models.Lote.objects.count()
        total_baixo = sum(1 for l in models.Lote.objects.all() if l.nivel_estoque == "BAIXO")
        total_muito_baixo = sum(1 for l in models.Lote.objects.all() if l.nivel_estoque == "MUITO_BAIXO")
        vencendo = sum(1 for l in models.Lote.objects.all() if l.proximo_vencimento or l.vencido)

        ctx.update(
            {
                "lotes": lotes,
                "q": q,
                "filtro_tipo": tipo_id,
                "filtro_forma": forma_id,
                "filtro_nivel": nivel,
                "tipos": models.TipoMedicamento.objects.all(),
                "formas": models.FormaMedicamento.objects.all(),
                "kpis": {
                    "medicamentos": total_medicamentos,
                    "lotes": total_lotes,
                    "baixo": total_baixo,
                    "muito_baixo": total_muito_baixo,
                    "vencendo": vencendo,
                },
                "form_mov": core_forms.MovimentacaoForm(),
                "pagina_ativa": "medicamentos",
            }
        )
        return ctx


class MedicamentoFormView(LoginRequiredMixin, View):
    template_name = "core/medicamentos/form.html"

    def _load(self, pk):
        return get_object_or_404(models.Medicamento, pk=pk) if pk else None

    def get(self, request, pk=None):
        medicamento = self._load(pk)
        form = core_forms.MedicamentoForm(instance=medicamento)
        lote_form = core_forms.LoteForm() if medicamento is None else None
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "lote_form": lote_form,
                "medicamento": medicamento,
                "pagina_ativa": "medicamentos",
            },
        )

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
                        tipo="ENTRADA",
                        lote=lote,
                        quantidade=lote.quantidade,
                        origem="Cadastro inicial",
                        funcionario=getattr(request.user, "funcionario", None),
                    )
            messages.success(request, "Medicamento salvo com sucesso.")
            return redirect("medicamentos_lista")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "lote_form": lote_form,
                "medicamento": medicamento,
                "pagina_ativa": "medicamentos",
            },
        )


class MedicamentoExcluirView(LoginRequiredMixin, View):
    """Deleta o medicamento OU um número específico de lotes.

    Regra: se houver apenas 1 lote associado ao medicamento, remove o medicamento
    inteiro (após confirmação pop-up). Se houver múltiplos lotes, o usuário indica
    quantos remover (removem-se os lotes mais próximos do vencimento primeiro).
    """

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


class LoteFormView(LoginRequiredMixin, View):
    template_name = "core/medicamentos/lote_form.html"

    def get(self, request, pk):
        # Se veio via /medicamentos/<pk>/lotes/novo/, pk é o medicamento.
        # Se via /lotes/<pk>/editar/, pk é o lote.
        if "novo" in request.path:
            medicamento = get_object_or_404(models.Medicamento, pk=pk)
            form = core_forms.LoteForm()
            lote = None
        else:
            lote = get_object_or_404(models.Lote, pk=pk)
            medicamento = lote.medicamento
            form = core_forms.LoteForm(instance=lote)
        return render(
            request,
            self.template_name,
            {"form": form, "medicamento": medicamento, "lote": lote, "pagina_ativa": "medicamentos"},
        )

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
        return render(
            request,
            self.template_name,
            {"form": form, "medicamento": medicamento, "lote": lote, "pagina_ativa": "medicamentos"},
        )


class LoteExcluirView(LoginRequiredMixin, View):
    def post(self, request, pk):
        lote = get_object_or_404(models.Lote, pk=pk)
        medicamento = lote.medicamento
        lote.delete()
        if medicamento.lotes.count() == 0:
            medicamento.delete()
            messages.success(request, "Lote removido. Medicamento não possui mais lotes: também foi removido.")
        else:
            messages.success(request, "Lote removido do estoque.")
        return redirect("medicamentos_lista")


class MovimentarView(LoginRequiredMixin, View):
    """Registra entrada/saída de estoque a partir do modal."""

    def post(self, request):
        form = core_forms.MovimentacaoForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Verifique os dados da movimentação.")
            return redirect("medicamentos_lista")

        data = form.cleaned_data
        query = data["medicamento_query"].strip()
        tipo = data["tipo_movimentacao"]
        qtd = int(data["quantidade"] or 1)
        tipo_med = data.get("tipo_medicamento")
        forma_med = data.get("forma_medicamento")
        origem = data.get("origem", "")

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
            messages.error(
                request,
                "Nenhum medicamento encontrado com o critério informado. Cadastre-o antes de registrar movimentação.",
            )
            return redirect("medicamentos_lista")
        if len(candidatos) > 1:
            nomes = ", ".join(f"{m.nome} ({m.tipo.nome}/{m.forma.nome})" for m in candidatos[:3])
            messages.error(
                request,
                f"Vários medicamentos correspondem à busca ({nomes}...). Especifique tipo e forma para desambiguar.",
            )
            return redirect("medicamentos_lista")

        medicamento = candidatos[0]

        if tipo == "ENTRADA":
            # Adiciona ao lote mais recente; se não houver lote, cria um "AVULSO".
            lote = medicamento.lotes.order_by("-criado_em").first()
            if lote is None:
                lote = models.Lote.objects.create(
                    medicamento=medicamento,
                    codigo="AVULSO-1",
                    validade=timezone.now().date() + timedelta(days=365),
                    quantidade=0,
                    situacao="RECEBIDO",
                )
            lote.quantidade += qtd
            lote.save(update_fields=["quantidade", "atualizado_em"])
            models.Movimentacao.objects.create(
                tipo="ENTRADA",
                lote=lote,
                quantidade=qtd,
                origem=origem,
                funcionario=getattr(request.user, "funcionario", None),
            )
            messages.success(request, f"Entrada de {qtd}× {medicamento.nome} registrada no lote {lote.codigo}.")
            return redirect("medicamentos_lista")

        # SAÍDA — FEFO (first expire first out) e nunca deixa estoque negativo.
        lotes = list(medicamento.lotes.order_by("validade"))
        disponivel = sum(l.quantidade for l in lotes)
        if disponivel < qtd:
            messages.error(
                request,
                f"Estoque insuficiente: há {disponivel} unidade(s) de {medicamento.nome}, mas a saída pede {qtd}.",
            )
            return redirect("medicamentos_lista")

        restante = qtd
        for lote in lotes:
            if restante <= 0:
                break
            usar = min(restante, lote.quantidade)
            if usar <= 0:
                continue
            lote.quantidade -= usar
            lote.save(update_fields=["quantidade", "atualizado_em"])
            models.Movimentacao.objects.create(
                tipo="SAIDA",
                lote=lote,
                quantidade=usar,
                destino=origem,
                funcionario=getattr(request.user, "funcionario", None),
            )
            restante -= usar

        messages.success(request, f"Saída de {qtd}× {medicamento.nome} registrada com sucesso.")
        return redirect("medicamentos_lista")


# ---------- Funcionários ----------
class FuncionariosListaView(LoginRequiredMixin, TemplateView):
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
        ctx.update(
            {
                "funcionarios": qs,
                "q": q,
                "filtro_funcao": funcao,
                "funcoes": models.Funcionario.FUNCAO_CHOICES,
                "pagina_ativa": "funcionarios",
            }
        )
        return ctx


class FuncionarioFormView(LoginRequiredMixin, View):
    template_name = "core/funcionarios/form.html"

    def get(self, request, pk=None):
        instancia = get_object_or_404(models.Funcionario, pk=pk) if pk else None
        movimentacoes = (
            instancia.movimentacoes.select_related("lote", "lote__medicamento")[:20] if instancia else []
        )
        return render(
            request,
            self.template_name,
            {
                "form": core_forms.FuncionarioForm(instance=instancia),
                "funcionario": instancia,
                "movimentacoes": movimentacoes,
                "pagina_ativa": "funcionarios",
            },
        )

    def post(self, request, pk=None):
        instancia = get_object_or_404(models.Funcionario, pk=pk) if pk else None
        form = core_forms.FuncionarioForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Funcionário salvo com sucesso.")
            return redirect("funcionarios_lista")
        movimentacoes = (
            instancia.movimentacoes.select_related("lote", "lote__medicamento")[:20] if instancia else []
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "funcionario": instancia,
                "movimentacoes": movimentacoes,
                "pagina_ativa": "funcionarios",
            },
        )


class FuncionarioExcluirView(LoginRequiredMixin, View):
    def post(self, request, pk):
        funcionario = get_object_or_404(models.Funcionario, pk=pk)
        funcionario.delete()
        messages.success(request, "Funcionário removido.")
        return redirect("funcionarios_lista")


# ---------- Veículos ----------
class VeiculosListaView(LoginRequiredMixin, TemplateView):
    template_name = "core/veiculos/lista.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status") or ""
        qs = models.Veiculo.objects.all()
        if q:
            qs = qs.filter(Q(codigo_id__icontains=q) | Q(modelo__icontains=q))
        if status:
            qs = qs.filter(status=status)
        ctx.update(
            {
                "veiculos": qs,
                "q": q,
                "filtro_status": status,
                "status_choices": models.Veiculo.STATUS_CHOICES,
                "pagina_ativa": "veiculos",
            }
        )
        return ctx


class VeiculoFormView(LoginRequiredMixin, View):
    template_name = "core/veiculos/form.html"

    def get(self, request, pk=None):
        instancia = get_object_or_404(models.Veiculo, pk=pk) if pk else None
        return render(
            request,
            self.template_name,
            {
                "form": core_forms.VeiculoForm(instance=instancia),
                "veiculo": instancia,
                "pagina_ativa": "veiculos",
            },
        )

    def post(self, request, pk=None):
        instancia = get_object_or_404(models.Veiculo, pk=pk) if pk else None
        form = core_forms.VeiculoForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Veículo salvo com sucesso.")
            return redirect("veiculos_lista")
        return render(
            request,
            self.template_name,
            {"form": form, "veiculo": instancia, "pagina_ativa": "veiculos"},
        )


class VeiculoExcluirView(LoginRequiredMixin, View):
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
        lotes = list(models.Lote.objects.select_related("medicamento"))
        proximos_venc = [
            l for l in lotes if l.proximo_vencimento or l.vencido
        ]
        proximos_venc.sort(key=lambda l: l.validade)

        ctx.update(
            {
                "kpis": {
                    "medicamentos": models.Medicamento.objects.count(),
                    "lotes": models.Lote.objects.count(),
                    "funcionarios": models.Funcionario.objects.count(),
                    "veiculos": models.Veiculo.objects.count(),
                    "estoque_total": sum(l.quantidade for l in lotes),
                },
                "baixo": [l for l in lotes if l.nivel_estoque == "BAIXO"][:20],
                "muito_baixo": [l for l in lotes if l.nivel_estoque == "MUITO_BAIXO"][:20],
                "vencendo": proximos_venc[:20],
                "pagina_ativa": "relatorio",
            }
        )
        return ctx


class RelatorioJson(LoginRequiredMixin, View):
    """Fornece dados para os gráficos (Chart.js) do relatório."""

    def get(self, request):
        filtro = request.GET.get("filtro", "tipo")

        if filtro == "tipo":
            data = (
                models.Lote.objects.values("medicamento__tipo__nome")
                .annotate(total=Sum("quantidade"))
                .order_by("-total")
            )
            labels = [row["medicamento__tipo__nome"] or "—" for row in data]
            valores = [row["total"] or 0 for row in data]
        elif filtro == "forma":
            data = (
                models.Lote.objects.values("medicamento__forma__nome")
                .annotate(total=Sum("quantidade"))
                .order_by("-total")
            )
            labels = [row["medicamento__forma__nome"] or "—" for row in data]
            valores = [row["total"] or 0 for row in data]
        elif filtro == "validade":
            hoje = timezone.now().date()
            faixas = [
                ("Vencidos", lambda l: l.validade < hoje),
                ("Até 30 dias", lambda l: 0 <= (l.validade - hoje).days <= 30),
                ("31 a 90 dias", lambda l: 31 <= (l.validade - hoje).days <= 90),
                ("91 a 180 dias", lambda l: 91 <= (l.validade - hoje).days <= 180),
                ("Mais de 180 dias", lambda l: (l.validade - hoje).days > 180),
            ]
            lotes = list(models.Lote.objects.all())
            labels = [nome for nome, _ in faixas]
            valores = [sum(l.quantidade for l in lotes if pred(l)) for _, pred in faixas]
        else:
            labels, valores = [], []

        veiculos = (
            models.Veiculo.objects.values("status").annotate(total=Count("id"))
        )
        veiculo_dict = {v["status"]: v["total"] for v in veiculos}
        veiculo_labels = ["Normal", "Manutenção", "Inativo"]
        veiculo_valores = [
            veiculo_dict.get("NORMAL", 0),
            veiculo_dict.get("MANUTENCAO", 0),
            veiculo_dict.get("INATIVO", 0),
        ]

        return JsonResponse(
            {
                "estoque": {"labels": labels, "valores": valores, "filtro": filtro},
                "veiculos": {"labels": veiculo_labels, "valores": veiculo_valores},
            }
        )


# ---------- Perfil ----------
class PerfilView(LoginRequiredMixin, View):
    template_name = "core/perfil.html"

    def _perfil(self, user: User) -> models.Perfil:
        perfil, _ = models.Perfil.objects.get_or_create(user=user)
        return perfil

    def get(self, request):
        perfil = self._perfil(request.user)
        form = core_forms.PerfilForm(instance=perfil)
        return render(
            request,
            self.template_name,
            {"form": form, "perfil": perfil, "pagina_ativa": "perfil"},
        )

    def post(self, request):
        perfil = self._perfil(request.user)
        form = core_forms.PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado.")
            return redirect("perfil")
        return render(
            request,
            self.template_name,
            {"form": form, "perfil": perfil, "pagina_ativa": "perfil"},
        )


# ---------- APIs JSON (autocomplete) ----------
class BuscaMedicamentosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Medicamento.objects.select_related("tipo", "forma")
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(complemento__icontains=q))
        qs = qs[:15]
        resultado = [
            {
                "id": m.id,
                "nome": m.nome,
                "tipo": m.tipo.nome,
                "forma": m.forma.nome,
                "complemento": m.complemento,
                "quantidade_total": m.quantidade_total,
            }
            for m in qs
        ]
        return JsonResponse({"resultados": resultado})


class BuscaFuncionariosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Funcionario.objects.all()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(email__icontains=q))
        return JsonResponse(
            {
                "resultados": [
                    {"id": f.id, "nome": f.nome, "cpf": f.cpf, "funcao": f.get_funcao_display()}
                    for f in qs[:15]
                ]
            }
        )


class BuscaVeiculosJson(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = models.Veiculo.objects.all()
        if q:
            qs = qs.filter(Q(codigo_id__icontains=q) | Q(modelo__icontains=q))
        return JsonResponse(
            {
                "resultados": [
                    {"id": v.id, "codigo": v.codigo_id, "modelo": v.modelo, "status": v.get_status_display()}
                    for v in qs[:15]
                ]
            }
        )


class HealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


# ---------- Exportação (PDF / XLSX) ----------
class RelatorioExportarPdf(LoginRequiredMixin, View):
    def get(self, request):
        conteudo = exportacao.gerar_pdf()
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        resp = HttpResponse(conteudo, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="samu192-relatorio-{stamp}.pdf"'
        return resp


class RelatorioExportarXlsx(LoginRequiredMixin, View):
    def get(self, request):
        conteudo = exportacao.gerar_xlsx()
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        resp = HttpResponse(
            conteudo,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="samu192-relatorio-{stamp}.xlsx"'
        return resp
