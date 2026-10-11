"""Formulários Django (ModelForms) para os cadastros do SAMU 192."""
from __future__ import annotations

import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from . import models


CPF_REGEX = re.compile(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$")


def _c(*extras: str) -> str:
    base = (
        "w-full rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm text-neutral-800 "
        "placeholder:text-neutral-400 focus:border-red-500 focus:outline-none focus:ring-2 "
        "focus:ring-red-100 transition"
    )
    return " ".join([base, *extras])


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário ou e-mail",
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "seu.usuario", "autofocus": True, "data-testid": "login-username"}),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": _c(), "placeholder": "••••••••", "data-testid": "login-password"}),
    )
    remember_me = forms.BooleanField(
        label="Lembrar desta sessão",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 accent-red-600", "data-testid": "login-remember"}),
    )


class RegistroForm(forms.Form):
    """Registro completo com função, data nascimento, telefone, email, senha."""

    nome_completo = forms.CharField(
        label="Nome completo",
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: Gustavo Batista Oliveira", "data-testid": "reg-nome"}),
    )
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"class": _c(), "type": "date", "data-testid": "reg-nascimento"}, format="%Y-%m-%d"),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": _c(), "placeholder": "voce@samu.gov.br", "data-testid": "reg-email"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "(00) 00000-0000", "data-testid": "reg-telefone"}),
    )
    funcao = forms.ChoiceField(
        label="Função",
        choices=models.Perfil.FUNCAO_CHOICES,
        widget=forms.Select(attrs={"class": _c(), "data-testid": "reg-funcao"}),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": _c(), "placeholder": "Mín. 8 caracteres · letras + números", "data-testid": "reg-senha"}),
        help_text="Mínimo 8 caracteres, com letras e números.",
    )
    senha2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": _c(), "placeholder": "Digite novamente", "data-testid": "reg-senha2"}),
    )
    remember_me = forms.BooleanField(
        label="Lembrar desta sessão",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "w-4 h-4 accent-red-600", "data-testid": "reg-remember"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está em uso.")
        return email

    def clean_senha(self):
        senha = self.cleaned_data["senha"]
        if len(senha) < 8:
            raise forms.ValidationError("A senha deve ter pelo menos 8 caracteres.")
        if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
            raise forms.ValidationError("A senha deve conter letras e números.")
        validate_password(senha)
        return senha

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("senha") and cleaned.get("senha2") and cleaned["senha"] != cleaned["senha2"]:
            self.add_error("senha2", "As senhas não coincidem.")
        return cleaned

    def save(self) -> User:
        d = self.cleaned_data
        nome = d["nome_completo"].strip()
        partes = nome.split(maxsplit=1)
        first = partes[0]
        last = partes[1] if len(partes) > 1 else ""
        # username = parte local do e-mail
        base_username = d["email"].split("@")[0]
        username = base_username
        i = 1
        while User.objects.filter(username=username).exists():
            i += 1
            username = f"{base_username}{i}"

        is_admin = d["funcao"] == "ADMINISTRADOR"
        user = User(
            username=username,
            email=d["email"],
            first_name=first,
            last_name=last,
            is_staff=is_admin,
            is_superuser=is_admin,
        )
        user.set_password(d["senha"])
        user.save()
        models.Perfil.objects.create(
            user=user,
            funcao=d["funcao"],
            telefone=d["telefone"],
            data_nascimento=d["data_nascimento"],
        )
        # Cria também um Funcionario correspondente (para registro de manuseios)
        funcao_map = {
            "ADMINISTRADOR": "ADMINISTRATIVO",
            "MOTORISTA": "MOTORISTA",
            "AUXILIAR": "AUXILIAR",
            "ENFERMEIRO": "ENFERMEIRO",
        }
        if not models.Funcionario.objects.filter(email__iexact=d["email"]).exists():
            models.Funcionario.objects.create(
                nome=nome,
                email=d["email"],
                funcao=funcao_map[d["funcao"]],
                telefone=d["telefone"],
                usuario=user,
            )
        return user


class MedicamentoForm(forms.ModelForm):
    class Meta:
        model = models.Medicamento
        fields = ("nome", "metragem", "tipo", "forma", "complemento")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: Adrenalina", "data-testid": "medicamento-nome"}),
            "metragem": forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: 1mg/mL, 500mg, 20mL", "data-testid": "medicamento-metragem"}),
            "tipo": forms.Select(attrs={"class": _c(), "data-testid": "medicamento-tipo"}),
            "forma": forms.Select(attrs={"class": _c(), "data-testid": "medicamento-forma"}),
            "complemento": forms.TextInput(
                attrs={"class": _c(), "placeholder": "Ex.: Uso restrito à emergência", "data-testid": "medicamento-complemento"}
            ),
        }


class LoteForm(forms.ModelForm):
    class Meta:
        model = models.Lote
        fields = ("codigo", "validade", "quantidade", "situacao")
        widgets = {
            "codigo": forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: L2025-A1", "data-testid": "lote-codigo"}),
            "validade": forms.DateInput(
                attrs={"class": _c(), "type": "date", "data-testid": "lote-validade"}, format="%Y-%m-%d"
            ),
            "quantidade": forms.NumberInput(attrs={"class": _c(), "min": 0, "data-testid": "lote-quantidade"}),
            "situacao": forms.Select(attrs={"class": _c(), "data-testid": "lote-situacao"}),
        }


class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = models.Funcionario
        fields = ("nome", "cpf", "funcao", "email", "telefone")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _c(), "placeholder": "Nome completo", "data-testid": "funcionario-nome"}),
            "cpf": forms.TextInput(attrs={"class": _c(), "placeholder": "000.000.000-00", "data-testid": "funcionario-cpf"}),
            "funcao": forms.Select(attrs={"class": _c(), "data-testid": "funcionario-funcao"}),
            "email": forms.EmailInput(attrs={"class": _c(), "placeholder": "email@samu.gov.br", "data-testid": "funcionario-email"}),
            "telefone": forms.TextInput(attrs={"class": _c(), "placeholder": "(00) 00000-0000", "data-testid": "funcionario-telefone"}),
        }

    def clean_cpf(self):
        cpf = (self.cleaned_data.get("cpf") or "").strip()
        if cpf and not CPF_REGEX.match(cpf):
            raise forms.ValidationError("Informe o CPF no formato 000.000.000-00.")
        return cpf


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = models.Veiculo
        fields = ("modelo", "ano", "tipo", "status")
        widgets = {
            "modelo": forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: Mercedes-Benz Sprinter", "data-testid": "veiculo-modelo"}),
            "ano": forms.NumberInput(attrs={"class": _c(), "min": 1980, "max": 2100, "data-testid": "veiculo-ano"}),
            "tipo": forms.Select(attrs={"class": _c(), "data-testid": "veiculo-tipo"}),
            "status": forms.Select(attrs={"class": _c(), "data-testid": "veiculo-status"}),
        }

    def clean_ano(self):
        ano = self.cleaned_data.get("ano")
        if ano is None or ano < 1980 or ano > 2100:
            raise forms.ValidationError("Ano inválido.")
        return ano


class PerfilForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nome completo",
        widget=forms.TextInput(attrs={"class": _c(), "data-testid": "perfil-nome"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": _c(), "data-testid": "perfil-email"}),
    )

    class Meta:
        model = models.Perfil
        fields = ("telefone", "data_nascimento")
        widgets = {
            "telefone": forms.TextInput(attrs={"class": _c(), "placeholder": "(00) 00000-0000", "data-testid": "perfil-telefone"}),
            "data_nascimento": forms.DateInput(attrs={"class": _c(), "type": "date", "data-testid": "perfil-nascimento"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            full = self.instance.user.get_full_name() or self.instance.user.first_name
            self.fields["first_name"].initial = full
            self.fields["email"].initial = self.instance.user.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        user = perfil.user
        nome = self.cleaned_data.get("first_name", "").strip()
        partes = nome.split(maxsplit=1)
        user.first_name = partes[0] if partes else ""
        user.last_name = partes[1] if len(partes) > 1 else ""
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save()
            perfil.save()
        return perfil


class EditarContaForm(forms.ModelForm):
    """Admin editando conta de outro usuário."""

    first_name = forms.CharField(label="Nome completo", widget=forms.TextInput(attrs={"class": _c()}))
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"class": _c()}))
    nova_senha = forms.CharField(
        label="Nova senha (opcional)",
        required=False,
        widget=forms.PasswordInput(attrs={"class": _c(), "placeholder": "Deixe em branco para manter"}),
    )

    class Meta:
        model = models.Perfil
        fields = ("funcao", "telefone", "data_nascimento")
        widgets = {
            "funcao": forms.Select(attrs={"class": _c()}),
            "telefone": forms.TextInput(attrs={"class": _c()}),
            "data_nascimento": forms.DateInput(attrs={"class": _c(), "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.get_full_name() or self.instance.user.first_name
            self.fields["email"].initial = self.instance.user.email

    def clean_nova_senha(self):
        senha = self.cleaned_data.get("nova_senha", "")
        if senha:
            if len(senha) < 8 or not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
                raise forms.ValidationError("Mínimo 8 caracteres, letras e números.")
            validate_password(senha)
        return senha

    def save(self, commit=True):
        perfil = super().save(commit=False)
        user = perfil.user
        nome = self.cleaned_data.get("first_name", "").strip()
        partes = nome.split(maxsplit=1)
        user.first_name = partes[0] if partes else ""
        user.last_name = partes[1] if len(partes) > 1 else ""
        user.email = self.cleaned_data.get("email", "")
        is_admin = perfil.funcao == "ADMINISTRADOR"
        user.is_staff = is_admin
        user.is_superuser = is_admin
        if self.cleaned_data.get("nova_senha"):
            user.set_password(self.cleaned_data["nova_senha"])
        if commit:
            user.save()
            perfil.save()
        return perfil


_CHK = "w-4 h-4 accent-red-600 rounded"


class FirebaseConfigForm(forms.ModelForm):
    credenciais = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={"accept": ".json,application/json", "class": "block w-full text-xs mt-2",
                                      "data-testid": "fb-credenciais"}),
    )

    class Meta:
        model = models.Configuracao
        fields = ("firebase_bucket", "firebase_simulado", "firebase_auto", "firebase_intervalo_horas", "firebase_sync_login")
        widgets = {
            "firebase_bucket": forms.TextInput(attrs={"class": _c(), "placeholder": "seu-projeto.appspot.com", "data-testid": "fb-bucket"}),
            "firebase_simulado": forms.CheckboxInput(attrs={"class": _CHK, "data-testid": "fb-simulado"}),
            "firebase_auto": forms.CheckboxInput(attrs={"class": _CHK, "data-testid": "fb-auto"}),
            "firebase_intervalo_horas": forms.NumberInput(attrs={"class": _c(), "min": 1, "max": 720, "data-testid": "fb-intervalo"}),
            "firebase_sync_login": forms.CheckboxInput(attrs={"class": _CHK, "data-testid": "fb-sync-login"}),
        }

    def clean_firebase_bucket(self):
        return (self.cleaned_data.get("firebase_bucket") or "").strip().removeprefix("gs://").strip("/")

    def clean_firebase_intervalo_horas(self):
        h = self.cleaned_data.get("firebase_intervalo_horas") or 0
        if not 1 <= h <= 720:
            raise forms.ValidationError("Intervalo deve ficar entre 1 e 720 horas.")
        return h

    def clean_credenciais(self):
        arq = self.cleaned_data.get("credenciais")
        if arq and arq.size > 64 * 1024:
            raise forms.ValidationError("Arquivo grande demais para uma chave de serviço.")
        return arq


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = models.Configuracao
        fields = (
            "estoque_muito_baixo", "estoque_baixo", "estoque_alto",
            "validade_muito_proximo", "validade_proximo", "validade_controlado",
            "intervalo_dias_padrao", "diretorio_downloads",
        )
        widgets = {
            "estoque_muito_baixo": forms.NumberInput(attrs={"class": _c(), "min": 0, "data-testid": "cfg-muito-baixo"}),
            "estoque_baixo": forms.NumberInput(attrs={"class": _c(), "min": 1, "data-testid": "cfg-baixo"}),
            "estoque_alto": forms.NumberInput(attrs={"class": _c(), "min": 1, "data-testid": "cfg-alto"}),
            "validade_muito_proximo": forms.NumberInput(attrs={"class": _c(), "min": 0, "data-testid": "cfg-val-mp"}),
            "validade_proximo": forms.NumberInput(attrs={"class": _c(), "min": 1, "data-testid": "cfg-val-p"}),
            "validade_controlado": forms.NumberInput(attrs={"class": _c(), "min": 1, "data-testid": "cfg-val-c"}),
            "intervalo_dias_padrao": forms.NumberInput(attrs={"class": _c(), "min": 1, "data-testid": "cfg-intervalo"}),
            "diretorio_downloads": forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: C:\\Relatorios ou /home/user/Downloads", "data-testid": "cfg-dir"}),
        }

    def clean(self):
        cleaned = super().clean()
        mb = cleaned.get("estoque_muito_baixo") or 0
        b = cleaned.get("estoque_baixo") or 0
        a = cleaned.get("estoque_alto") or 0
        if not (mb < b < a):
            raise forms.ValidationError("Valores de estoque devem crescer: muito baixo < baixo < alto.")
        mp = cleaned.get("validade_muito_proximo") or 0
        p = cleaned.get("validade_proximo") or 0
        c = cleaned.get("validade_controlado") or 0
        if not (mp < p < c):
            raise forms.ValidationError("Dias de validade devem crescer: muito próximo < próximo < controlado.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.validade_configurada = True
        if commit:
            obj.save()
        return obj


class MovimentacaoForm(forms.Form):
    """Modal 'Registrar entrada/saída': medicamento + lote + quantidade + tipo + forma + origem/destino."""

    TIPO_MOV_CHOICES = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    tipo_movimentacao = forms.ChoiceField(choices=TIPO_MOV_CHOICES, widget=forms.HiddenInput())
    medicamento_query = forms.CharField(
        label="Medicamento (nome ou ID)",
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "Digite o nome do medicamento", "autocomplete": "off", "data-testid": "mov-medicamento"}),
    )
    lote_codigo = forms.CharField(
        label="Lote",
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "Ex.: L2025-A1", "autocomplete": "off", "data-testid": "mov-lote"}),
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        widget=forms.NumberInput(attrs={"class": _c(), "placeholder": "1", "min": 1, "data-testid": "mov-quantidade"}),
    )
    tipo_medicamento = forms.ModelChoiceField(
        queryset=models.TipoMedicamento.objects.all(),
        required=False,
        empty_label="— automático (último) —",
        widget=forms.Select(attrs={"class": _c(), "data-testid": "mov-tipo"}),
    )
    forma_medicamento = forms.ModelChoiceField(
        queryset=models.FormaMedicamento.objects.all(),
        required=False,
        empty_label="— automático (último) —",
        widget=forms.Select(attrs={"class": _c(), "data-testid": "mov-forma"}),
    )
    origem_destino = forms.CharField(
        label="Origem / Destino",
        required=False,
        widget=forms.TextInput(attrs={"class": _c(), "placeholder": "De onde veio ou para onde foi (opcional)", "data-testid": "mov-origem-destino"}),
    )
