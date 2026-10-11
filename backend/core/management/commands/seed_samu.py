"""Popula o banco com dados iniciais."""
import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from core import models


TIPOS = ["Analgésico", "Antibiótico", "Anti-inflamatório", "Antiviral",
         "Antifúngico", "Antidepressivo", "Antihipertensivo", "Vacina", "Outro"]
FORMAS = ["Comprimido", "Cápsula", "Drágea", "Pílula", "Gotas", "Xarope",
          "Ampola", "Frasco-ampola", "Pomada", "Pastilha", "Outro"]

MEDICAMENTOS = [
    ("Adrenalina", "1mg/mL", "Outro", "Ampola", "Uso restrito à emergência"),
    ("Amoxicilina", "500mg", "Antibiótico", "Cápsula", ""),
    ("Azitromicina", "500mg", "Antibiótico", "Comprimido", ""),
    ("Ceftriaxona", "1g", "Antibiótico", "Frasco-ampola", ""),
    ("Dipirona", "500mg", "Analgésico", "Comprimido", ""),
    ("Dipirona", "500mg/mL", "Analgésico", "Gotas", ""),
    ("Paracetamol", "750mg", "Analgésico", "Comprimido", ""),
    ("Paracetamol", "200mg/mL", "Analgésico", "Gotas", "Uso pediátrico"),
    ("Ibuprofeno", "600mg", "Anti-inflamatório", "Comprimido", ""),
    ("Diclofenaco", "50mg", "Anti-inflamatório", "Drágea", ""),
    ("Diazepam", "10mg", "Outro", "Comprimido", "Controle especial"),
    ("Midazolam", "5mg/mL", "Outro", "Ampola", "Uso hospitalar"),
    ("Morfina", "10mg/mL", "Analgésico", "Ampola", "Controlado"),
    ("Tramadol", "100mg/2mL", "Analgésico", "Ampola", ""),
    ("Hidralazina", "20mg", "Antihipertensivo", "Comprimido", ""),
    ("Losartana", "50mg", "Antihipertensivo", "Comprimido", ""),
    ("Captopril", "25mg", "Antihipertensivo", "Comprimido", ""),
    ("Captopril", "70mg/mL", "Antihipertensivo", "Pomada", "Uso tópico"),
    ("Fluoxetina", "20mg", "Antidepressivo", "Cápsula", ""),
    ("Sertralina", "50mg", "Antidepressivo", "Comprimido", ""),
    ("Aciclovir", "200mg", "Antiviral", "Comprimido", ""),
    ("Fluconazol", "150mg", "Antifúngico", "Cápsula", ""),
    ("Vacina Antitetânica", "", "Vacina", "Ampola", "Reforço adulto"),
    ("Vacina Hepatite B", "", "Vacina", "Ampola", ""),
    ("Soro fisiológico", "0,9%", "Outro", "Frasco-ampola", "500mL"),
    ("Ringer lactato", "", "Outro", "Frasco-ampola", "500mL"),
    ("Glicose", "50%", "Outro", "Ampola", "Emergência hipoglicemia"),
    ("Atropina", "0,25mg/mL", "Outro", "Ampola", ""),
    ("Amiodarona", "150mg/3mL", "Outro", "Ampola", "PCR"),
    ("Furosemida", "20mg/2mL", "Outro", "Ampola", ""),
    ("Omeprazol", "20mg", "Outro", "Cápsula", ""),
    ("Salbutamol", "100mcg", "Outro", "Outro", "Uso inalatório"),
    ("Prednisona", "20mg", "Anti-inflamatório", "Comprimido", "Corticoide"),
]

FUNCIONARIOS = [
    ("111.222.333-44", "Dra. Camila Barreto Rocha", "MEDICO", "camila.rocha@samu.gov.br", "(21) 98811-4423"),
    ("222.333.444-55", "Dr. Marcos Andrade", "MEDICO", "marcos.andrade@samu.gov.br", "(21) 98773-1290"),
    ("333.444.555-66", "Amanda Xavier Melo", "ENFERMEIRO", "amanda.xavier@samu.gov.br", "(21) 99334-7712"),
    ("444.555.666-77", "Renato Prudencio da Silva", "ENFERMEIRO", "renato.prudencio@samu.gov.br", "(21) 99201-8802"),
    ("555.666.777-88", "Julio Menezes", "TECNICO", "julio.menezes@samu.gov.br", "(21) 98177-2233"),
    ("666.777.888-99", "Priscila Duarte", "TECNICO", "priscila.duarte@samu.gov.br", "(21) 98884-6641"),
    ("777.888.999-00", "Fabio Souto", "MOTORISTA", "fabio.souto@samu.gov.br", "(21) 99777-4409"),
    ("888.999.000-11", "Nicole Fontes", "FARMACEUTICO", "nicole.fontes@samu.gov.br", "(21) 99441-1188"),
    ("999.000.111-22", "Eduardo Aquino", "COORDENADOR", "eduardo.aquino@samu.gov.br", "(21) 99873-3421"),
    ("000.111.222-33", "Talita Ramos", "ADMINISTRATIVO", "talita.ramos@samu.gov.br", "(21) 98234-5566"),
]

VEICULOS = [
    ("Renault Master USB", 2022, "VAN", "NORMAL"),
    ("Mercedes-Benz Sprinter USB", 2021, "VAN", "NORMAL"),
    ("Mercedes-Benz Sprinter USA", 2023, "VAN", "NORMAL"),
    ("Fiat Ducato USA", 2019, "VAN", "MANUTENCAO"),
    ("Honda XRE 300", 2022, "MOTO", "NORMAL"),
    ("Honda XRE 300", 2020, "MOTO", "INATIVO"),
    ("Iveco Daily USB", 2018, "VAN", "MANUTENCAO"),
    ("Renault Master USA", 2024, "VAN", "NORMAL"),
    ("Fiat Toro", 2023, "CARRO", "NORMAL"),
]


class Command(BaseCommand):
    help = "Popula o banco com dados demonstrativos do SAMU 192."

    def handle(self, *args, **options):
        random.seed(42)

        # Configuração padrão com validade já definida
        cfg = models.Configuracao.obter()
        cfg.validade_configurada = True
        cfg.save()

        tipos = {}
        for n in TIPOS:
            o, _ = models.TipoMedicamento.objects.get_or_create(nome=n, defaults={"slug": slugify(n)})
            tipos[n] = o
        formas = {}
        for n in FORMAS:
            o, _ = models.FormaMedicamento.objects.get_or_create(nome=n, defaults={"slug": slugify(n)})
            formas[n] = o
        self.stdout.write(self.style.SUCCESS(f"Tipos: {len(tipos)} · Formas: {len(formas)}"))

        # Admin
        admin, criado = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "Ana Silva", "email": "admin@samu.gov.br",
                      "is_staff": True, "is_superuser": True},
        )
        if criado:
            admin.set_password("samu192"); admin.save()
        models.Perfil.objects.get_or_create(user=admin, defaults={
            "funcao": "ADMINISTRADOR", "telefone": "(21) 99999-0000"})

        # Usuários exemplo para cada função
        for username, nome, email, funcao, senha in [
            ("motorista.demo", "Carlos Almeida", "motorista@samu.gov.br", "MOTORISTA", "motorista123"),
            ("auxiliar.demo", "Letícia Souza", "auxiliar@samu.gov.br", "AUXILIAR", "auxiliar123"),
            ("enfermeiro.demo", "Pedro Henrique Costa", "enfermeiro@samu.gov.br", "ENFERMEIRO", "enfermeiro123"),
        ]:
            u, cri = User.objects.get_or_create(username=username, defaults={
                "first_name": nome.split()[0], "last_name": " ".join(nome.split()[1:]),
                "email": email})
            if cri:
                u.set_password(senha); u.save()
            models.Perfil.objects.get_or_create(user=u, defaults={
                "funcao": funcao, "telefone": "(21) 98888-0000"})

        self.stdout.write(self.style.SUCCESS("Usuários: admin/samu192, motorista.demo, auxiliar.demo, enfermeiro.demo"))

        # Medicamentos + lotes
        for nome, metragem, tipo, forma, compl in MEDICAMENTOS:
            med, _ = models.Medicamento.objects.get_or_create(
                nome=nome, metragem=metragem, tipo=tipos[tipo], forma=formas[forma],
                defaults={"complemento": compl},
            )
            n_lotes = random.choice([1, 1, 2, 3])
            for i in range(n_lotes):
                codigo = f"L{2024 + i}-{random.randint(100, 999)}{random.choice('ABC')}"
                if models.Lote.objects.filter(medicamento=med, codigo=codigo).exists():
                    continue
                r = random.random()
                if r < 0.15:
                    validade = date.today() - timedelta(days=random.randint(1, 90))
                elif r < 0.35:
                    validade = date.today() + timedelta(days=random.randint(1, 30))
                else:
                    validade = date.today() + timedelta(days=random.randint(60, 720))
                qr = random.random()
                if qr < 0.2:
                    qtd = random.randint(0, 5)
                elif qr < 0.4:
                    qtd = random.randint(6, 15)
                else:
                    qtd = random.randint(30, 240)
                situacao = random.choice(["RECEBIDO", "RECEBIDO", "LOTEADO", "DOADO"])
                models.Lote.objects.create(medicamento=med, codigo=codigo, validade=validade,
                                           quantidade=qtd, situacao=situacao)
        self.stdout.write(self.style.SUCCESS(
            f"Medicamentos: {models.Medicamento.objects.count()} · Lotes: {models.Lote.objects.count()}"))

        for cpf, nome, funcao, email, telefone in FUNCIONARIOS:
            models.Funcionario.objects.get_or_create(cpf=cpf, defaults={
                "nome": nome, "funcao": funcao, "email": email, "telefone": telefone})

        for modelo, ano, tipo, status in VEICULOS:
            if not models.Veiculo.objects.filter(modelo=modelo, ano=ano).exists():
                models.Veiculo.objects.create(modelo=modelo, ano=ano, tipo=tipo, status=status)

        funcs = list(models.Funcionario.objects.all())
        lotes = list(models.Lote.objects.all())
        if funcs and lotes and models.Movimentacao.objects.count() == 0:
            for _ in range(45):
                lote = random.choice(lotes); f = random.choice(funcs)
                tipo = random.choice(["ENTRADA", "SAIDA", "SAIDA"])
                qtd = random.randint(1, max(1, min(10, lote.quantidade or 1)))
                models.Movimentacao.objects.create(
                    tipo=tipo, lote=lote, funcionario=f, quantidade=qtd,
                    origem="Farmácia central" if tipo == "ENTRADA" else "",
                    destino="Viatura USB-01" if tipo == "SAIDA" else "",
                    horario=timezone.now() - timedelta(days=random.randint(0, 45), hours=random.randint(0, 23)))

        self.stdout.write(self.style.SUCCESS("Seed concluído."))
