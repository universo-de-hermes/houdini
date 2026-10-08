#!/usr/bin/env bash
# =============================================
# Houdini - Script de Inicio
# =============================================
set -e

echo "🎩 Iniciando Houdini..."

# Verificar que PostgreSQL esté corriendo
if ! docker compose ps postgres | grep -q "Up"; then
    echo "🗄️  Levantando PostgreSQL..."
    docker compose up -d postgres
    sleep 3
fi

# Iniciar Houdini
python main.py
