"""
FastAPI service for advanced forecasting models.
Supports Prophet, SARIMAX, XGBoost, clustering, and ensemble methods.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from models.forecaster import AdvancedForecaster
from models.clustering import ClientClusterer
from models.survival import SurvivalAnalyzer
from utils.validation import validate_sales_data
from utils.feature_engineering import FeatureEngineer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sales Forecast Service",
    description="Advanced forecasting with Prophet, SARIMAX, ML models and clustering",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SkuData(BaseModel):
    codigoCliente: str
    codigoArticulo: str
    skuId: str
    ventasMes: Dict[str, float]
    envaseDesc: Optional[str] = ""
    formatoDesc: Optional[str] = ""
    grupoMat: Optional[str] = ""
    grupoMatDesc: Optional[str] = ""
    marcaDesc: Optional[str] = ""
    materialId: Optional[str] = ""
    marcaDesglose: Optional[str] = ""
    negocioDesc: Optional[str] = ""


class ClienteData(BaseModel):
    codigo: str
    skus: List[SkuData]


class SalesData(BaseModel):
    clientes: List[ClienteData]
    meses: List[str]
    mesesFecha: List[str]
    conceptos: Optional[Dict[str, str]] = {}
    totalSkus: Optional[int] = 0


class ForecastRequest(BaseModel):
    salesData: SalesData
    forecastMonths: int = Field(ge=1, le=24, default=3)
    endDate: str
    model: str = "prophet"
    options: Optional[Dict[str, Any]] = {}


class ForecastResponse(BaseModel):
    exitoso: bool
    modelRequested: str
    modelUsed: str
    summary: Dict[str, Any]
    graficoHistorico: List[Dict[str, Any]]
    graficoForecast: List[Dict[str, Any]]
    resultadosPorSku: List[Dict[str, Any]]
    resultadosPorCliente: List[Dict[str, Any]]
    detalleCompleto: Dict[str, Any]
    diagnostics: Dict[str, Any]
    warnings: List[str] = []


@app.get("/")
async def root():
    return {
        "service": "Sales Forecast Model Service",
        "status": "running",
        "version": "1.0.0",
        "models": ["v0", "holtwinters", "prophet", "sarimax", "ml_cluster", "ensemble"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/models")
async def list_models():
    return {
        "available_models": [
            {
                "id": "v0",
                "name": "Heurístico Base (v0)",
                "description": "Modelo lineal con estacionalidad básica",
                "use_case": "Rápido, baseline"
            },
            {
                "id": "holtwinters",
                "name": "Holt-Winters",
                "description": "Triple exponential smoothing con estacionalidad",
                "use_case": "Series estacionales estables"
            },
            {
                "id": "prophet",
                "name": "Facebook Prophet",
                "description": "Tendencias no lineales + múltiples estacionalidades + eventos",
                "use_case": "Series complejas con cambios estructurales"
            },
            {
                "id": "sarimax",
                "name": "SARIMAX",
                "description": "ARIMA estacional con regresores externos",
                "use_case": "Series con variables externas conocidas"
            },
            {
                "id": "ml_cluster",
                "name": "ML por Clúster",
                "description": "XGBoost/LightGBM con clustering previo",
                "use_case": "Gran volumen de clientes con patrones heterogéneos"
            },
            {
                "id": "ensemble",
                "name": "Ensemble",
                "description": "Combinación ponderada de múltiples modelos",
                "use_case": "Máxima precisión, combina fortalezas"
            }
        ]
    }


@app.post("/predict", response_model=ForecastResponse)
async def predict(request: ForecastRequest):
    """
    Generate forecast using the specified model.
    """
    start_time = datetime.utcnow()
    warnings = []
    
    try:
        logger.info(f"Received forecast request: model={request.model}, "
                   f"clients={len(request.salesData.clientes)}, "
                   f"forecastMonths={request.forecastMonths}")
        
        # Validate input data
        validation_errors = validate_sales_data(request.salesData)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Validation errors: {validation_errors}")
        
        # Initialize forecaster
        forecaster = AdvancedForecaster(
            model_type=request.model,
            forecast_horizon=request.forecastMonths,
            options=request.options or {}
        )
        
        # Optional: cluster clients if using ml_cluster model
        if request.model == "ml_cluster":
            logger.info("Clustering clients for ML model...")
            clusterer = ClientClusterer(n_clusters=request.options.get("n_clusters", "auto"))
            cluster_assignments = clusterer.fit_predict(request.salesData)
            warnings.append(f"Clusterización: {len(set(cluster_assignments))} clusters detectados")
        else:
            cluster_assignments = None
        
        # Optional: survival analysis for churn prediction
        if request.options.get("include_survival_analysis", False):
            logger.info("Running survival analysis...")
            survival_analyzer = SurvivalAnalyzer()
            survival_probs = survival_analyzer.predict_continuity(request.salesData, request.endDate)
        else:
            survival_probs = None
        
        # Generate forecasts
        results = forecaster.forecast(
            sales_data=request.salesData,
            end_date=request.endDate,
            cluster_assignments=cluster_assignments,
            survival_probs=survival_probs
        )
        
        # Calculate metrics
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        # Build response
        response = ForecastResponse(
            exitoso=True,
            modelRequested=request.model,
            modelUsed=results["model_used"],
            summary=results["summary"],
            graficoHistorico=results["grafico_historico"],
            graficoForecast=results["grafico_forecast"],
            resultadosPorSku=results["resultados_por_sku"],
            resultadosPorCliente=results["resultados_por_cliente"],
            detalleCompleto=results["detalle_completo"],
            diagnostics={
                "training_time_s": elapsed,
                "cv_scores": results.get("cv_scores", {}),
                "model_version": results.get("model_version", "1.0.0"),
                "model_params": results.get("model_params", {}),
                "warnings": results.get("warnings", [])
            },
            warnings=warnings + results.get("warnings", [])
        )
        
        logger.info(f"Forecast completed successfully in {elapsed:.2f}s")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during forecast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing forecast: {str(e)}")


@app.post("/analyze/survival")
async def analyze_survival(request: ForecastRequest):
    """
    Run survival analysis to predict client churn probability.
    """
    try:
        analyzer = SurvivalAnalyzer()
        results = analyzer.analyze(request.salesData, request.endDate)
        return {
            "exitoso": True,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in survival analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/clusters")
async def analyze_clusters(request: ForecastRequest):
    """
    Cluster clients based on sales patterns.
    """
    try:
        clusterer = ClientClusterer(n_clusters=request.options.get("n_clusters", "auto"))
        results = clusterer.analyze(request.salesData)
        return {
            "exitoso": True,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in clustering: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
