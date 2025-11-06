# 🚀 Quick Reference - Comandos Útiles

## Inicio Rápido

```bash
# Setup completo con Docker
./start.sh

# Verificar implementación
./verify.sh
```

## Docker Commands

```bash
# Build y start
docker-compose up --build

# Start en background
docker-compose up -d

# Ver logs
docker-compose logs -f
docker-compose logs -f model-service
docker-compose logs -f nextjs

# Stop
docker-compose down

# Rebuild solo un servicio
docker-compose up --build model-service

# Ver estado
docker-compose ps
```

## Development Local

### Model Service (Python)

```bash
cd model-service

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run con logs detallados
uvicorn app.main:app --reload --log-level debug
```

### Next.js Frontend

```bash
cd forecast

# Install
pnpm install

# Setup env
echo "MODEL_SERVICE_URL=http://localhost:8000" > .env.local

# Dev
pnpm dev

# Build
pnpm build

# Production
pnpm start

# Lint
pnpm lint
```

## Testing

```bash
# Test model service (requiere que esté corriendo)
cd model-service
python tests/test_service.py

# Test individual model
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @tests/sample_request.json

# Health check
curl http://localhost:8000/health
curl http://localhost:8000/

# Test con different models
# Prophet
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"salesData": {...}, "model": "prophet", "forecastMonths": 6, "endDate": "2024-12"}'

# SARIMAX
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
  -d '{"salesData": {...}, "model": "sarimax", "forecastMonths": 6, "endDate": "2024-12"}'
```

## Debugging

```bash
# Ver logs en tiempo real
docker-compose logs -f --tail=100

# Entrar al container
docker-compose exec model-service bash
docker-compose exec nextjs sh

# Ver variables de entorno
docker-compose exec model-service env
docker-compose exec nextjs env

# Restart un servicio
docker-compose restart model-service
docker-compose restart nextjs
```

## URLs Importantes

```
Frontend:        http://localhost:3000
Model API:       http://localhost:8000
API Docs:        http://localhost:8000/docs
Redoc:           http://localhost:8000/redoc
Health Check:    http://localhost:8000/health
```

## Archivo de Configuración

### forecast/.env.local
```env
MODEL_SERVICE_URL=http://localhost:8000          # Local dev
# MODEL_SERVICE_URL=http://model-service:8000    # Docker Compose
```

### model-service/.env (opcional)
```env
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
```

## Troubleshooting Rápido

```bash
# Model service no responde
docker-compose logs model-service | tail -50
docker-compose restart model-service

# Frontend no conecta
cat forecast/.env.local
docker-compose restart nextjs

# Puerto ocupado
docker-compose down
lsof -ti:3000 | xargs kill -9  # Matar proceso en puerto 3000
lsof -ti:8000 | xargs kill -9  # Matar proceso en puerto 8000

# Limpiar todo y empezar de nuevo
docker-compose down -v
docker system prune -a
docker-compose up --build
```

## Desarrollo de Modelos

### Añadir nuevo modelo

1. Crear `model-service/app/models/mi_modelo.py`
2. Implementar class `MiModeloForecaster` con método `forecast()`
3. Registrar en `model-service/app/main.py`
4. Añadir en dropdown de `forecast/app/page.tsx`

### Testing local de modelo

```python
# model-service/test_my_model.py
from app.models.mi_modelo import MiModeloForecaster

forecaster = MiModeloForecaster()
result = forecaster.forecast(data, 6, "2024-12", 3)
print(result)
```

## Performance Profiling

```bash
# Time de request
time curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @model-service/tests/sample_request.json

# Monitor recursos
docker stats

# Memory usage
docker stats --format "table {{.Name}}\t{{.MemUsage}}"
```

## Backup y Restore

```bash
# Backup de modelos entrenados (si implementado)
docker cp model-service:/app/cache ./backup_cache

# Restore
docker cp ./backup_cache model-service:/app/cache
```

## Git Workflow

```bash
# Crear feature branch
git checkout -b feature/mi-feature

# Commit changes
git add .
git commit -m "feat: añadir mi feature"

# Push
git push origin feature/mi-feature

# Merge a main (después de PR aprobado)
git checkout main
git pull
git merge feature/mi-feature
git push
```

## Checklist Pre-Deploy

- [ ] `./verify.sh` pasa
- [ ] `docker-compose up --build` funciona
- [ ] `pnpm lint` sin errores
- [ ] `python tests/test_service.py` pasa
- [ ] Variables de entorno configuradas
- [ ] Documentación actualizada
- [ ] Tests añadidos para nuevas features

---

**Pro tip:** Guarda este archivo en favoritos para acceso rápido a comandos comunes.
