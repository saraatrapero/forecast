#!/bin/bash

echo "🚀 Sales Forecast - Quick Start"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Por favor instala Docker primero."
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado."
    exit 1
fi

echo "✅ Docker detectado"
echo ""

# Check if .env.local exists
if [ ! -f forecast/.env.local ]; then
    echo "📝 Creando forecast/.env.local..."
    echo "MODEL_SERVICE_URL=http://model-service:8000" > forecast/.env.local
fi

echo "🔨 Building containers..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "❌ Build falló"
    exit 1
fi

echo ""
echo "🎉 Build exitoso!"
echo ""
echo "▶️  Iniciando servicios..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ No se pudieron iniciar los servicios"
    exit 1
fi

echo ""
echo "⏳ Esperando a que los servicios estén listos..."
sleep 5

# Check health
echo "🔍 Verificando servicios..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Model Service OK (http://localhost:8000)"
else
    echo "⚠️  Model Service aún iniciando..."
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Next.js Frontend OK (http://localhost:3000)"
else
    echo "⚠️  Frontend aún iniciando..."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎊 ¡Todo listo!"
echo ""
echo "📊 Frontend:     http://localhost:3000"
echo "🔧 Model API:    http://localhost:8000"
echo "📚 API Docs:     http://localhost:8000/docs"
echo ""
echo "Ver logs:"
echo "  docker-compose logs -f"
echo ""
echo "Detener:"
echo "  docker-compose down"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
