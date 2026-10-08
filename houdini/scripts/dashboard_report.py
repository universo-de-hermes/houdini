"""
Houdini - Generador de Reporte Dashboard Membresías VIP v2
Calcula los KPIs desde la hoja Ventas (data real) y genera HTML profesional.
"""
import asyncio
import io
import os
import sys
import logging
import tempfile
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.oauth import GoogleOAuth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from agents.design_agent import DesignAgent
from agents.gmail_agent import GmailAgent
from schemas.tools import CreateHTMLInput, SendEmailInput
import openpyxl

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("houdini.dashboard")

# Configuración
SPREADSHEET_FILE_ID = "1-LrFtiMDIuMqXF7hTSnOEO_k-XGCitdF"
DEFAULT_RECIPIENT = "jhotas96@gmail.com"


def num(v, default=0):
    try:
        if v is None:
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def money(v):
    return f"${num(v):,.0f}"


def download_excel(creds) -> bytes:
    """Descarga el Excel desde Google Drive."""
    drive = build("drive", "v3", credentials=creds)
    request = drive.files().get_media(fileId=SPREADSHEET_FILE_ID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.getvalue()


def analyze_ventas(rows):
    """Analiza la hoja Ventas y calcula todos los KPIs."""
    total_membresias = 0
    valor_vendido = 0.0
    count_3m = 0
    count_6m = 0
    count_pagadas = 0
    count_anuladas = 0

    por_asesora = defaultdict(lambda: {"ventas": 0, "valor": 0.0, "m3": 0, "m6": 0})
    por_sede = defaultdict(lambda: {"ventas": 0, "valor": 0.0, "m3": 0, "m6": 0})

    for row in rows:
        # Solo contar filas con datos reales (fecha de venta o cliente)
        if not row or len(row) < 9:
            continue
        fecha = row[0]
        cliente = str(row[2] or "").strip()
        if not fecha and not cliente:
            continue

        asesora = str(row[1] or "").strip()
        sede = str(row[5] or "").strip()
        membresia = str(row[6] or "").strip()
        valor = num(row[7])
        estado = str(row[8] or "").strip()

        if estado.lower() == "anulado":
            count_anuladas += 1
            continue

        total_membresias += 1
        valor_vendido += valor
        if "6" in membresia:
            count_6m += 1
        else:
            count_3m += 1
        if estado.lower() == "pagado":
            count_pagadas += 1

        if asesora:
            a = por_asesora[asesora]
            a["ventas"] += 1
            a["valor"] += valor
            if "6" in membresia:
                a["m6"] += 1
            else:
                a["m3"] += 1
        if sede:
            s = por_sede[sede]
            s["ventas"] += 1
            s["valor"] += valor
            if "6" in membresia:
                s["m6"] += 1
            else:
                s["m3"] += 1

    ticket_promedio = valor_vendido / total_membresias if total_membresias else 0

    return {
        "total_membresias": total_membresias,
        "valor_vendido": valor_vendido,
        "count_3m": count_3m,
        "count_6m": count_6m,
        "count_pagadas": count_pagadas,
        "count_anuladas": count_anuladas,
        "ticket_promedio": ticket_promedio,
        "por_asesora": dict(por_asesora),
        "por_sede": dict(por_sede),
    }


def build_dashboard_html(ventas_rows) -> str:
    """Genera un HTML completo, standalone y profesional."""
    d = analyze_ventas(ventas_rows)
    asesoras = sorted(d["por_asesora"].items(), key=lambda x: x[1]["valor"], reverse=True)
    sedes = sorted(d["por_sede"].items(), key=lambda x: x[1]["valor"], reverse=True)
    total_valor = d["valor_vendido"] or 1

    # Filas de asesoras
    filas_asesoras = ""
    for name, a in asesoras:
        pct = (a["valor"] / total_valor) * 100
        filas_asesoras += f"""
        <tr>
            <td style="font-weight:600;padding:8px 12px;border-bottom:1px solid #e8e8e8">{name}</td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{a['m3']}</td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{a['m6']}</td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8"><span class="badge">{a['ventas']}</span></td>
            <td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;font-weight:500">{money(a['valor'])}</td>
            <td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;color:#888">{pct:.1f}%</td>
        </tr>"""

    filas_sedes = ""
    for name, s in sedes:
        pct = (s["valor"] / total_valor) * 100
        filas_sedes += f"""
        <tr>
            <td style="font-weight:600;padding:8px 12px;border-bottom:1px solid #e8e8e8">{name}</td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8"><span class="badge">{s['ventas']}</span></td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{s['m3']}</td>
            <td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{s['m6']}</td>
            <td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;font-weight:500">{money(s['valor'])}</td>
            <td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;color:#888">{pct:.1f}%</td>
        </tr>"""

    fecha_reporte = __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Membresias VIP</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; background:#f5f6fa; color:#2d2d2d; line-height:1.6; }}
.header {{ background:linear-gradient(135deg,#B0E0E6 0%,#E6E6FA 50%,#d4d4f0 100%); padding:40px 20px 30px; position:relative; }}
.header::after {{ content:''; position:absolute; bottom:0; left:0; right:0; height:5px; background:linear-gradient(90deg,#5B7B9A,#B0E0E6,#A9A9A9); }}
.header h1 {{ font-size:clamp(1.5rem,4vw,2.2rem); color:#2d2d2d; text-align:center; }}
.header p {{ text-align:center; color:#666; margin-top:6px; font-size:0.9rem; }}
.container {{ max-width:960px; margin:0 auto; padding:20px 16px; }}
.kpi-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:24px; }}
.kpi-card {{ background:white; border-radius:14px; padding:20px 16px; text-align:center; border-top:4px solid #5B7B9A; box-shadow:0 2px 12px rgba(0,0,0,0.06); }}
.kpi-num {{ font-size:clamp(1.4rem,3vw,2rem); font-weight:700; color:#5B7B9A; }}
.kpi-label {{ font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.04em; margin-top:4px; }}
.section {{ background:white; border-radius:16px; padding:20px; margin-bottom:20px; box-shadow:0 2px 12px rgba(0,0,0,0.06); }}
.section h2 {{ font-size:1.1rem; color:#2d2d2d; margin-bottom:16px; padding-bottom:10px; border-bottom:2px solid #B0E0E6; }}
table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
thead th {{ background:#f8f9fc; padding:10px 12px; text-align:left; font-weight:600; color:#555; border-bottom:2px solid #B0E0E6; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.03em; }}
.badge {{ display:inline-block; background:#5B7B9A; color:white; font-size:0.75rem; font-weight:600; padding:2px 10px; border-radius:20px; }}
.footer {{ text-align:center; padding:20px; color:#A9A9A9; font-size:0.8rem; border-top:1px solid #e8e8e8; margin-top:10px; }}
.footer strong {{ color:#5B7B9A; }}
@media (max-width:600px) {{
    .kpi-row {{ grid-template-columns:repeat(2,1fr); gap:8px; }}
    .kpi-card {{ padding:14px 10px; }}
    table {{ font-size:0.75rem; }}
    thead th, td {{ padding:6px 8px !important; }}
    .section {{ padding:14px !important; }}
    .header {{ padding:25px 14px 20px; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>Dashboard Membresias VIP</h1>
    <p>Reporte Ejecutivo &middot; {fecha_reporte}</p>
</div>
<div class="container">

    <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-num">{d['total_membresias']}</div><div class="kpi-label">Total Membresias</div></div>
        <div class="kpi-card"><div class="kpi-num">{money(d['valor_vendido'])}</div><div class="kpi-label">Valor Vendido</div></div>
        <div class="kpi-card"><div class="kpi-num">{d['count_3m']}</div><div class="kpi-label">Membresias 3 Meses</div></div>
        <div class="kpi-card"><div class="kpi-num">{d['count_6m']}</div><div class="kpi-label">Membresias 6 Meses</div></div>
    </div>

    <div class="kpi-row">
        <div class="kpi-card"><div class="kpi-num">{d['count_pagadas']}</div><div class="kpi-label">Pagos Completados</div></div>
        <div class="kpi-card"><div class="kpi-num">{money(d['ticket_promedio'])}</div><div class="kpi-label">Ticket Promedio</div></div>
        <div class="kpi-card"><div class="kpi-num">{d['count_anuladas']}</div><div class="kpi-label">Ventas Anuladas</div></div>
    </div>

    <div class="section">
        <h2>Ventas por Asesora</h2>
        <div style="overflow-x:auto">
        <table>
            <thead><tr><th>Asesora</th><th style="text-align:center">3 Meses</th><th style="text-align:center">6 Meses</th><th style="text-align:center">Total</th><th style="text-align:right">Valor</th><th style="text-align:right">%</th></tr></thead>
            <tbody>{filas_asesoras}</tbody>
        </table>
        </div>
    </div>

    <div class="section">
        <h2>Ventas por Sede</h2>
        <div style="overflow-x:auto">
        <table>
            <thead><tr><th>Sede</th><th style="text-align:center">Membresias</th><th style="text-align:center">3 Meses</th><th style="text-align:center">6 Meses</th><th style="text-align:right">Valor</th><th style="text-align:right">%</th></tr></thead>
            <tbody>{filas_sedes}</tbody>
        </table>
        </div>
    </div>

</div>
<div class="footer">
    Generado por <strong>Houdini</strong> &middot; Asistente Digital de Juan Jose
</div>
</body>
</html>"""
    return html


async def send_dashboard_report(recipient: str = DEFAULT_RECIPIENT) -> dict:
    """Flujo completo: descarga → analiza Ventas → genera HTML → envía."""
    logger.info("📥 Descargando Excel desde Drive...")
    oauth = GoogleOAuth()
    creds = oauth.get_credentials()
    excel_bytes = download_excel(creds)
    logger.info("✅ Excel descargado")

    logger.info("📊 Analizando datos de Ventas...")
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
    ws = wb["Ventas"]
    ventas_rows = list(ws.iter_rows(min_row=2, values_only=True))
    total_registros = len([r for r in ventas_rows if r and r[0]])
    logger.info(f"✅ {total_registros} registros de ventas")

    logger.info("🎨 Generando HTML profesional...")
    content = build_dashboard_html(ventas_rows)
    # Calcular resumen
    resumen = analyze_ventas(ventas_rows)

    # Guardar HTML directo (sin DesignAgent, ya es completo)
    import tempfile
    out_dir = os.path.join(tempfile.gettempdir(), "houdini_designs")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"dashboard_membresias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"✅ HTML generado: {filename}")

    logger.info(f"📧 Enviando correo a {recipient}...")
    gmail = GmailAgent(credentials=creds)
    result = await gmail.send_email(SendEmailInput(
        to=recipient,
        subject="Dashboard Membresías VIP - Reporte Ejecutivo",
        body=(
            "Jefe, aquí tiene el reporte ejecutivo del dashboard de membresías VIP.\n\n"
            f"Resumen: {resumen['total_membresias']} membresías por {money(resumen['valor_vendido'])} "
            f"con ticket promedio de {money(resumen['ticket_promedio'])}.\n\n"
            "Adjunto el reporte completo en HTML."
        ),
        attachments=[filepath],
    ))
    logger.info(f"✅ Correo enviado: {result.get('status', result)}")
    return result


if __name__ == "__main__":
    recipient = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RECIPIENT
    result = asyncio.run(send_dashboard_report(recipient))
    print(result)
