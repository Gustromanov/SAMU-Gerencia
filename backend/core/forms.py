"""Formulários Django (ModelForms) para os cadastros do SAMU 192."""
import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from . import models


CPF_REGEX = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")


def _classes(*extras: str) -> str:
    base = (
        "w-full rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-800 "
        "placeholder:text-neutral-400 focus:border-red-500 focus:outline-none focus:ring-2 "
        "focus:ring-red-100 transition"
    )
    return " ".join([base, *extras])


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário ou e-mail",
        widget=forms.TextInput(attrs={"class": _classes(), "placeholder": "seu.usuario", "autofocus": True, "data-testid": "login-username"}),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": _classes(), "placeholder": "••••••••", "data-testid": "login-password"}),
    )


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nome",
        widget=forms.TextInput(attrs={"class": _classes(), "placeholder": "Ana Silva"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": _classes(), "placeholder": "ana@samu.gov.br"}),
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": _classes(), "placeholder": "ana.silva"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update({"class": _classes(), "placeholder": "••••••••"})


class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = models.Medicamento
        fields = ("nome", "tipo", "forma", "complemento")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _classes(), "placeholder": "Ex.: Adrenalina 1mg/mL", "data-testid": "medicamento-nome"}),
            "tipo": forms.Select(attrs={"class": _classes(), "data-testid": "medicamento-tipo"}),
            "forma": forms.Select(attrs={"class": _classes(), "data-testid": "medicamento-forma"}),
            "complemento": forms.TextInput(
                attrs={"class": _classes(), "placeholder": "Ex.: Uso restrito à emergência", "data-testid": "medicamento-complemento"}
            ),
        }


class LoteForm(forms.ModelForm):
    class Meta:
        model = models.Lote
        fields = ("codigo", "validade", "quantidade", "situacao")
        widgets = {
            "codigo": forms.TextInput(attrs={"class": _classes(), "placeholder": "L2025-A1", "data-testid": "lote-codigo"}),
            "validade": forms.DateInput(
                attrs={"class": _classes(), "type": "date", "data-testid": "lote-validade"}, format="%Y-%m-%d"
            ),
            "quantidade": forms.NumberInput(attrs={"class": _classes(), "min": 0, "data-testid": "lote-quantidade"}),
            "situacao": forms.Select(attrs={"class": _classes(), "data-testid": "lote-situacao"}),
        }

    def clean_quantidade(self):
        qtd = self.cleaned_data.get("quantidade")
        if qtd is None or qtd < 0:
            raise forms.ValidationError("A quantidade não pode ser negativa.")
        return qtd


class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = models.Funcionario
        fields = ("nome", "cpf", "funcao", "email", "telefone")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _classes(), "placeholder": "Nome completo", "data-testid": "funcionario-nome"}),
            "cpf": forms.TextInput(attrs={"class": _classes(), "placeholder": "000.000.000-00", "data-testid": "funcionario-cpf"}),
            "funcao": forms.Select(attrs={"class": _classes(), "data-testid": "funcionario-funcao"}),
            "email": forms.EmailInput(attrs={"class": _classes(), "placeholder": "email@samu.gov.br", "data-testid": "funcionario-email"}),
            "telefone": forms.TextInput(attrs={"class": _classes(), "placeholder": "(00) 00000-0000", "data-testid": "funcionario-telefone"}),
        }

    def clean_cpf(self):
        cpf = (self.cleaned_data.get("cpf") or "").strip()
        if not CPF_REGEX.match(cpf):
            raise forms.ValidationError("Informe o CPF no formato 000.000.000-00.")
        return cpf


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = models.Veiculo
        fields = ("codigo_id", "modelo", "ano", "status")
        widgets = {
            "codigo_id": forms.TextInput(attrs={"class": _classes(), "placeholder": "Ex.: USB-01", "data-testid": "veiculo-codigo"}),
            "modelo": forms.TextInput(attrs={"class": _classes(), "placeholder": "Ex.: Mercedes-Benz Sprinter", "data-testid": "veiculo-modelo"}),
            "ano": forms.NumberInput(attrs={"class": _classes(), "min": 1980, "max": 2100, "data-testid": "veiculo-ano"}),
            "status": forms.Select(attrs={"class": _classes(), "data-testid": "veiculo-status"}),
        }

    def clean_ano(self):
        ano = self.cleaned_data.get("ano")
        if ano is None or ano < 1980 or ano > 2100:
            raise forms.ValidationError("Ano inválido.")
        return ano


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nome completo",
        widget=forms.TextInput(attrs={"class": _classes(), "data-testid": "perfil-nome"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": _classes(), "data-testid": "perfil-email"}),
    )

    class Meta:
        model = models.Perfil
        fields = ("telefone", "cargo", "bio")
        widgets = {
            "telefone": forms.TextInput(attrs={"class": _classes(), "placeholder": "(00) 00000-0000", "data-testid": "perfil-telefone"}),
            "cargo": forms.TextInput(attrs={"class": _classes(), "data-testid": "perfil-cargo"}),
            "bio": forms.Textarea(attrs={"class": _classes(), "rows": 3, "data-testid": "perfil-bio"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.get_full_name() or self.instance.user.first_name
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        user = perfil.user
        nome = self.cleaned_data.get("first_name", "").strip()
        user.first_name = nome
        user.last_name = ""
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            perfil.save()
        return perfil


class MovimentacaoForm(forms.Form):
    """Modal 'Registrar entrada/saída' — usa 4 campos: medicamento, quantidade, tipo, forma."""

    TIPO_MOV_CHOICES = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    tipo_movimentacao = forms.ChoiceField(choices=TIPO_MOV_CHOICES, widget=forms.HiddenInput())
    medicamento_query = forms.CharField(
        label="Medicamento (nome ou ID)",
        widget=forms.TextInput(
            attrs={
                "class": _classes(),
                "placeholder": "Digite o nome ou o ID do medicamento",
                "autocomplete": "off",
                "data-testid": "mov-medicamento",
            }
        ),
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={"class": _classes(), "placeholder": "Padrão: 1", "min": 1, "data-testid": "mov-quantidade"}
        ),
    )
    tipo_medicamento = forms.ModelChoiceField(
        queryset=models.TipoMedicamento.objects.all(),
        required=False,
        empty_label="— Todos —",
        widget=forms.Select(attrs={"class": _classes(), "data-testid": "mov-tipo"}),
    )
    forma_medicamento = forms.ModelChoiceField(
        queryset=models.FormaMedicamento.objects.all(),
        required=False,
        empty_label="— Todas —",
        widget=forms.Select(attrs={"class": _classes(), "data-testid": "mov-forma"}),
    )
    origem = forms.CharField(
        label="Origem / Destino",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": _classes(),
                "placeholder": "De onde veio ou para onde foi (opcional)",
                "data-testid": "mov-origem-destino",
            }
        ),
    )

    def clean_quantidade(self):
        qtd = self.cleaned_data.get("quantidade")
        return qtd or 1
