#!/usr/bin/env bash
# =============================================
# Houdini - Script de Parada
# =============================================
echo "🎩 Deteniendo Houdini..."

# Detener PostgreSQL
docker compose stop postgres

echo "✅ Houdini detenido"
