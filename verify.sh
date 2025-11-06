#!/bin/bash
# Quick verification script to check implementation

echo "🔍 Verificación de Implementación"
echo "=================================="
echo ""

# Check directory structure
echo "📁 Verificando estructura de directorios..."
dirs=(
    "model-service"
    "model-service/app"
    "model-service/app/models"
    "model-service/app/utils"
    "model-service/tests"
    "forecast/app/api/forecast"
)

for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (FALTA)"
    fi
done

echo ""
echo "📄 Verificando archivos clave..."

files=(
    "model-service/app/main.py"
    "model-service/app/models/prophet_model.py"
    "model-service/app/models/sarimax_model.py"
    "model-service/app/models/holtwinters_model.py"
    "model-service/app/models/ensemble_model.py"
    "model-service/app/utils/clustering.py"
    "model-service/app/utils/survival_analysis.py"
    "model-service/app/utils/feature_engineering.py"
    "model-service/app/utils/validation.py"
    "model-service/requirements.txt"
    "model-service/Dockerfile"
    "model-service/tests/test_service.py"
    "model-service/tests/sample_request.json"
    "forecast/Dockerfile"
    "forecast/app/api/forecast/route.ts"
    "forecast/app/page.tsx"
    "docker-compose.yml"
    "start.sh"
    "README_MODEL_SERVICE.md"
    "IMPLEMENTATION_SUMMARY.md"
    ".github/copilot-instructions.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (FALTA)"
    fi
done

echo ""
echo "🔧 Verificando dependencias Python..."
if [ -f "model-service/requirements.txt" ]; then
    echo "  Paquetes principales:"
    grep -E "(fastapi|prophet|statsmodels|scikit-learn|lifelines)" model-service/requirements.txt | sed 's/^/    ✅ /'
fi

echo ""
echo "📦 Verificando configuración Next.js..."
if [ -f "forecast/package.json" ]; then
    echo "  ✅ package.json encontrado"
    if grep -q "next" forecast/package.json; then
        echo "  ✅ Next.js configurado"
    fi
fi

echo ""
echo "🐳 Verificando Docker..."
if command -v docker &> /dev/null; then
    echo "  ✅ Docker instalado: $(docker --version)"
else
    echo "  ⚠️  Docker no encontrado"
fi

if command -v docker-compose &> /dev/null; then
    echo "  ✅ Docker Compose instalado"
else
    echo "  ⚠️  Docker Compose no encontrado"
fi

echo ""
echo "=================================="
echo "✅ Verificación completa!"
echo ""
echo "Siguiente paso:"
echo "  ./start.sh"
echo ""
