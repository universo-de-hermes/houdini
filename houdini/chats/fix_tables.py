# -*- coding: utf-8 -*-
"""Añade un convertidor de tablas-pipe a texto legible dentro de clean_markdown."""

path = "/root/universo/houdini/agents/telegram_agent.py"
s = open(path, encoding="utf-8").read()

# --- Función convertidora de tablas, insertada justo antes de clean_markdown ---
tables_fn = '''def _tables_to_plain(text: str) -> str:
    """Convierte tablas markdown de pipes (| a | b |) a líneas legibles.

    Formato de entrada (típico del LLM):
        | Hora | Evento |
        |---|---|
        | 3:00 PM | Agendado por houdini |
    Salida legible en Telegram:
        Hora: 3:00 PM
        Evento: Agendado por houdini
        (cada fila -> 'key: value')
    """
    lines = text.split("\\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detectar una línea de tabla: contiene múltiples pipes '|'
        if line.count("|") >= 2 and "|" in line:
            block = []
            while i < len(lines) and lines[i].count("|") >= 2:
                block.append(lines[i])
                i += 1
            out.append(_render_table_block(block))
            continue
        out.append(line)
        i += 1
    return "\\n".join(out)


def _render_table_block(block):
    """Convierte el bloque de líneas pipe en líneas sencillas key: value."""
    parsed = []
    for line in block:
        raw = line.strip()
        # quitar el '|' inicial y final
        if raw.startswith("|"):
            raw = raw[1:]
        if raw.endswith("|"):
            raw = raw[:-1]
        # separar por pipes
        cells = [c.strip() for c in raw.split("|")]
        cells = [c for c in cells if c and c.strip("-") and c.strip(":")]  # ignora el separador |---|
        if cells:
            parsed.append(cells)

    if not parsed:
        return ""

    header = parsed[0]
    rows = parsed[1:]
    rendered = []

    if rows and len(rows[0]) == len(header) and all(r[0] != "-" for r in rows):
        # Tabla con cabecera: filas -> "Header: valor"
        for row in rows:
            pairs = " · ".join(f"{h}: {v}" for h, v in zip(header, row) if h and v)
            rendered.append(f"• {pairs}")
    else:
        # Tabla sin cabecera clara: una fila -> "v1: v2" (o solo lista)
        for row in rows:
            if len(row) >= 2 and all(x != "-" for x in row):
                rendered.append(f"• {row[0]}: {row[1]}")
            else:
                rendered.append(f"• {' · '.join(x for x in row if x)}")

    if not rendered:
        return ""

    # encabezado como título si no es un separador
    head_txt = ""
    if len(header) == 1 and header[0] not in ("", "-", "---"):
        head_txt = header[0].rstrip(":") + ": "
    return head_txt + "\\n" + "\\n".join(rendered)


'''

# 1. Insertar las funciones antes de clean_markdown
anchor = "def clean_markdown(text: str) -> str:"
if "_tables_to_plain" not in s:
    s = s.replace(anchor, tables_fn + anchor, 1)

# 2. Añadir la llamada dentro de clean_markdown, al inicio
old_first = 'def clean_markdown(text: str) -> str:\n    """Elimina todo formato Markdown: asteriscos, numerales, underscores, etc."""'
new_first = 'def clean_markdown(text: str) -> str:\n    """Elimina todo formato Markdown: asteriscos, numerales, underscores, etc."""\n    # Convertir tablas pipe a texto legible ANTES de limpiar\n    text = _tables_to_plain(text)'
if "_tables_to_plain(text)" not in s.split("clean_markdown")[1][:200]:
    s = s.replace(old_first, new_first, 1)

open(path, "w", encoding="utf-8").write(s)

print("Tablas insertadas:", "_tables_to_plain" in s)
print("Llamada añadida:", "_tables_to_plain(text)" in s)