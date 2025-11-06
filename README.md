# # Sales Forecast Application - Documentación Completa

Sistema completo de forecasting de ventas con modelos avanzados (Prophet, SARIMAX, ML clustering) y análisis de supervivencia.

## 🎯 Características Principales

### Frontend (Next.js + TypeScript)
- ✅ Carga de archivos Excel con validación robusta
- ✅ Selector de modelo de forecasting
- ✅ Visualización interactiva de resultados (histórico + forecast)
- ✅ Dashboard con KPIs (ventas, crecimiento, cartera activa)
- ✅ Descarga de resultados en Excel
- ✅ Tema oscuro con Tailwind CSS

### Backend - Servicio de Modelado (Python + FastAPI)
- ✅ **6 modelos disponibles**: v0 (baseline), Holt-Winters, Prophet, SARIMAX, ML cluster, Ensemble
- ✅ **Clustering inteligente**: segmentación automática de clientes
- ✅ **Survival Analysis**: predicción de churn y probabilidad de continuidad
- ✅ **Feature Engineering**: lags, rolling stats, estacionalidad, trends
- ✅ **Validación robusta**: input validation y manejo de errores
- ✅ **Métricas detalladas**: MAPE, CV scores, diagnósticos de entrenamiento

## 📦 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     USUARIO                                  │
│                        ↓                                     │
│              ┌─────────────────────┐                        │
│              │   Next.js Frontend  │                        │
│              │   (Port 3000)       │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │   API Route         │                        │
│              │   /api/forecast     │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│           ┌─────────────┴──────────────┐                   │
│           │ model != "v0"?             │                    │
│           │                            │                    │
│      YES  ▼                            ▼  NO                │
│  ┌─────────────────┐         ┌─────────────────┐          │
│  │  Python Service │         │  v0 (JS native) │          │
│  │  Prophet/SARIMAX│         │  Baseline model │          │
│  │  ML/Clustering  │         └─────────────────┘          │
│  │  (Port 8000)    │                                       │
│  └─────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Setup y Deployment

### Opción 1: Docker Compose (Recomendado)

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd forecast

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Construir y ejecutar con Docker Compose
docker-compose up --build

# Acceder a:
# - Frontend: http://localhost:3000
# - Model Service: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Opción 2: Desarrollo Local

#### Frontend (Next.js)

```bash
cd forecast

# Instalar dependencias
pnpm install

# Desarrollo
pnpm dev

# Build para producción
pnpm build
pnpm start
```

#### Model Service (Python)

```bash
cd model-service

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
python main.py

# O con Uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Configurar integración

```bash
# En el directorio forecast/, crear .env.local
echo "MODEL_SERVICE_URL=http://localhost:8000" > .env.local
```

## 📊 Uso de la Aplicación

### 1. Preparar el Excel

Formato requerido:
- **Fila 1**: Conceptos (ej: "Ventas", "Presupuesto")
- **Fila 2**: Fechas (formatos soportados: YYYY-MM, MM-YYYY, DD/MM/YYYY, etc.)
- **Columna A** (desde fila 3): Código Cliente+Artículo (28 chars cliente + 7 chars artículo)
- **Columnas B-I**: Metadatos (envase, formato, grupo material, marca, etc.)
- **Columnas J en adelante**: Datos de ventas por mes

### 2. Cargar y Configurar

1. Arrastra el Excel o haz clic para seleccionar
2. Selecciona la **fecha de corte** (último mes a analizar)
3. Elige el **modelo de forecasting**:
   - **v0 (Automático)**: Rápido, baseline heurístico
   - **Holt-Winters**: Suavizado exponencial triple (bueno para estacionalidad estable)
   - **Prophet**: Facebook Prophet (tendencias no lineales, eventos, holidays)
   - **SARIMAX**: ARIMA estacional con regresores externos
   - **ML Cluster**: XGBoost con clustering previo (gran volumen)
   - **Ensemble**: Combinación ponderada de múltiples modelos (máxima precisión)
4. Ajusta **meses a pronosticar** (1-24 meses)
5. Haz clic en **"Generar Forecast"**

### 3. Analizar Resultados

La aplicación muestra:
- **KPIs principales**: Venta real, forecast, crecimiento, cartera activa
- **Gráfico histórico**: Ventas pasadas con días hábiles
- **Gráfico forecast**: Proyección futura
- **Top 10 SKUs**: Ordenados por forecast
- **Detalle por cliente**: Ventas, forecast, variación, SKUs activos
- **Insights y recomendaciones**: Análisis automático de salud de cartera

### 4. Descargar Resultados

Haz clic en **"Descargar Excel"** para obtener un archivo con:
- Hoja 1: Forecast por SKU (con detalle mensual)
- Hoja 2: Forecast por Cliente
- Hoja 3: Resumen general y métricas

## 🧪 Testing

### Servicio Python

```bash
cd model-service

# Test manual con script de prueba
python test_service.py

# Con pytest (si instalado)
pytest tests/ -v

# Test de un modelo específico
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Frontend

```bash
cd forecast

# Lint
pnpm lint

# Build test
pnpm build
```

## 🔧 Configuración Avanzada

### Variables de Entorno

#### Frontend (.env.local)
```env
MODEL_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:3000
NODE_ENV=development
```

#### Model Service (.env)
```env
LOG_LEVEL=INFO
WORKERS=2
PORT=8000
```

### Opciones de Modelos

Al llamar a `/predict`, puedes pasar opciones específicas:

```json
{
  "model": "prophet",
  "options": {
    "include_survival_analysis": true,
    "n_clusters": "auto",
    "seasonal_period": 12,
    "holidays": ["ES-2024-12-25"],
    "changepoint_prior_scale": 0.05
  }
}
```

## 📈 Comparativa de Modelos

| Modelo | Velocidad | Precisión | Datos Mínimos | Uso Recomendado |
|--------|-----------|-----------|---------------|-----------------|
| **v0** | ⚡⚡⚡⚡⚡ | ⭐⭐ | 2 períodos | Baseline rápido |
| **Holt-Winters** | ⚡⚡⚡⚡ | ⭐⭐⭐ | 12 períodos | Estacionalidad regular |
| **Prophet** | ⚡⚡⚡ | ⭐⭐⭐⭐ | 10+ períodos | Tendencias complejas |
| **SARIMAX** | ⚡⚡ | ⭐⭐⭐⭐ | 24+ períodos | Con regresores externos |
| **ML Cluster** | ⚡⚡⚡ | ⭐⭐⭐⭐ | 12+ períodos | Gran volumen clientes |
| **Ensemble** | ⚡ | ⭐⭐⭐⭐⭐ | 12+ períodos | Máxima precisión |

## 🐛 Troubleshooting

### Prophet no se instala

```bash
# En Ubuntu/Debian
sudo apt-get install gcc g++ python3-dev

# En macOS
brew install gcc

# Reinstalar
pip install --no-cache-dir prophet
```

### Timeout en requests grandes

Ajustar timeout en `forecast/app/api/forecast/route.ts`:
```typescript
signal: AbortSignal.timeout(180000), // 3 minutos
```

### Error "Cannot find module 'next/server'"

```bash
cd forecast
pnpm install
```

### Model service no responde

```bash
# Verificar salud
curl http://localhost:8000/health

# Ver logs
docker-compose logs model-service

# Reiniciar
docker-compose restart model-service
```

## 🔐 Seguridad y Producción

### Recomendaciones para Producción

1. **Usar HTTPS** en ambos servicios
2. **Añadir autenticación** (JWT, API keys)
3. **Rate limiting** en endpoints
4. **Validación estricta** de tamaño de archivos
5. **Logs centralizados** (ej: ELK stack)
6. **Monitoreo** (Prometheus + Grafana)
7. **Backup** de modelos entrenados

### Deployment en Cloud

#### Vercel (Frontend)
```bash
cd forecast
vercel deploy
```

#### AWS/Azure/GCP (Model Service)
```bash
# Dockerizar y subir a registry
docker build -t forecast-model-service:latest model-service/
docker tag forecast-model-service:latest <registry>/forecast-model-service:latest
docker push <registry>/forecast-model-service:latest

# Desplegar en Kubernetes/ECS/Cloud Run
```

## 📝 Roadmap y Mejoras Futuras

- [ ] Pipeline automático (Airflow/Prefect) para reentrenamiento
- [ ] Explainability con SHAP para interpretar predicciones
- [ ] Detección de cambios estructurales (ruptures, change points)
- [ ] Forecast probabilístico (P10, P50, P90)
- [ ] A/B testing de modelos
- [ ] Cache de predicciones
- [ ] Dashboard de monitoring de modelos
- [ ] Integración con fuentes externas (clima, festivos, IPC)

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -am 'Add nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

## 📄 Licencia

MIT

## 📧 Soporte

Para issues y preguntas: abrir un issue en el repositorio de GitHub.

---

**¡Listo para generar forecasts precisos! 🚀📊**
