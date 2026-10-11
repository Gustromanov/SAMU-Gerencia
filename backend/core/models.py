"""Modelos de domínio do SAMU 192 (Django ORM)."""
from __future__ import annotations

from datetime import timedelta
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ---------- Tabelas de lookup ----------
class TipoMedicamento(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Tipo de medicamento"
        verbose_name_plural = "Tipos de medicamento"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class FormaMedicamento(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name = "Forma farmacêutica"
        verbose_name_plural = "Formas farmacêuticas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# ---------- Configuração do sistema (singleton) ----------
class Configuracao(models.Model):
    """Painel do administrador: thresholds de estoque/validade e diretório padrão de exports."""

    # Estoque (unidades)
    estoque_muito_baixo = models.PositiveIntegerField(default=5)
    estoque_baixo = models.PositiveIntegerField(default=15)
    estoque_alto = models.PositiveIntegerField(default=200)

    # Validade (dias a partir de hoje)
    validade_muito_proximo = models.PositiveIntegerField(default=15)
    validade_proximo = models.PositiveIntegerField(default=60)
    validade_controlado = models.PositiveIntegerField(default=180)
    # <0 => Vencido ; >controlado => Distante

    # Outras preferências
    diretorio_downloads = models.CharField(max_length=512, blank=True, default="")
    intervalo_dias_padrao = models.PositiveIntegerField(default=30)

    # Flag: thresholds de validade foram definidos pelo admin?
    validade_configurada = models.BooleanField(default=False)

    # Backup Firebase
    firebase_bucket = models.CharField(max_length=200, blank=True, default="")
    firebase_simulado = models.BooleanField(default=True)
    firebase_auto = models.BooleanField(default=False)
    firebase_intervalo_horas = models.PositiveIntegerField(default=24)
    firebase_sync_login = models.BooleanField(default=True)
    firebase_ultimo_backup = models.DateTimeField(null=True, blank=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"

    def __str__(self):
        return "Configuração do sistema"

    @classmethod
    def obter(cls) -> "Configuracao":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ---------- Medicamento / Lote ----------
class Medicamento(models.Model):
    nome = models.CharField(max_length=160)
    metragem = models.CharField(max_length=40, blank=True, default="", help_text="Ex.: 500mg, 10mg/mL, 20mL")
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
                fields=["nome", "metragem", "tipo", "forma"],
                name="uniq_medicamento_nome_metragem_tipo_forma",
            )
        ]
        ordering = ["nome", "metragem"]

    def __str__(self):
        return f"{self.nome} {self.metragem} — {self.tipo.nome}/{self.forma.nome}".strip()

    @property
    def nome_exibicao(self) -> str:
        return f"{self.nome} {self.metragem}".strip()

    @property
    def quantidade_total(self) -> int:
        return sum(l.quantidade for l in self.lotes.all())

    @property
    def total_lotes(self) -> int:
        return self.lotes.count()


class Lote(models.Model):
    SITUACAO_CHOICES = [
        ("RECEBIDO", "Recebido"),
        ("LOTEADO", "Entregue"),
        ("DOADO", "Doado"),
    ]

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

    def __str__(self):
        return f"{self.codigo} — {self.medicamento.nome_exibicao}"

    def _cfg(self) -> Configuracao:
        if not hasattr(self, "_cached_cfg"):
            self._cached_cfg = Configuracao.obter()
        return self._cached_cfg

    @property
    def nivel_estoque(self) -> str:
        cfg = self._cfg()
        q = self.quantidade
        if q <= cfg.estoque_muito_baixo:
            return "MUITO_BAIXO"
        if q <= cfg.estoque_baixo:
            return "BAIXO"
        if q >= cfg.estoque_alto:
            return "ALTO"
        return "NORMAL"

    @property
    def nivel_estoque_label(self) -> str:
        return {
            "MUITO_BAIXO": "Muito baixo",
            "BAIXO": "Baixo",
            "NORMAL": "Normal",
            "ALTO": "Alto",
        }[self.nivel_estoque]

    @property
    def dias_para_validade(self) -> int:
        return (self.validade - timezone.now().date()).days

    @property
    def vencido(self) -> bool:
        return self.dias_para_validade < 0

    @property
    def nivel_validade(self) -> str:
        """Retorna a classificação de validade conforme Configuracao."""
        cfg = self._cfg()
        if not cfg.validade_configurada:
            return "NAO_DEFINIDO"
        d = self.dias_para_validade
        if d < 0:
            return "VENCIDO"
        if d <= cfg.validade_muito_proximo:
            return "MUITO_PROXIMO"
        if d <= cfg.validade_proximo:
            return "PROXIMO"
        if d <= cfg.validade_controlado:
            return "CONTROLADO"
        return "DISTANTE"

    @property
    def nivel_validade_label(self) -> str:
        return {
            "VENCIDO": "Vencido",
            "MUITO_PROXIMO": "Muito próximo",
            "PROXIMO": "Próximo",
            "CONTROLADO": "Controlado",
            "DISTANTE": "Distante",
            "NAO_DEFINIDO": "—",
        }[self.nivel_validade]

    @property
    def mostra_dias_restantes(self) -> bool:
        return self.nivel_validade in {"VENCIDO", "MUITO_PROXIMO", "PROXIMO"}


# ---------- Funcionário ----------
class Funcionario(models.Model):
    """Cadastro profissional (independente da conta de login — serve para registro de manuseio)."""

    FUNCAO_CHOICES = [
        ("MEDICO", "Médico(a)"),
        ("ENFERMEIRO", "Enfermeiro(a)"),
        ("TECNICO", "Técnico(a) de enfermagem"),
        ("MOTORISTA", "Motorista socorrista"),
        ("FARMACEUTICO", "Farmacêutico(a)"),
        ("ADMINISTRATIVO", "Administrativo"),
        ("COORDENADOR", "Coordenador(a)"),
        ("AUXILIAR", "Auxiliar"),
        ("OUTRO", "Outro"),
    ]

    cpf = models.CharField(max_length=14, unique=True, blank=True, default="")
    nome = models.CharField(max_length=160)
    funcao = models.CharField(max_length=24, choices=FUNCAO_CHOICES)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=32, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="funcionario"
    )

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"
        ordering = ["nome"]

    def __str__(self):
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
    STATUS_CHOICES = [
        ("NORMAL", "Normal"),
        ("MANUTENCAO", "Em manutenção"),
        ("INATIVO", "Inativo"),
    ]
    TIPO_CHOICES = [
        ("VAN", "Van / Ambulância"),
        ("CARRO", "Carro"),
        ("MOTO", "Motolância"),
    ]

    codigo_id = models.CharField(max_length=32, unique=True, blank=True, default="")
    modelo = models.CharField(max_length=120)
    ano = models.PositiveIntegerField()
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES, default="VAN")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="NORMAL")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["codigo_id"]

    def __str__(self):
        return f"{self.codigo_id} — {self.modelo}"

    def save(self, *args, **kwargs):
        if not self.codigo_id:
            # Gera ID automático baseado em tipo + sequencial
            prefixos = {"VAN": "USB", "CARRO": "USA", "MOTO": "MOTO"}
            prefixo = prefixos.get(self.tipo, "VEI")
            ultimo = (
                Veiculo.objects.filter(codigo_id__startswith=f"{prefixo}-")
                .order_by("-id").first()
            )
            if ultimo and "-" in ultimo.codigo_id:
                try:
                    n = int(ultimo.codigo_id.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    n = 1
            else:
                n = 1
            self.codigo_id = f"{prefixo}-{n:02d}"
        super().save(*args, **kwargs)


# ---------- Movimentação de estoque ----------
class Movimentacao(models.Model):
    TIPO_CHOICES = [("ENTRADA", "Entrada"), ("SAIDA", "Saída")]

    tipo = models.CharField(max_length=8, choices=TIPO_CHOICES)
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="movimentacoes")
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes"
    )
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes"
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

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.lote} ({self.quantidade})"


# ---------- Histórico de backups Firebase ----------
class BackupFirebase(models.Model):
    ORIGEM_CHOICES = [
        ("MANUAL", "Manual (painel)"),
        ("AUTOMATICO", "Automático"),
        ("LOGIN", "Ao fazer login"),
        ("TERMINAL", "Terminal / agendador"),
    ]
    MODO_CHOICES = [("REAL", "Firebase"), ("SIMULADO", "Simulado (local)")]
    STATUS_CHOICES = [("SUCESSO", "Sucesso"), ("ERRO", "Erro")]

    criado_em = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(max_length=12, choices=ORIGEM_CHOICES)
    modo = models.CharField(max_length=10, choices=MODO_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ERRO")
    destino = models.CharField(max_length=500, blank=True, default="")
    tamanho_bytes = models.PositiveIntegerField(default=0)
    mensagem = models.CharField(max_length=500, blank=True, default="")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="backups_firebase")

    class Meta:
        verbose_name = "Backup Firebase"
        verbose_name_plural = "Backups Firebase"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.criado_em:%d/%m/%Y %H:%M} — {self.get_status_display()}"


# ---------- Perfil do usuário logado (com role!) ----------
class Perfil(models.Model):
    """Extensão de User com função (role) e dados pessoais do operador."""

    FUNCAO_CHOICES = [
        ("ADMINISTRADOR", "Administrador"),
        ("MOTORISTA", "Motorista"),
        ("AUXILIAR", "Auxiliar"),
        ("ENFERMEIRO", "Enfermeiro"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    funcao = models.CharField(max_length=16, choices=FUNCAO_CHOICES, default="ADMINISTRADOR")
    telefone = models.CharField(max_length=32, blank=True, default="")
    data_nascimento = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"
        ordering = ["user__first_name"]

    def __str__(self):
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

    @property
    def is_admin(self) -> bool:
        return self.funcao == "ADMINISTRADOR"

    @property
    def pode_ver_medicamentos(self) -> bool:
        return self.funcao in {"ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO"}

    @property
    def pode_ver_veiculos(self) -> bool:
        return self.funcao in {"ADMINISTRADOR", "MOTORISTA"}

    @property
    def pode_ver_funcionarios(self) -> bool:
        return self.funcao == "ADMINISTRADOR"

    @property
    def pode_editar_medicamentos(self) -> bool:
        return self.funcao in {"ADMINISTRADOR", "AUXILIAR", "ENFERMEIRO"}

    @property
    def pode_deletar_medicamentos(self) -> bool:
        return self.funcao == "ADMINISTRADOR"

    @property
    def pode_editar_veiculos(self) -> bool:
        return self.funcao in {"ADMINISTRADOR", "MOTORISTA"}

    @property
    def pode_deletar_veiculos(self) -> bool:
        return self.funcao == "ADMINISTRADOR"

    @property
    def pode_exportar(self) -> bool:
        return self.funcao == "ADMINISTRADOR"

    @property
    def home_url_name(self) -> str:
        return {
            "ADMINISTRADOR": "medicamentos_lista",
            "AUXILIAR": "medicamentos_lista",
            "ENFERMEIRO": "medicamentos_lista",
            "MOTORISTA": "veiculos_lista",
        }[self.funcao]
