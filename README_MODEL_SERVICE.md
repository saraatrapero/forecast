# Sales Forecast - Modelo Service

Sistema completo de forecasting de ventas con modelos avanzados.

## Arquitectura

```
┌─────────────┐         ┌──────────────┐
│   Next.js   │────────▶│ Model Service│
│  (Frontend) │◀────────│   (Python)   │
│   Port 3000 │         │   Port 8000  │
└─────────────┘         └──────────────┘
```

## Modelos Disponibles

1. **v0** (JavaScript nativo) - Heurístico rápido con estacionalidad
2. **Prophet** - Modelo de Facebook para series temporales con tendencias y estacionalidad
3. **SARIMAX** - ARIMA estacional con regresores externos
4. **Holt-Winters** - Exponential Smoothing clásico
5. **Ensemble** - Combinación ponderada de múltiples modelos
6. **ML Cluster** - Machine Learning por clústeres de clientes

## Features Avanzadas

- ✅ **Clustering de clientes** (K-means basado en RFM y tendencias)
- ✅ **Análisis de supervivencia** (Kaplan-Meier para predecir churn)
- ✅ **Feature engineering** temporal (lags, rolling windows)
- ✅ **Cross-validation** robusto para estimar MAPE
- ✅ **Forecast probabilístico** (P10, P50, P90)
- ✅ **Fallback automático** a v0 si el servicio Python falla

## Inicio Rápido

### Opción 1: Docker Compose (Recomendado)

```bash
# Build y run completo
docker-compose up --build

# Accede a:
# - Frontend: http://localhost:3000
# - Model Service API: http://localhost:8000
# - Docs API: http://localhost:8000/docs
```

### Opción 2: Local Development

#### 1. Model Service (Python)

```bash
cd model-service

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Next.js Frontend

```bash
cd forecast

# Instalar dependencias
pnpm install

# Configurar variable de entorno
echo "MODEL_SERVICE_URL=http://localhost:8000" > .env.local

# Run dev server
pnpm dev
```

## Testing

### Test Model Service

```bash
# Health check
curl http://localhost:8000/health

# Test Prophet model
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @model-service/tests/sample_request.json
```

### Test Frontend

```bash
cd forecast
pnpm lint
pnpm build
```

## Configuración

### Variables de Entorno

#### Next.js (`forecast/.env.local`)
```env
MODEL_SERVICE_URL=http://localhost:8000
```

#### Model Service (opcional, `model-service/.env`)
```env
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

## API Reference

### POST /predict

**Request Body:**
```json
{
  "salesData": {
    "clientes": [...],
    "meses": ["2024-01", "2024-02", ...],
    "mesesFecha": ["2024-01-01", ...],
    "conceptos": {...}
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
    "totalVentasHistoricas": 1234567,
    "totalForecast": 1456789,
    "crecimientoEsperado": 18.2,
    "clientesActivos": 234,
    "skusActivos": 1234
  },
  "graficoHistorico": [...],
  "graficoForecast": [...],
  "resultadosPorSku": [...],
  "resultadosPorCliente": [...],
  "diagnostics": {
    "training_time_s": 12.5,
    "cv_scores": {"horizon1": 15.2, "horizon3": 18.5},
    "model_version": "1.0.0",
    "clusters_used": 5
  },
  "warnings": [...]
}
```

## Desarrollo

### Añadir un Nuevo Modelo

1. Crear `model-service/app/models/mi_modelo.py`:
```python
class MiModeloForecaster:
    def forecast(self, enriched_data, forecast_months, end_date, cv_folds):
        # Implementar lógica
        return result_dict
```

2. Registrar en `model-service/app/main.py`:
```python
elif model_name == "mi_modelo":
    forecaster = MiModeloForecaster()
```

3. Añadir en el dropdown de `forecast/app/page.tsx`:
```tsx
<option value="mi_modelo">Mi Modelo</option>
```

## Troubleshooting

### Error: "Cannot find module 'next/server'"
```bash
cd forecast
pnpm install
```

### Error: "Model service timeout"
- Aumenta el timeout en `route.ts` (línea `AbortSignal.timeout`)
- Verifica que el servicio Python esté corriendo
- Revisa logs: `docker-compose logs model-service`

### Forecast muy lento
- Reduce `cv_folds` a 1 o 2
- Usa `model=v0` para prototipar rápido
- Considera clustering para reducir modelos

## Performance

| Modelo | Precisión (MAPE) | Tiempo (100 SKUs) | RAM |
|--------|------------------|-------------------|-----|
| v0 | ~25% | 1s | 50MB |
| Prophet | ~15% | 10s | 200MB |
| SARIMAX | ~16% | 15s | 250MB |
| Ensemble | ~14% | 25s | 400MB |

## Contribuir

1. Fork el repo
2. Crea una branch: `git checkout -b feature/mi-feature`
3. Commit: `git commit -am 'Add mi feature'`
4. Push: `git push origin feature/mi-feature`
5. Abre un Pull Request

## License

MIT
