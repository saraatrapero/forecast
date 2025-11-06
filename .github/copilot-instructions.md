## Propósito

Guía completa para agentes de codificación en el repositorio `forecast` - Sistema de forecasting avanzado con Next.js (frontend) + FastAPI (modelo service en Python).

## Arquitectura del Sistema

```
forecast/
├── forecast/              # Next.js App (Frontend + API Gateway)
│   ├── app/
│   │   ├── api/forecast/route.ts  # Proxy a model-service
│   │   ├── page.tsx               # UI principal
│   │   └── layout.tsx
│   ├── components/        # UI components (file-uploader, forecast-results)
│   └── Dockerfile
│
└── model-service/         # FastAPI Python Service (Modelos ML)
    ├── app/
    │   ├── main.py        # FastAPI app + endpoints
    │   ├── models/        # Prophet, SARIMAX, Holt-Winters, Ensemble
    │   └── utils/         # Clustering, survival analysis, validation
    ├── requirements.txt
    └── Dockerfile
```

### Stack Tecnológico

**Frontend (forecast/):**
- Next.js 16 (app directory)
- TypeScript
- pnpm
- Tailwind CSS
- Recharts (gráficos)
- shadcn/ui components

**Model Service (model-service/):**
- FastAPI (Python 3.11)
- Prophet (forecasting)
- statsmodels (SARIMAX)
- scikit-learn (clustering, ML)
- lifelines (survival analysis)
- XGBoost/LightGBM
- Docker

## Qué Leer Primero

1. **README_MODEL_SERVICE.md** - Arquitectura completa, API reference
2. **forecast/app/api/forecast/route.ts** - Proxy logic y fallback a v0
3. **forecast/app/page.tsx** - UI y selector de modelo
4. **model-service/app/main.py** - FastAPI endpoints y orquestación
5. **model-service/app/models/** - Implementaciones de modelos (Prophet, SARIMAX, etc.)

## Comandos Seguros y Workflows

### Desarrollo Local (Opción 1: Docker Compose - Recomendado)

```bash
# Build y run completo
docker-compose up --build

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

Acceso:
- Frontend: http://localhost:3000
- Model API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Desarrollo Local (Opción 2: Servicios Separados)

**Model Service:**
```bash
cd model-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Next.js:**
```bash
cd forecast
pnpm install
echo "MODEL_SERVICE_URL=http://localhost:8000" > .env.local
pnpm dev
```

### Testing

```bash
# Test model service
cd model-service
python tests/test_service.py

# Test Next.js
cd forecast
pnpm lint
pnpm build
pnpm start
```

### Quick Start Script

```bash
chmod +x start.sh
./start.sh
```

## Patrones y Decisiones Clave

### 1. Proxy Pattern en Next.js API Route

`forecast/app/api/forecast/route.ts` actúa como gateway:
- Si `model === 'v0'`: ejecuta algoritmo local (JavaScript heurístico)
- Si `model !== 'v0'` y `MODEL_SERVICE_URL` está configurado: reenvía a Python service
- **Fallback automático**: si Python service falla, vuelve a v0

```typescript
const modelServiceUrl = process.env.MODEL_SERVICE_URL
if (model !== "v0" && modelServiceUrl) {
  // Proxy to Python service
  const response = await fetch(`${modelServiceUrl}/predict`, {...})
  // Fallback to v0 on error
}
```

### 2. Modelos Disponibles

| Modelo | Precisión | Velocidad | Uso |
|--------|-----------|-----------|-----|
| v0 | MAPE ~25% | Muy rápido | Prototipado, fallback |
| prophet | MAPE ~15% | Medio | Estacionalidad compleja |
| sarimax | MAPE ~16% | Lento | Regresores externos |
| holtwinters | MAPE ~16% | Rápido | Smoothing clásico |
| ensemble | MAPE ~14% | Muy lento | Máxima precisión |
| ml_cluster | MAPE ~15% | Medio | Segmentación inteligente |

### 3. Features Avanzadas Implementadas

✅ **Clustering de clientes** (`app/utils/clustering.py`):
- K-means basado en RFM (Recency, Frequency, Monetary)
- Features: ventas totales, promedio, std, n_skus, recency, frequency, trend

✅ **Análisis de supervivencia** (`app/utils/survival_analysis.py`):
- Kaplan-Meier para probabilidad de continuidad
- Ajuste automático del forecast por riesgo de churn

✅ **Feature engineering** (`app/utils/feature_engineering.py`):
- Lags automáticos (1, 3, 6, 12 meses)
- Rolling windows (3, 6, 12)
- Decomposición de tendencia/estacionalidad

✅ **Validación robusta** (`app/utils/validation.py`):
- Checks de datos mínimos
- Detección de fechas inválidas

✅ **Cross-validation**:
- TimeSeriesSplit con holdout
- MAPE por horizonte (1, 3, 6 meses)

### 4. Contrato de Datos (API)

**Request a `/api/forecast` (POST):**
```json
{
  "salesData": {
    "clientes": [{
      "codigo": "CLIENT001",
      "skus": [{
        "skuId": "...",
        "ventasMes": {"2024-01": 1000, ...}
      }]
    }],
    "meses": ["2024-01", ...],
    "mesesFecha": ["2024-01-01", ...]
  },
  "forecastMonths": 6,
  "endDate": "2024-12",
  "model": "prophet",
  "options": {
    "seasonal_period": 12,
    "n_clusters": 5,
    "enable_survival": true,
    "cv_folds": 3
  }
}
```

**Response:**
```json
{
  "exitoso": true,
  "modelRequested": "prophet",
  "modelUsed": "prophet-v1",
  "summary": {
    "totalVentasHistoricas": 123456,
    "totalForecast": 145678,
    "crecimientoEsperado": 18.2,
    "clientesActivos": 234,
    "skusActivos": 1234
  },
  "graficoHistorico": [...],
  "graficoForecast": [...],
  "resultadosPorSku": [...],
  "diagnostics": {
    "training_time_s": 12.5,
    "cv_scores": {"horizon1": 15.2},
    "clusters_used": 5
  }
}
```

## Contribuciones y PRs

### Añadir un Nuevo Modelo

1. Crear `model-service/app/models/mi_modelo.py`:
```python
class MiModeloForecaster:
    def get_params(self): ...
    def forecast(self, enriched_data, forecast_months, end_date, cv_folds):
        # Return dict con estructura estándar
        return {...}
```

2. Registrar en `model-service/app/main.py`:
```python
elif model_name == "mi_modelo":
    forecaster = MiModeloForecaster()
```

3. Añadir opción en `forecast/app/page.tsx`:
```tsx
<option value="mi_modelo">Mi Modelo</option>
```

### Convenciones de Branch/PR

- Feature: `feature/nombre-corto`
- Fix: `fix/descripcion`
- Docs: `docs/actualizacion`
- PR en draft si hay dudas

### Checklist antes de PR

- [ ] `pnpm lint` (Next.js)
- [ ] `pnpm build` (Next.js)
- [ ] `python tests/test_service.py` (Model service)
- [ ] Actualizar README_MODEL_SERVICE.md si añades features
- [ ] Docker build exitoso: `docker-compose build`

## Señales de Alerta

⚠️ **No modificar** sin coordinación:
- Estructura de `app/` en Next.js (afecta routing)
- Contrato de datos entre frontend y model-service
- Versiones de Next.js (16) o React (19)
- Versiones de Prophet, statsmodels (breaking changes)

⚠️ **No añadir dependencias** sin discutir:
- Frontend: revisar bundle size
- Python: algunas librerías (TensorFlow, PyTorch) son pesadas

⚠️ **Timeout considerations**:
- Model service puede tardar >30s con muchos clientes
- Ajustar `AbortSignal.timeout` en `route.ts` si es necesario
- Considerar jobs asíncronos para datasets grandes

## Debugging Tips

### Model Service no responde
```bash
# Check logs
docker-compose logs model-service

# Test directo
curl http://localhost:8000/health

# Rebuild
docker-compose down
docker-compose up --build model-service
```

### Frontend no conecta a model service
```bash
# Verificar .env.local
cat forecast/.env.local
# Debe tener: MODEL_SERVICE_URL=http://localhost:8000

# Si usas Docker Compose, usar nombre del servicio:
# MODEL_SERVICE_URL=http://model-service:8000
```

### Forecast muy lento
- Reducir `cv_folds` a 1
- Usar `model=v0` temporalmente
- Verificar que no haya miles de SKUs por cliente

### Errores de Prophet
- Verifica que haya suficientes datos (>3 meses)
- Prophet no funciona bien con series muy cortas o con muchos ceros
- El código tiene fallback a seasonal naive automático

## Variables de Entorno

**forecast/.env.local:**
```env
MODEL_SERVICE_URL=http://localhost:8000  # local dev
# MODEL_SERVICE_URL=http://model-service:8000  # docker-compose
```

**model-service/.env (opcional):**
```env
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

## Performance y Escalabilidad

| Métrica | v0 | Prophet | Ensemble |
|---------|----|---------| ---------|
| 100 SKUs | 1s | 10s | 25s |
| 1000 SKUs | 5s | 90s | 240s |
| RAM | 50MB | 200MB | 400MB |

**Recomendaciones:**
- Para >500 clientes: considerar procesamiento asíncrono (Celery/Redis)
- Clustering reduce tiempo al agrupar clientes similares
- Cachear modelos entrenados (pickle/joblib) si entrenas periódicamente

## Recursos Adicionales

- [Prophet Docs](https://facebook.github.io/prophet/)
- [SARIMAX (statsmodels)](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js App Router](https://nextjs.org/docs/app)

## Preguntas Frecuentes

**Q: ¿Puedo añadir TensorFlow/PyTorch?**
A: Sí, pero el Docker image será mucho más pesado. Considera imagen base especializada.

**Q: ¿Cómo añado festivos españoles?**
A: En `options.holidays` pasa array de fechas ISO. Prophet los detecta automáticamente.

**Q: ¿El modelo se reentrena cada request?**
A: Sí, por ahora. Para producción, implementar caché de modelos o jobs programados.

**Q: ¿Puedo usar GPU?**
A: Para Prophet/SARIMAX no es necesario. Si añades LSTM/XGBoost profundo, configura Docker con GPU support.

---

**Última actualización:** Sistema completo con Prophet, SARIMAX, Holt-Winters, Ensemble, clustering, survival analysis y validación robusta implementados.