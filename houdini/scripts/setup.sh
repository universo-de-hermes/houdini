#!/usr/bin/env bash
# =============================================
# Houdini - Script de Inicialización
# Ejecutar una sola vez para setup completo
# =============================================
set -e

echo "🎩 Houdini - Setup inicial"
echo "============================"

# 1. Verificar .env
if [ ! -f .env ]; then
    echo "📋 Creando .env desde .env.example..."
    cp .env.example .env
    echo "⚠️  Edita .env con tus claves API antes de continuar."
    echo "   - OPENROUTER_API_KEY"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET"
    exit 1
fi

echo "✅ .env encontrado"

# 2. Levantar PostgreSQL
echo ""
echo "🗄️  Levantando PostgreSQL + pgvector..."
docker compose up -d postgres
echo "⏳ Esperando que PostgreSQL esté listo..."
sleep 5
docker compose exec postgres pg_isready -U houdini -d houdini_db
echo "✅ PostgreSQL listo"

# 3. Instalar dependencias Python
echo ""
echo "📦 Instalando dependencias Python..."
pip install -r requirements.txt
echo "✅ Dependencias instaladas"

# 4. Verificar Google OAuth
if [ ! -f config/google_client_secret.json ]; then
    echo ""
    echo "⚠️  Falta config/google_client_secret.json"
    echo "   Descárgalo desde Google Cloud Console:"
    echo "   https://console.cloud.google.com/apis/credentials"
    echo "   Crea un OAuth 2.0 Client ID (tipo: Desktop app)"
    echo "   y guarda el archivo como config/google_client_secret.json"
fi

echo ""
echo "🎩 Setup completo! Para iniciar Houdini:"
echo "   python main.py"
