# Model Service - Advanced Forecasting

FastAPI service for advanced sales forecasting with Prophet, SARIMAX, ML models, clustering, and survival analysis.

## Features

- **Multiple Models**: Prophet, Holt-Winters, SARIMAX, XGBoost, Ensemble
- **Client Clustering**: Automatic segmentation based on sales patterns
- **Survival Analysis**: Churn prediction and continuity probability
- **Feature Engineering**: Advanced lag features, rolling statistics, seasonality
- **Robust Validation**: Input validation and error handling

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

Service will be available at `http://localhost:8000`

### Docker

```bash
# Build image
docker build -t forecast-model-service .

# Run container
docker run -p 8000:8000 forecast-model-service
```

### Docker Compose (with Next.js frontend)

```bash
# From project root
docker-compose up
```

## API Endpoints

### Health Check
```
GET /health
```

### List Available Models
```
GET /models
```

### Generate Forecast
```
POST /predict
Content-Type: application/json

{
  "salesData": { ... },
  "forecastMonths": 6,
  "endDate": "2024-09",
  "model": "prophet",
  "options": {
    "include_survival_analysis": true,
    "n_clusters": "auto"
  }
}
```

### Survival Analysis
```
POST /analyze/survival
```

### Client Clustering
```
POST /analyze/clusters
```

## Model Selection Guide

| Model | Best For | Pros | Cons |
|-------|----------|------|------|
| **v0** | Baseline/Fast | Simple, fast | Limited accuracy |
| **holtwinters** | Stable seasonality | Good for regular patterns | Needs 12+ periods |
| **prophet** | Complex patterns | Handles trends, events, holidays | Slower training |
| **sarimax** | With external data | Supports regressors | Requires tuning |
| **ml_cluster** | Large datasets | Captures non-linear patterns | Needs more data |
| **ensemble** | Maximum accuracy | Combines strengths | Slowest, most compute |

## Configuration

Environment variables:
- `LOG_LEVEL`: Logging level (default: INFO)
- `WORKERS`: Number of Uvicorn workers (default: 2)
- `PORT`: Service port (default: 8000)

## Response Format

```json
{
  "exitoso": true,
  "modelRequested": "prophet",
  "modelUsed": "prophet",
  "summary": {
    "totalVentasHistoricas": 12345.67,
    "totalForecast": 14000.00,
    "crecimientoEsperado": 13.5,
    "clientesActivos": 42,
    "clientesTotales": 50,
    "skusActivos": 320
  },
  "graficoHistorico": [...],
  "graficoForecast": [...],
  "resultadosPorSku": [...],
  "resultadosPorCliente": [...],
  "detalleCompleto": {...},
  "diagnostics": {
    "training_time_s": 12.3,
    "cv_scores": {...},
    "model_version": "1.1.5",
    "model_params": {...}
  },
  "warnings": []
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format
black .

# Lint
flake8 .

# Type check
mypy .
```

## Performance Tips

1. **Use clustering** for large client bases (>1000 clients)
2. **Choose appropriate model** based on data volume
3. **Enable caching** for repeated forecasts
4. **Use ensemble** only when accuracy is critical
5. **Monitor memory** with Prophet on large datasets

## Troubleshooting

### Prophet fails to install
- Ensure `gcc` and `g++` are installed
- Use pre-built wheels: `pip install prophet --find-links https://github.com/facebook/prophet/releases`

### SARIMAX slow convergence
- Reduce `maxiter` in options
- Use simpler ARIMA order
- Check for stationarity

### Memory issues
- Reduce workers
- Use v0 or holtwinters for large datasets
- Process clients in batches

## License

MIT
