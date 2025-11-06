"""
FastAPI Main Application - Sales Forecast Model Service
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import time

from app.models.prophet_model import ProphetForecaster
from app.models.sarimax_model import SARIMAXForecaster
from app.models.holtwinters_model import HoltWintersForecaster
from app.models.ensemble_model import EnsembleForecaster
from app.utils.clustering import CustomerClusterer
from app.utils.feature_engineering import FeatureEngineer
from app.utils.survival_analysis import SurvivalAnalyzer
from app.utils.validation import TimeSeriesValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sales Forecast Model Service",
    description="Advanced forecasting models with clustering and survival analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SkuData(BaseModel):
    skuId: str
    codigoCliente: str
    codigoArticulo: str
    ventasMes: Dict[str, float]
    grupoMatDesc: Optional[str] = None
    marcaDesc: Optional[str] = None
    negocioDesc: Optional[str] = None

class ClienteData(BaseModel):
    codigo: str
    skus: List[SkuData]

class SalesData(BaseModel):
    clientes: List[ClienteData]
    meses: List[str]
    mesesFecha: List[str]
    conceptos: Optional[Dict[str, str]] = None
    totalSkus: Optional[int] = None

class ForecastOptions(BaseModel):
    seasonal_period: Optional[int] = 12
    holidays: Optional[List[str]] = None
    cluster_method: Optional[str] = "kmeans"
    n_clusters: Optional[int] = 5
    enable_survival: Optional[bool] = True
    enable_changepoints: Optional[bool] = False
    cv_folds: Optional[int] = 3

class ForecastRequest(BaseModel):
    salesData: SalesData
    forecastMonths: int = Field(ge=1, le=24)
    endDate: str
    model: str = "prophet"
    regressors: Optional[Dict[str, Any]] = None
    options: Optional[ForecastOptions] = ForecastOptions()

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
    warnings: Optional[List[str]] = []

@app.get("/")
async def root():
    return {
        "service": "Sales Forecast Model Service",
        "version": "1.0.0",
        "status": "running",
        "models": ["prophet", "sarimax", "holtwinters", "ensemble", "ml_cluster"]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/predict", response_model=ForecastResponse)
async def predict_forecast(request: ForecastRequest):
    """
    Main forecast endpoint - routes to appropriate model
    """
    start_time = time.time()
    logger.info(f"Forecast request: model={request.model}, months={request.forecastMonths}")
    
    try:
        # Extract data
        sales_data = request.salesData
        forecast_months = request.forecastMonths
        end_date = request.endDate
        model_name = request.model
        options = request.options or ForecastOptions()
        
        # Validate input
        validator = TimeSeriesValidator()
        validation_result = validator.validate_data(sales_data, end_date)
        if not validation_result["valid"]:
            raise HTTPException(status_code=400, detail=validation_result["errors"])
        
        warnings = []
        
        # Feature engineering
        feature_engineer = FeatureEngineer()
        enriched_data = feature_engineer.enrich_data(sales_data, end_date)
        
        # Clustering (if enabled for ml_cluster model)
        clusters = None
        if model_name == "ml_cluster" or options.n_clusters:
            logger.info("Performing customer clustering...")
            clusterer = CustomerClusterer(n_clusters=options.n_clusters or 5)
            clusters = clusterer.fit_predict(sales_data, end_date)
            warnings.append(f"Clientes agrupados en {len(set(clusters.values()))} clusters")
        
        # Survival analysis (if enabled)
        survival_probs = None
        if options.enable_survival:
            logger.info("Computing survival probabilities...")
            survival_analyzer = SurvivalAnalyzer()
            survival_probs = survival_analyzer.compute_survival_probabilities(
                sales_data, end_date, forecast_months
            )
            warnings.append("Probabilidades de supervivencia aplicadas")
        
        # Select and run model
        if model_name == "prophet":
            forecaster = ProphetForecaster(
                seasonal_period=options.seasonal_period,
                holidays=options.holidays
            )
        elif model_name == "sarimax":
            forecaster = SARIMAXForecaster(
                seasonal_period=options.seasonal_period
            )
        elif model_name == "holtwinters":
            forecaster = HoltWintersForecaster(
                seasonal_period=options.seasonal_period
            )
        elif model_name == "ensemble":
            forecaster = EnsembleForecaster(
                models=["prophet", "sarimax", "holtwinters"],
                weights=[0.4, 0.3, 0.3]
            )
        elif model_name == "ml_cluster":
            # Use ensemble with cluster-specific models
            forecaster = EnsembleForecaster(
                models=["prophet", "xgboost"],
                weights=[0.5, 0.5],
                clusters=clusters
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        
        # Run forecast
        logger.info(f"Running {model_name} forecast...")
        forecast_result = forecaster.forecast(
            enriched_data,
            forecast_months,
            end_date,
            cv_folds=options.cv_folds
        )
        
        # Apply survival probabilities if available
        if survival_probs:
            forecast_result = apply_survival_adjustment(
                forecast_result, survival_probs, forecast_months
            )
        
        # Build response
        training_time = time.time() - start_time
        
        response = ForecastResponse(
            exitoso=True,
            modelRequested=model_name,
            modelUsed=f"{model_name}-v1",
            summary=forecast_result["summary"],
            graficoHistorico=forecast_result["graficoHistorico"],
            graficoForecast=forecast_result["graficoForecast"],
            resultadosPorSku=forecast_result["resultadosPorSku"],
            resultadosPorCliente=forecast_result["resultadosPorCliente"],
            detalleCompleto=forecast_result["detalleCompleto"],
            diagnostics={
                "training_time_s": round(training_time, 2),
                "cv_scores": forecast_result.get("cv_scores", {}),
                "model_version": "1.0.0",
                "model_params": forecaster.get_params(),
                "clusters_used": len(set(clusters.values())) if clusters else None,
                "survival_analysis": options.enable_survival
            },
            warnings=warnings
        )
        
        logger.info(f"Forecast completed in {training_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def apply_survival_adjustment(
    forecast_result: Dict[str, Any],
    survival_probs: Dict[str, List[float]],
    forecast_months: int
) -> Dict[str, Any]:
    """Apply survival probability adjustment to forecasts"""
    for sku in forecast_result["resultadosPorSku"]:
        sku_id = sku["skuId"]
        if sku_id in survival_probs and "forecast_detalle" in sku:
            for i in range(min(len(sku["forecast_detalle"]), forecast_months)):
                if i < len(survival_probs[sku_id]):
                    sku["forecast_detalle"][i] *= survival_probs[sku_id][i]
            # Update first forecast value
            if sku["forecast_detalle"]:
                sku["forecast"] = sku["forecast_detalle"][0]
    
    return forecast_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
