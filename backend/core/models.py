"""Modelos de domínio do SAMU 192 (Django ORM)."""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ---------- Tabelas de lookup ----------
class TipoMedicamento(models.Model):
    """Categoria/finalidade do medicamento (analgésico, antibiótico, vacina, etc.)."""

    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Tipo de medicamento"
        verbose_name_plural = "Tipos de medicamento"
        ordering = ["nome"]

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class FormaMedicamento(models.Model):
    """Forma farmacêutica (comprimido, cápsula, gotas, ampola, etc.)."""

    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Forma farmacêutica"
        verbose_name_plural = "Formas farmacêuticas"
        ordering = ["nome"]

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


# ---------- Medicamento / Lote ----------
class Medicamento(models.Model):
    """Um medicamento cadastrado (identidade lógica). Cada lote é uma linha em Lote."""

    nome = models.CharField(max_length=160)
    tipo = models.ForeignKey(TipoMedicamento, on_delete=models.PROTECT, related_name="medicamentos")
    forma = models.ForeignKey(FormaMedicamento, on_delete=models.PROTECT, related_name="medicamentos")
    complemento = models.CharField(max_length=240, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "tipo", "forma"], name="uniq_medicamento_nome_tipo_forma"
            )
        ]
        ordering = ["nome"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.nome} — {self.tipo.nome} / {self.forma.nome}"

    @property
    def quantidade_total(self) -> int:
        return sum(l.quantidade for l in self.lotes.all())

    @property
    def total_lotes(self) -> int:
        return self.lotes.count()


class Lote(models.Model):
    """Lote específico de um medicamento (código, validade, quantidade)."""

    SITUACAO_CHOICES = [
        ("LOTEADO", "Loteado"),
        ("RECEBIDO", "Recebido"),
        ("DOADO", "Doado"),
    ]

    NIVEL_MUITO_BAIXO = 5
    NIVEL_BAIXO = 15

    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name="lotes")
    codigo = models.CharField(max_length=64)
    validade = models.DateField()
    quantidade = models.PositiveIntegerField(default=0)
    situacao = models.CharField(max_length=16, choices=SITUACAO_CHOICES, default="RECEBIDO")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        constraints = [
            models.UniqueConstraint(fields=["medicamento", "codigo"], name="uniq_lote_medicamento_codigo"),
        ]
        ordering = ["validade", "codigo"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.codigo} — {self.medicamento.nome}"

    @property
    def nivel_estoque(self) -> str:
        if self.quantidade <= self.NIVEL_MUITO_BAIXO:
            return "MUITO_BAIXO"
        if self.quantidade <= self.NIVEL_BAIXO:
            return "BAIXO"
        return "NORMAL"

    @property
    def nivel_estoque_label(self) -> str:
        return {"MUITO_BAIXO": "Muito baixo", "BAIXO": "Baixo", "NORMAL": "Normal"}[self.nivel_estoque]

    @property
    def dias_para_validade(self) -> int:
        return (self.validade - timezone.now().date()).days

    @property
    def vencido(self) -> bool:
        return self.dias_para_validade < 0

    @property
    def proximo_vencimento(self) -> bool:
        return 0 <= self.dias_para_validade <= 30


# ---------- Funcionário ----------
class Funcionario(models.Model):
    """Colaborador da unidade SAMU."""

    FUNCAO_CHOICES = [
        ("MEDICO", "Médico(a)"),
        ("ENFERMEIRO", "Enfermeiro(a)"),
        ("TECNICO", "Técnico(a) de enfermagem"),
        ("MOTORISTA", "Motorista socorrista"),
        ("FARMACEUTICO", "Farmacêutico(a)"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("COORDENADOR", "Coordenador(a)"),
        ("OUTRO", "Outro"),
    ]

    cpf = models.CharField(max_length=14, unique=True, help_text="Formato 000.000.000-00")
    nome = models.CharField(max_length=160)
    funcao = models.CharField(max_length=24, choices=FUNCAO_CHOICES)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=32)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="funcionario"
    )

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ["nome"]

    def __str__(self) -> str:  # pragma: no cover
        return self.nome

    @property
    def iniciais(self) -> str:
        partes = [p for p in self.nome.strip().split() if p]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()


# ---------- Veículo ----------
class Veiculo(models.Model):
    """Viatura da unidade SAMU."""

    STATUS_CHOICES = [
        ("NORMAL", "Normal"),
        ("MANUTENCAO", "Em manutenção"),
        ("INATIVO", "Inativo"),
    ]

    codigo_id = models.CharField(
        max_length=32, unique=True, help_text="Identificador visível da viatura (ex.: USB-01)"
    )
    modelo = models.CharField(max_length=120)
    ano = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="NORMAL")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["codigo_id"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.codigo_id} — {self.modelo}"


# ---------- Movimentação de estoque ----------
class Movimentacao(models.Model):
    """Registro histórico de entrada/saída de um lote de medicamento."""

    TIPO_CHOICES = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    tipo = models.CharField(max_length=8, choices=TIPO_CHOICES)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="movimentacoes")
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes"
    )
    quantidade = models.PositiveIntegerField(default=1)
    origem = models.CharField(max_length=160, blank=True, default="")
    destino = models.CharField(max_length=160, blank=True, default="")
    observacao = models.CharField(max_length=240, blank=True, default="")
    horario = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-horario"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.get_tipo_display()} — {self.lote} ({self.quantidade})"


# ---------- Perfil do usuário logado ----------
class Perfil(models.Model):
    """Dados exibidos na tela de perfil (extensão do django.contrib.auth.User)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    telefone = models.CharField(max_length=32, blank=True, default="")
    cargo = models.CharField(max_length=80, blank=True, default="Administrador(a) SAMU")
    bio = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"

    def __str__(self) -> str:  # pragma: no cover
        return self.user.get_full_name() or self.user.username

    @property
    def iniciais(self) -> str:
        nome = (self.user.get_full_name() or self.user.username).strip()
        partes = [p for p in nome.split() if p]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()
