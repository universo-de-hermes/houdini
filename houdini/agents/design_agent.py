"""
Houdini - DesignAgent
Sub-agente para generar diseños HTML con Bootstrap y adjuntarlos a correos.
"""
import os
import logging
import tempfile
from datetime import datetime
from typing import Optional

logger = logging.getLogger("houdini.agents.design")


# Templates de diseño predefinidos
TEMPLATES = {
    "report": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --powder: #B0E0E6;
            --lavender: #E6E6FA;
            --gray: #A9A9A9;
            --dark: #2D2D2D;
            --accent: #5B7B9A;
        }}
        body {{ font-family: 'Inter', sans-serif; background: #fafafa; color: var(--dark); line-height: 1.7; }}
        h1, h2, h3, h4 {{ font-family: 'Playfair Display', serif; font-weight: 700; }}
        .report-header {{ 
            background: linear-gradient(135deg, var(--powder) 0%, var(--lavender) 100%);
            padding: 60px 0 50px; position: relative; overflow: hidden;
        }}
        .report-header::after {{
            content: ''; position: absolute; bottom: 0; left: 0; right: 0;
            height: 6px; background: linear-gradient(90deg, var(--accent), var(--powder), var(--gray));
        }}
        .report-header h1 {{ font-size: 2.8rem; color: var(--dark); }}
        .report-header .lead {{ font-size: 1.1rem; color: #555; font-weight: 300; }}
        .stat-card {{
            border: 1px solid #e8e8e8; border-radius: 16px; padding: 28px;
            background: white; transition: all 0.3s ease;
            border-top: 4px solid var(--accent);
        }}
        .stat-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 40px rgba(91,123,154,0.12); }}
        .stat-number {{ font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; color: var(--accent); }}
        .content-section {{
            background: white; border-radius: 20px; padding: 40px;
            border: 1px solid #f0f0f0; box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        }}
        .footer {{
            background: var(--dark); color: var(--gray); padding: 30px 0;
            font-size: 0.85rem; letter-spacing: 0.02em;
        }}
        .footer strong {{ color: var(--powder); }}
        .divider {{ height: 2px; background: linear-gradient(90deg, var(--accent), transparent); margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="report-header">
        <div class="container">
            <h1>{title}</h1>
            {subtitle_block}
        </div>
    </div>
    <div class="container py-5">
        <div class="content-section">
            {content}
        </div>
    </div>
    <div class="footer text-center">
        <div class="container">
            <p class="mb-1">Generado por <strong>Houdini</strong></p>
            <p class="mb-0">Asistente Digital de Juan José &middot; {date}</p>
        </div>
    </div>
</body>
</html>""",

    "proposal": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --powder: #B0E0E6;
            --lavender: #E6E6FA;
            --gray: #A9A9A9;
            --dark: #2D2D2D;
            --accent: #5B7B9A;
        }}
        body {{ font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%); color: var(--dark); line-height: 1.7; min-height: 100vh; }}
        h1, h2, h3, h4 {{ font-family: 'Playfair Display', serif; font-weight: 700; }}
        .proposal-card {{
            background: white; border-radius: 24px; overflow: hidden;
            box-shadow: 0 20px 60px rgba(91,123,154,0.10);
            border: 1px solid rgba(176,224,230,0.3);
        }}
        .proposal-header {{
            padding: 50px 50px 30px;
            background: linear-gradient(135deg, var(--powder) 0%, var(--lavender) 50%, white 100%);
            border-bottom: 3px solid var(--accent);
        }}
        .proposal-header h1 {{ font-size: 2.4rem; color: var(--dark); }}
        .proposal-body {{ padding: 40px 50px 50px; }}
        .badge-accent {{ background: var(--accent); color: white; font-weight: 500; padding: 6px 18px; border-radius: 50px; font-size: 0.8rem; letter-spacing: 0.05em; }}
        .highlight-box {{
            background: linear-gradient(135deg, var(--powder) 0%, var(--lavender) 100%);
            border-radius: 16px; padding: 24px 30px; border-left: 4px solid var(--accent);
        }}
        .footer-line {{ border: none; height: 1px; background: linear-gradient(90deg, var(--accent), var(--powder), transparent); }}
    </style>
</head>
<body>
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-lg-9">
                <div class="proposal-card">
                    <div class="proposal-header">
                        <span class="badge-accent mb-3 d-inline-block">Propuesta</span>
                        <h1>{title}</h1>
                        {subtitle_block}
                    </div>
                    <div class="proposal-body">
                        {content}
                        <hr class="footer-line my-4">
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">{date}</small>
                            <small class="text-muted">Generado por <strong style="color:var(--accent)">Houdini</strong></small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>""",

    "summary": """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --powder: #B0E0E6;
            --lavender: #E6E6FA;
            --gray: #A9A9A9;
            --dark: #2D2D2D;
            --accent: #5B7B9A;
        }}
        body {{ font-family: 'Inter', sans-serif; background: white; color: var(--dark); line-height: 1.8; }}
        h1, h2, h3 {{ font-family: 'Playfair Display', serif; font-weight: 700; color: var(--dark); }}
        h1 {{ font-size: 2.2rem; margin-bottom: 0.5rem; }}
        .doc {{ max-width: 800px; margin: 0 auto; padding: 50px 30px; }}
        .doc-header {{
            padding-bottom: 25px; margin-bottom: 35px;
            border-bottom: 3px solid var(--powder);
        }}
        .doc-header .meta {{ color: var(--gray); font-size: 0.9rem; }}
        .accent-line {{ 
            width: 60px; height: 4px; background: var(--accent); 
            border-radius: 4px; margin: 20px 0 25px;
        }}
        .doc-footer {{
            margin-top: 50px; padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 0.85rem; color: var(--gray);
        }}
        .tag {{
            display: inline-block; background: var(--lavender); color: var(--dark);
            padding: 3px 14px; border-radius: 50px; font-size: 0.75rem;
            font-weight: 500; letter-spacing: 0.03em;
        }}
    </style>
</head>
<body>
    <div class="doc">
        <div class="doc-header">
            <span class="tag mb-3">Resumen</span>
            <h1>{title}</h1>
            {subtitle_block}
            <div class="meta">{date}</div>
        </div>
        <div class="accent-line"></div>
        <div class="content">
            {content}
        </div>
        <div class="doc-footer text-center">
            Generado por <strong style="color:var(--accent)">Houdini</strong> &middot; Asistente Digital de Juan José
        </div>
    </div>
</body>
</html>""",
}

# Helper to format subtitle
def _format_subtitle(subtitle: str) -> str:
    if subtitle:
        return f'<p class="lead" style="font-family:\'Inter\',sans-serif;font-weight:300;color:#555">{subtitle}</p>'
    return ""


class DesignAgent:
    """Sub-agente para generar archivos HTML con diseño Bootstrap."""

    def __init__(self):
        self.output_dir = os.path.join(tempfile.gettempdir(), "houdini_designs")
        os.makedirs(self.output_dir, exist_ok=True)

    def create_html(self, params) -> dict:
        """
        Genera un archivo HTML con diseño Bootstrap.
        
        Args:
            params: CreateHTMLInput con title, content_html, template, subtitle, filename
        
        Returns:
            dict con la ruta del archivo y metadatos
        """
        if params.template not in TEMPLATES:
            return {"error": f"Plantilla no disponible. Opciones: {list(TEMPLATES.keys())}"}

        today = datetime.now().strftime("%d/%m/%Y %H:%M")
        subtitle_block = _format_subtitle(params.subtitle or "")

        html = TEMPLATES[params.template].format(
            title=params.title,
            content=params.content_html,
            subtitle_block=subtitle_block,
            date=today,
        )

        if not params.filename:
            sanitized = params.title.lower().replace(" ", "_").replace("ñ", "n")[:30]
            filename = f"{sanitized}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        else:
            filename = params.filename
        if not filename.endswith(".html"):
            filename += ".html"

        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"HTML generado: {filepath} (plantilla: {params.template})")
        return {
            "filepath": filepath,
            "filename": filename,
            "template": params.template,
            "size_bytes": os.path.getsize(filepath),
            "status": "created",
        }

    def list_templates(self, params=None) -> dict:
        """Lista las plantillas disponibles con descripción."""
        return {
            "templates": {
                "report": "Reporte ejecutivo con header degradado y sección de contenido tipo tarjeta - ideal para informes y resúmenes",
                "proposal": "Propuesta elegante estilo carta con badge y diseño centrado - perfecto para propuestas comerciales",
                "summary": "Documento limpio tipo artículo con línea decorativa - ideal para ensayos, análisis y documentos formales",
            }
        }