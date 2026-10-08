import sys

p = "/root/universo/houdini/core/orchestrator.py"
s = open(p, encoding="utf-8").read()

# 1. Añadir import de ZoneInfo
s2 = s.replace(
    "import datetime\nimport asyncio",
    "import datetime\nfrom zoneinfo import ZoneInfo\nimport asyncio",
    1,
)

# 2. Cambiar la línea del now()
s3 = s2.replace(
    "        now = datetime.datetime.now()",
    '        now = datetime.datetime.now(ZoneInfo("America/Bogota"))',
    1,
)

changed = s != s3
open(p, "w", encoding="utf-8").write(s3)
print("ZONEIFIX import real:", "from zoneinfo import ZoneInfo" in s3)
print('ZONEIFIX now real:', 'now(ZoneInfo("America/Bogota"))' in s3)
print("Archivo cambiado:", changed)