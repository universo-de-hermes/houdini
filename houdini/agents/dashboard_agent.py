"""
Houdini - DashboardAgent
Genera y envía el reporte de Dashboard Membresías VIP desde Telegram.
"""
import asyncio
import io
import os
import logging
import tempfile
from datetime import datetime
from collections import defaultdict

from services.oauth import GoogleOAuth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from agents.gmail_agent import GmailAgent
from schemas.tools import SendEmailInput
import openpyxl

logger = logging.getLogger("houdini.agents.dashboard")

SPREADSHEET_FILE_ID = "1-LrFtiMDIuMqXF7hTSnOEO_k-XGCitdF"
DEFAULT_RECIPIENT = "jhotas96@gmail.com"


def num(v, default=0):
    try:
        if v is None: return default
        return float(v)
    except: return default


def money(v):
    return f"${num(v):,.0f}"


class DashboardAgent:
    """Sub-agente para generar y enviar reportes del Dashboard."""

    async def send_dashboard(self, params) -> dict:
        """
        Genera el reporte del dashboard y lo envía por correo.
        params: SendDashboardInput con recipient_email (opcional)
        """
        recipient = getattr(params, 'recipient_email', None) or DEFAULT_RECIPIENT
        logger.info(f"📊 Generando dashboard para {recipient}...")

        # 1. Descargar Excel
        oauth = GoogleOAuth()
        creds = oauth.get_credentials()
        drive = build("drive", "v3", credentials=creds)
        request = drive.files().get_media(fileId=SPREADSHEET_FILE_ID)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)

        # 2. Analizar datos
        wb = openpyxl.load_workbook(io.BytesIO(fh.read()), data_only=True)
        ws = wb["Ventas"]
        ventas_rows = list(ws.iter_rows(min_row=2, values_only=True))
        d = self._analyze(ventas_rows)

        # 3. Generar HTML
        html = self._build_html(d)

        # 4. Guardar archivo
        out_dir = os.path.join(tempfile.gettempdir(), "houdini_designs")
        os.makedirs(out_dir, exist_ok=True)
        filename = f"dashboard_membresias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        # 5. Enviar correo
        gmail = GmailAgent(credentials=creds)
        result = await gmail.send_email(SendEmailInput(
            to=recipient,
            subject="Dashboard Membresias VIP - Reporte Ejecutivo",
            body=(
                f"Jefe, aqui tiene el reporte ejecutivo del dashboard.\n\n"
                f"Resumen: {d['total_membresias']} membresias por {money(d['valor_vendido'])} "
                f"con ticket promedio de {money(d['ticket_promedio'])}.\n\n"
                "Adjunto el reporte completo en HTML."
            ),
            attachments=[filepath],
        ))

        return {
            "status": "sent",
            "recipient": recipient,
            "summary": f"{d['total_membresias']} membresias, {money(d['valor_vendido'])} vendido",
        }

    def _analyze(self, rows):
        d = {"total_membresias": 0, "valor_vendido": 0.0, "count_3m": 0, "count_6m": 0,
             "count_pagadas": 0, "count_anuladas": 0, "ticket_promedio": 0,
             "por_asesora": {}, "por_sede": {}}
        por_asesora = defaultdict(lambda: {"ventas": 0, "valor": 0.0, "m3": 0, "m6": 0})
        por_sede = defaultdict(lambda: {"ventas": 0, "valor": 0.0, "m3": 0, "m6": 0})

        for row in rows:
            if not row or len(row) < 9: continue
            if not row[0] and not str(row[2] or "").strip(): continue
            asesora = str(row[1] or "").strip()
            sede = str(row[5] or "").strip()
            membresia = str(row[6] or "").strip()
            valor = num(row[7])
            estado = str(row[8] or "").strip()
            if estado.lower() == "anulado":
                d["count_anuladas"] += 1; continue
            d["total_membresias"] += 1
            d["valor_vendido"] += valor
            if "6" in membresia: d["count_6m"] += 1
            else: d["count_3m"] += 1
            if estado.lower() == "pagado": d["count_pagadas"] += 1
            if asesora:
                a = por_asesora[asesora]; a["ventas"] += 1; a["valor"] += valor
                if "6" in membresia: a["m6"] += 1
                else: a["m3"] += 1
            if sede:
                s = por_sede[sede]; s["ventas"] += 1; s["valor"] += valor
                if "6" in membresia: s["m6"] += 1
                else: s["m3"] += 1

        d["ticket_promedio"] = d["valor_vendido"] / d["total_membresias"] if d["total_membresias"] else 0
        d["por_asesora"] = dict(por_asesora)
        d["por_sede"] = dict(por_sede)
        return d

    def _build_html(self, d):
        asesoras = sorted(d["por_asesora"].items(), key=lambda x: x[1]["valor"], reverse=True)
        sedes = sorted(d["por_sede"].items(), key=lambda x: x[1]["valor"], reverse=True)
        total_valor = d["valor_vendido"] or 1

        fa = ""
        for name, a in asesoras:
            pct = (a["valor"] / total_valor) * 100
            fa += f'<tr><td style="font-weight:600;padding:8px 12px;border-bottom:1px solid #e8e8e8">{name}</td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{a["m3"]}</td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{a["m6"]}</td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8"><span class="badge">{a["ventas"]}</span></td><td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;font-weight:500">{money(a["valor"])}</td><td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;color:#888">{pct:.1f}%</td></tr>'

        fs = ""
        for name, s in sedes:
            pct = (s["valor"] / total_valor) * 100
            fs += f'<tr><td style="font-weight:600;padding:8px 12px;border-bottom:1px solid #e8e8e8">{name}</td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8"><span class="badge">{s["ventas"]}</span></td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{s["m3"]}</td><td style="text-align:center;padding:8px 12px;border-bottom:1px solid #e8e8e8">{s["m6"]}</td><td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;font-weight:500">{money(s["valor"])}</td><td style="text-align:right;padding:8px 12px;border-bottom:1px solid #e8e8e8;color:#888">{pct:.1f}%</td></tr>'

        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Dashboard Membresias VIP</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#f5f6fa;color:#2d2d2d;line-height:1.6}}
.header{{background:linear-gradient(135deg,#B0E0E6 0%,#E6E6FA 50%,#d4d4f0 100%);padding:40px 20px 30px;position:relative}}
.header::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:5px;background:linear-gradient(90deg,#5B7B9A,#B0E0E6,#A9A9A9)}}
.header h1{{font-size:clamp(1.5rem,4vw,2.2rem);color:#2d2d2d;text-align:center}}
.header p{{text-align:center;color:#666;margin-top:6px;font-size:.9rem}}
.container{{max-width:960px;margin:0 auto;padding:20px 16px}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}}
.kpi-card{{background:#fff;border-radius:14px;padding:20px 16px;text-align:center;border-top:4px solid #5B7B9A;box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.kpi-num{{font-size:clamp(1.4rem,3vw,2rem);font-weight:700;color:#5B7B9A}}
.kpi-label{{font-size:.75rem;color:#888;text-transform:uppercase;letter-spacing:.04em;margin-top:4px}}
.section{{background:#fff;border-radius:16px;padding:20px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.section h2{{font-size:1.1rem;color:#2d2d2d;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #B0E0E6}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
thead th{{background:#f8f9fc;padding:10px 12px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #B0E0E6;font-size:.75rem;text-transform:uppercase;letter-spacing:.03em}}
.badge{{display:inline-block;background:#5B7B9A;color:#fff;font-size:.75rem;font-weight:600;padding:2px 10px;border-radius:20px}}
.footer{{text-align:center;padding:20px;color:#A9A9A9;font-size:.8rem;border-top:1px solid #e8e8e8;margin-top:10px}}
.footer strong{{color:#5B7B9A}}
@media(max-width:600px){{.kpi-row{{grid-template-columns:repeat(2,1fr);gap:8px}}.kpi-card{{padding:14px 10px}}table{{font-size:.75rem}}thead th,td{{padding:6px 8px !important}}.section{{padding:14px !important}}.header{{padding:25px 14px 20px}}}}
</style></head><body>
<div class="header"><h1>Dashboard Membresias VIP</h1><p>Reporte Ejecutivo &middot; {fecha}</p></div>
<div class="container">
<div class="kpi-row"><div class="kpi-card"><div class="kpi-num">{d['total_membresias']}</div><div class="kpi-label">Total Membresias</div></div><div class="kpi-card"><div class="kpi-num">{money(d['valor_vendido'])}</div><div class="kpi-label">Valor Vendido</div></div><div class="kpi-card"><div class="kpi-num">{d['count_3m']}</div><div class="kpi-label">Membresias 3 Meses</div></div><div class="kpi-card"><div class="kpi-num">{d['count_6m']}</div><div class="kpi-label">Membresias 6 Meses</div></div></div>
<div class="kpi-row"><div class="kpi-card"><div class="kpi-num">{d['count_pagadas']}</div><div class="kpi-label">Pagos Completados</div></div><div class="kpi-card"><div class="kpi-num">{money(d['ticket_promedio'])}</div><div class="kpi-label">Ticket Promedio</div></div><div class="kpi-card"><div class="kpi-num">{d['count_anuladas']}</div><div class="kpi-label">Ventas Anuladas</div></div></div>
<div class="section"><h2>Ventas por Asesora</h2><div style="overflow-x:auto"><table><thead><tr><th>Asesora</th><th style="text-align:center">3 Meses</th><th style="text-align:center">6 Meses</th><th style="text-align:center">Total</th><th style="text-align:right">Valor</th><th style="text-align:right">%</th></tr></thead><tbody>{fa}</tbody></table></div></div>
<div class="section"><h2>Ventas por Sede</h2><div style="overflow-x:auto"><table><thead><tr><th>Sede</th><th style="text-align:center">Membresias</th><th style="text-align:center">3 Meses</th><th style="text-align:center">6 Meses</th><th style="text-align:right">Valor</th><th style="text-align:right">%</th></tr></thead><tbody>{fs}</tbody></table></div></div>
</div>
<div class="footer">Generado por <strong>Houdini</strong> &middot; Asistente Digital de Juan Jose</div>
</body></html>"""