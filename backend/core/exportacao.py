"""Geradores de relatório em PDF e XLSX para o sistema SAMU 192."""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import models


# ---------- helpers ----------
def _coletar_dados() -> dict:
    lotes = list(models.Lote.objects.select_related("medicamento", "medicamento__tipo", "medicamento__forma"))
    veiculos = list(models.Veiculo.objects.all())
    funcionarios = list(models.Funcionario.objects.all())
    hoje = timezone.now().date()

    kpis = {
        "medicamentos": models.Medicamento.objects.count(),
        "lotes": len(lotes),
        "estoque_total": sum(l.quantidade for l in lotes),
        "baixo": sum(1 for l in lotes if l.nivel_estoque == "BAIXO"),
        "muito_baixo": sum(1 for l in lotes if l.nivel_estoque == "MUITO_BAIXO"),
        "vencendo": sum(1 for l in lotes if l.proximo_vencimento or l.vencido),
        "funcionarios": len(funcionarios),
        "veiculos": len(veiculos),
    }

    por_tipo: dict[str, int] = {}
    por_forma: dict[str, int] = {}
    for l in lotes:
        por_tipo[l.medicamento.tipo.nome] = por_tipo.get(l.medicamento.tipo.nome, 0) + l.quantidade
        por_forma[l.medicamento.forma.nome] = por_forma.get(l.medicamento.forma.nome, 0) + l.quantidade

    frota = {"NORMAL": 0, "MANUTENCAO": 0, "INATIVO": 0}
    for v in veiculos:
        frota[v.status] = frota.get(v.status, 0) + 1

    lotes.sort(key=lambda l: l.validade)
    return {
        "kpis": kpis,
        "por_tipo": sorted(por_tipo.items(), key=lambda x: -x[1]),
        "por_forma": sorted(por_forma.items(), key=lambda x: -x[1]),
        "frota": frota,
        "muito_baixo": [l for l in lotes if l.nivel_estoque == "MUITO_BAIXO"],
        "baixo": [l for l in lotes if l.nivel_estoque == "BAIXO"],
        "vencendo": [l for l in lotes if l.proximo_vencimento or l.vencido],
        "lotes": lotes,
        "funcionarios": funcionarios,
        "veiculos": veiculos,
        "hoje": hoje,
    }


# ---------- XLSX ----------
def gerar_xlsx() -> bytes:
    dados = _coletar_dados()
    wb = Workbook()

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="7F1D1D")
    title_font = Font(name="Calibri", bold=True, size=16, color="7F1D1D")
    center = Alignment(horizontal="center", vertical="center")

    # ----- Aba Resumo -----
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = "SAMU 192 · Relatório operacional"
    ws["A1"].font = title_font
    ws.merge_cells("A1:D1")
    ws["A2"] = f"Gerado em {timezone.localtime().strftime('%d/%m/%Y %H:%M')}"
    ws["A2"].font = Font(italic=True, color="525252")
    ws.merge_cells("A2:D2")

    ws["A4"] = "Indicador"
    ws["B4"] = "Valor"
    for c in ("A4", "B4"):
        ws[c].font = header_font
        ws[c].fill = header_fill
        ws[c].alignment = center

    kpi_rows = [
        ("Medicamentos cadastrados", dados["kpis"]["medicamentos"]),
        ("Lotes ativos", dados["kpis"]["lotes"]),
        ("Estoque total (unidades)", dados["kpis"]["estoque_total"]),
        ("Lotes em nível baixo", dados["kpis"]["baixo"]),
        ("Lotes muito baixos", dados["kpis"]["muito_baixo"]),
        ("Vencendo em ≤30 dias / vencidos", dados["kpis"]["vencendo"]),
        ("Funcionários", dados["kpis"]["funcionarios"]),
        ("Veículos", dados["kpis"]["veiculos"]),
    ]
    for i, (k, v) in enumerate(kpi_rows, start=5):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 16

    # ----- Aba Lotes -----
    ws2 = wb.create_sheet("Lotes")
    headers = ["Medicamento", "Complemento", "Lote", "Tipo", "Forma", "Quantidade", "Validade", "Situação", "Nível"]
    for i, h in enumerate(headers, start=1):
        c = ws2.cell(row=1, column=i, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = center
    for i, l in enumerate(dados["lotes"], start=2):
        ws2.cell(row=i, column=1, value=l.medicamento.nome)
        ws2.cell(row=i, column=2, value=l.medicamento.complemento)
        ws2.cell(row=i, column=3, value=l.codigo)
        ws2.cell(row=i, column=4, value=l.medicamento.tipo.nome)
        ws2.cell(row=i, column=5, value=l.medicamento.forma.nome)
        ws2.cell(row=i, column=6, value=l.quantidade)
        ws2.cell(row=i, column=7, value=l.validade.strftime("%d/%m/%Y"))
        ws2.cell(row=i, column=8, value=l.get_situacao_display())
        ws2.cell(row=i, column=9, value=l.nivel_estoque_label)
    for i in range(1, len(headers) + 1):
        ws2.column_dimensions[get_column_letter(i)].width = 20

    # ----- Aba Distribuições -----
    ws3 = wb.create_sheet("Distribuições")
    ws3["A1"] = "Estoque por tipo"
    ws3["A1"].font = title_font
    ws3.append(["Tipo", "Unidades"])
    for r in range(2, 3):
        for col in ("A", "B"):
            ws3[f"{col}{r}"].font = header_font
            ws3[f"{col}{r}"].fill = header_fill
    for tipo, qtd in dados["por_tipo"]:
        ws3.append([tipo, qtd])
    ws3.append([])
    ws3.append(["Estoque por forma"])
    ws3.append(["Forma", "Unidades"])
    for f, q in dados["por_forma"]:
        ws3.append([f, q])
    ws3.append([])
    ws3.append(["Frota por status"])
    ws3.append(["Status", "Total"])
    ws3.append(["Normal", dados["frota"]["NORMAL"]])
    ws3.append(["Em manutenção", dados["frota"]["MANUTENCAO"]])
    ws3.append(["Inativo", dados["frota"]["INATIVO"]])
    ws3.column_dimensions["A"].width = 28
    ws3.column_dimensions["B"].width = 14

    # ----- Aba Funcionários -----
    ws4 = wb.create_sheet("Funcionários")
    ws4.append(["Nome", "CPF", "Função", "E-mail", "Telefone"])
    for c in ws4[1]:
        c.font = header_font
        c.fill = header_fill
        c.alignment = center
    for f in dados["funcionarios"]:
        ws4.append([f.nome, f.cpf, f.get_funcao_display(), f.email, f.telefone])
    for i, w in enumerate([28, 16, 22, 30, 18], start=1):
        ws4.column_dimensions[get_column_letter(i)].width = w

    # ----- Aba Veículos -----
    ws5 = wb.create_sheet("Veículos")
    ws5.append(["ID", "Modelo", "Ano", "Status"])
    for c in ws5[1]:
        c.font = header_font
        c.fill = header_fill
        c.alignment = center
    for v in dados["veiculos"]:
        ws5.append([v.codigo_id, v.modelo, v.ano, v.get_status_display()])
    for i, w in enumerate([14, 32, 8, 16], start=1):
        ws5.column_dimensions[get_column_letter(i)].width = w

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------- PDF ----------
def gerar_pdf() -> bytes:
    dados = _coletar_dados()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Relatório SAMU 192",
        author="SAMU 192",
    )
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "titulo", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#7F1D1D"),
        alignment=0, spaceAfter=4, leading=26,
    )
    subtitulo = ParagraphStyle(
        "subtitulo", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#525252"),
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#7F1D1D"),
        spaceBefore=8, spaceAfter=6,
    )

    elementos = []
    elementos.append(Paragraph("SAMU 192 · Relatório operacional", titulo))
    elementos.append(Paragraph(
        f"Gerado em {timezone.localtime().strftime('%d/%m/%Y %H:%M')} · Unidade local", subtitulo
    ))

    # KPIs em tabela
    k = dados["kpis"]
    kpi_data = [
        ["Medicamentos", "Lotes", "Estoque total", "Baixo", "Muito baixo", "Vencendo", "Funcionários", "Veículos"],
        [k["medicamentos"], k["lotes"], k["estoque_total"], k["baixo"], k["muito_baixo"], k["vencendo"], k["funcionarios"], k["veiculos"]],
    ]
    kpi_tbl = Table(kpi_data, colWidths=[32 * mm] * 8, rowHeights=[8 * mm, 14 * mm])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF2F2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 18),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E5E5")),
    ]))
    elementos.append(kpi_tbl)
    elementos.append(Spacer(1, 8 * mm))

    # Estoque por tipo
    elementos.append(Paragraph("Estoque por tipo", h2))
    tipos_data = [["Tipo", "Unidades"]] + [[t, q] for t, q in dados["por_tipo"]]
    tipos_tbl = Table(tipos_data, colWidths=[80 * mm, 30 * mm], hAlign="LEFT")
    tipos_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D4D4D4")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    elementos.append(tipos_tbl)
    elementos.append(Spacer(1, 6 * mm))

    # Alertas: muito baixo
    elementos.append(Paragraph(f"Alertas críticos · Muito baixo ({len(dados['muito_baixo'])})", h2))
    if dados["muito_baixo"]:
        alerta_data = [["Medicamento", "Lote", "Tipo", "Qtd.", "Validade"]]
        for l in dados["muito_baixo"][:25]:
            alerta_data.append([
                l.medicamento.nome, l.codigo, l.medicamento.tipo.nome,
                str(l.quantidade), l.validade.strftime("%d/%m/%Y"),
            ])
        t = Table(alerta_data, colWidths=[80 * mm, 30 * mm, 40 * mm, 20 * mm, 30 * mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D4D4D4")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FEF2F2")]),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhum item em nível crítico. ✓", styles["Normal"]))

    elementos.append(Spacer(1, 6 * mm))

    # Vencendo
    elementos.append(Paragraph(f"Validade próxima (≤30 dias) ou vencidos ({len(dados['vencendo'])})", h2))
    if dados["vencendo"]:
        v_data = [["Medicamento", "Lote", "Quantidade", "Validade", "Situação"]]
        for l in dados["vencendo"][:25]:
            situacao = "Vencido" if l.vencido else f"{l.dias_para_validade}d restantes"
            v_data.append([
                l.medicamento.nome, l.codigo, str(l.quantidade),
                l.validade.strftime("%d/%m/%Y"), situacao,
            ])
        t = Table(v_data, colWidths=[80 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm], hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C2410C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D4D4D4")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFEDD5")]),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhum lote próximo do vencimento. ✓", styles["Normal"]))

    elementos.append(Spacer(1, 6 * mm))

    # Frota
    elementos.append(Paragraph("Frota SAMU · Status", h2))
    frota_data = [
        ["Normal", "Em manutenção", "Inativo"],
        [dados["frota"]["NORMAL"], dados["frota"]["MANUTENCAO"], dados["frota"]["INATIVO"]],
    ]
    frota_tbl = Table(frota_data, colWidths=[60 * mm, 60 * mm, 60 * mm], hAlign="LEFT")
    frota_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#DCFCE7")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFEDD5")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#FEF2F2")),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#16A34A")),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#C2410C")),
        ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor("#7F1D1D")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, 1), 22),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E5E5")),
        ("TOPPADDING", (0, 1), (-1, 1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))
    elementos.append(frota_tbl)

    doc.build(elementos)
    return buf.getvalue()
