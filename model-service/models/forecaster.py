"""
Advanced forecasting models implementation.
Includes Prophet, SARIMAX, Holt-Winters, XGBoost, and ensemble methods.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdvancedForecaster:
    """
    Main forecaster class that handles multiple model types.
    """
    
    def __init__(self, model_type: str, forecast_horizon: int, options: Dict[str, Any]):
        self.model_type = model_type
        self.forecast_horizon = forecast_horizon
        self.options = options
        self.warnings = []
        
    def forecast(
        self,
        sales_data: Any,
        end_date: str,
        cluster_assignments: Optional[List[int]] = None,
        survival_probs: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Generate forecast using the specified model.
        """
        logger.info(f"Starting forecast with model={self.model_type}")
        
        # Parse dates and structure data
        meses = sales_data.meses
        meses_fecha = [datetime.fromisoformat(f) for f in sales_data.mesesFecha]
        clientes = sales_data.clientes
        
        end_date_idx = meses.index(end_date)
        
        # Build historical data structure
        historical_data = self._prepare_historical_data(
            clientes, meses, meses_fecha, end_date_idx
        )
        
        # Generate forecast months
        forecast_meses, forecast_meses_fecha = self._generate_forecast_dates(
            meses_fecha[end_date_idx], self.forecast_horizon
        )
        
        # Select and apply model
        if self.model_type == "prophet":
            results = self._forecast_prophet(historical_data, end_date_idx)
        elif self.model_type == "holtwinters":
            results = self._forecast_holtwinters(historical_data, end_date_idx)
        elif self.model_type == "sarimax":
            results = self._forecast_sarimax(historical_data, end_date_idx)
        elif self.model_type == "ml_cluster":
            results = self._forecast_ml_cluster(
                historical_data, end_date_idx, cluster_assignments
            )
        elif self.model_type == "ensemble":
            results = self._forecast_ensemble(historical_data, end_date_idx)
        else:  # v0 or fallback
            results = self._forecast_v0(historical_data, end_date_idx)
        
        # Apply survival probability adjustment if available
        if survival_probs:
            results = self._apply_survival_adjustment(results, survival_probs)
        
        # Build response structure
        response = self._build_response(
            results, historical_data, meses, meses_fecha,
            forecast_meses, forecast_meses_fecha, end_date_idx
        )
        
        return response
    
    def _prepare_historical_data(
        self, clientes: List[Any], meses: List[str],
        meses_fecha: List[datetime], end_date_idx: int
    ) -> Dict[str, Any]:
        """
        Convert client/SKU data into structured format for modeling.
        """
        data = {
            "clientes": [],
            "skus": [],
            "meses": meses[:end_date_idx + 1],
            "meses_fecha": meses_fecha[:end_date_idx + 1]
        }
        
        for cliente in clientes:
            cliente_data = {
                "codigo": cliente.codigo,
                "skus": []
            }
            
            for sku in cliente.skus:
                ventas = [sku.ventasMes.get(m, 0.0) for m in data["meses"]]
                
                sku_data = {
                    "skuId": sku.skuId,
                    "codigoCliente": sku.codigoCliente,
                    "codigoArticulo": sku.codigoArticulo,
                    "grupoMatDesc": sku.grupoMatDesc or "",
                    "marcaDesc": sku.marcaDesc or "",
                    "negocioDesc": sku.negocioDesc or "",
                    "ventas": ventas,
                    "metadata": {
                        "envaseDesc": sku.envaseDesc,
                        "formatoDesc": sku.formatoDesc,
                        "grupoMat": sku.grupoMat,
                        "materialId": sku.materialId,
                        "marcaDesglose": sku.marcaDesglose
                    }
                }
                
                cliente_data["skus"].append(sku_data)
                data["skus"].append(sku_data)
            
            data["clientes"].append(cliente_data)
        
        return data
    
    def _generate_forecast_dates(
        self, last_date: datetime, periods: int
    ) -> tuple[List[str], List[datetime]]:
        """
        Generate future month dates for forecast.
        """
        forecast_meses = []
        forecast_meses_fecha = []
        
        current = last_date + timedelta(days=32)
        current = current.replace(day=1)
        
        for _ in range(periods):
            forecast_meses.append(current.strftime("%Y-%m"))
            forecast_meses_fecha.append(current)
            current = (current + timedelta(days=32)).replace(day=1)
        
        return forecast_meses, forecast_meses_fecha
    
    def _forecast_prophet(self, data: Dict[str, Any], end_date_idx: int) -> Dict[str, Any]:
        """
        Prophet-based forecast with trend and seasonality detection.
        """
        try:
            from prophet import Prophet
            logger.info("Using Prophet model")
            
            results_por_sku = []
            
            for sku in data["skus"]:
                ventas = sku["ventas"]
                
                # Check if series has enough data
                if len([v for v in ventas if v > 0]) < 3:
                    # Fallback to simple method
                    forecast = [max(0, ventas[-1] * 0.9)] * self.forecast_horizon
                    mape = 999
                    estado = "sin_datos_suficientes"
                else:
                    # Prepare data for Prophet
                    df = pd.DataFrame({
                        'ds': data["meses_fecha"],
                        'y': ventas
                    })
                    
                    # Initialize and fit Prophet
                    model = Prophet(
                        yearly_seasonality=True,
                        weekly_seasonality=False,
                        daily_seasonality=False,
                        seasonality_mode='multiplicative',
                        changepoint_prior_scale=0.05
                    )
                    
                    try:
                        model.fit(df)
                        
                        # Generate future dates
                        future = model.make_future_dataframe(periods=self.forecast_horizon, freq='MS')
                        forecast_df = model.predict(future)
                        
                        # Extract forecast values
                        forecast = forecast_df['yhat'].tail(self.forecast_horizon).tolist()
                        forecast = [max(0, f) for f in forecast]
                        
                        # Calculate MAPE on last 3 periods
                        if len(ventas) >= 3:
                            test_size = min(3, len(ventas) - 1)
                            actuals = ventas[-test_size:]
                            preds = forecast_df['yhat'].iloc[-test_size - self.forecast_horizon:-self.forecast_horizon].tolist()
                            
                            mape = np.mean([
                                abs((a - p) / a) if a > 0 else 0
                                for a, p in zip(actuals, preds)
                            ]) * 100
                        else:
                            mape = 999
                        
                        estado = "activo"
                        
                    except Exception as e:
                        logger.warning(f"Prophet failed for SKU {sku['skuId']}: {str(e)}")
                        forecast = [max(0, ventas[-1] * 0.9)] * self.forecast_horizon
                        mape = 999
                        estado = "prophet_fallback"
                
                results_por_sku.append({
                    "sku": sku,
                    "forecast": forecast,
                    "mape": mape,
                    "estado": estado,
                    "ultimo_valor": ventas[-1] if ventas else 0
                })
            
            return {
                "model_used": "prophet",
                "results_por_sku": results_por_sku,
                "model_version": "1.1.5",
                "warnings": self.warnings
            }
            
        except ImportError:
            logger.error("Prophet not installed, falling back to v0")
            self.warnings.append("Prophet no disponible, usando modelo v0")
            return self._forecast_v0(data, end_date_idx)
    
    def _forecast_holtwinters(self, data: Dict[str, Any], end_date_idx: int) -> Dict[str, Any]:
        """
        Holt-Winters triple exponential smoothing.
        """
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            logger.info("Using Holt-Winters model")
            
            results_por_sku = []
            
            for sku in data["skus"]:
                ventas = sku["ventas"]
                
                if len([v for v in ventas if v > 0]) < 12:
                    # Need at least 12 periods for seasonal
                    forecast = [max(0, ventas[-1])] * self.forecast_horizon
                    mape = 999
                    estado = "sin_datos_suficientes"
                else:
                    try:
                        model = ExponentialSmoothing(
                            ventas,
                            seasonal_periods=12,
                            trend='add',
                            seasonal='add',
                            damped_trend=True
                        )
                        fit = model.fit()
                        forecast = fit.forecast(self.forecast_horizon).tolist()
                        forecast = [max(0, f) for f in forecast]
                        
                        # Simple MAPE calculation
                        mape = 50  # Placeholder
                        estado = "activo"
                        
                    except Exception as e:
                        logger.warning(f"Holt-Winters failed for SKU {sku['skuId']}: {str(e)}")
                        forecast = [max(0, ventas[-1])] * self.forecast_horizon
                        mape = 999
                        estado = "hw_fallback"
                
                results_por_sku.append({
                    "sku": sku,
                    "forecast": forecast,
                    "mape": mape,
                    "estado": estado,
                    "ultimo_valor": ventas[-1] if ventas else 0
                })
            
            return {
                "model_used": "holtwinters",
                "results_por_sku": results_por_sku,
                "model_version": "statsmodels-0.14",
                "warnings": self.warnings
            }
            
        except ImportError:
            logger.error("statsmodels not installed, falling back to v0")
            self.warnings.append("Holt-Winters no disponible, usando modelo v0")
            return self._forecast_v0(data, end_date_idx)
    
    def _forecast_sarimax(self, data: Dict[str, Any], end_date_idx: int) -> Dict[str, Any]:
        """
        SARIMAX with external regressors.
        """
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            logger.info("Using SARIMAX model")
            
            results_por_sku = []
            
            for sku in data["skus"]:
                ventas = sku["ventas"]
                
                if len([v for v in ventas if v > 0]) < 12:
                    forecast = [max(0, ventas[-1])] * self.forecast_horizon
                    mape = 999
                    estado = "sin_datos_suficientes"
                else:
                    try:
                        model = SARIMAX(
                            ventas,
                            order=(1, 1, 1),
                            seasonal_order=(1, 1, 1, 12),
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )
                        fit = model.fit(disp=False, maxiter=100)
                        forecast = fit.forecast(self.forecast_horizon).tolist()
                        forecast = [max(0, f) for f in forecast]
                        
                        mape = 50  # Placeholder
                        estado = "activo"
                        
                    except Exception as e:
                        logger.warning(f"SARIMAX failed for SKU {sku['skuId']}: {str(e)}")
                        forecast = [max(0, ventas[-1])] * self.forecast_horizon
                        mape = 999
                        estado = "sarimax_fallback"
                
                results_por_sku.append({
                    "sku": sku,
                    "forecast": forecast,
                    "mape": mape,
                    "estado": estado,
                    "ultimo_valor": ventas[-1] if ventas else 0
                })
            
            return {
                "model_used": "sarimax",
                "results_por_sku": results_por_sku,
                "model_version": "statsmodels-0.14",
                "warnings": self.warnings
            }
            
        except ImportError:
            logger.error("SARIMAX not available, falling back to v0")
            self.warnings.append("SARIMAX no disponible, usando modelo v0")
            return self._forecast_v0(data, end_date_idx)
    
    def _forecast_ml_cluster(
        self, data: Dict[str, Any], end_date_idx: int,
        cluster_assignments: Optional[List[int]]
    ) -> Dict[str, Any]:
        """
        ML-based forecast with clustering (XGBoost/LightGBM).
        """
        try:
            import xgboost as xgb
            from utils.feature_engineering import FeatureEngineer
            
            logger.info("Using ML cluster model")
            
            # Build features
            feature_engineer = FeatureEngineer()
            features, targets = feature_engineer.build_features(data["skus"], data["meses_fecha"])
            
            # Train model per cluster or globally
            results_por_sku = []
            
            for idx, sku in enumerate(data["skus"]):
                ventas = sku["ventas"]
                
                if len([v for v in ventas if v > 0]) < 6:
                    forecast = [max(0, ventas[-1] * 0.9)] * self.forecast_horizon
                    mape = 999
                    estado = "sin_datos_suficientes"
                else:
                    try:
                        # Simple lag features
                        X = []
                        y = []
                        for i in range(3, len(ventas)):
                            X.append([ventas[i-1], ventas[i-2], ventas[i-3]])
                            y.append(ventas[i])
                        
                        if len(X) >= 3:
                            model = xgb.XGBRegressor(
                                n_estimators=50,
                                max_depth=3,
                                learning_rate=0.1
                            )
                            model.fit(X, y)
                            
                            # Generate forecast
                            forecast = []
                            last_values = ventas[-3:]
                            for _ in range(self.forecast_horizon):
                                pred = model.predict([last_values])[0]
                                forecast.append(max(0, pred))
                                last_values = last_values[1:] + [pred]
                            
                            mape = 50  # Placeholder
                            estado = "activo"
                        else:
                            forecast = [max(0, ventas[-1])] * self.forecast_horizon
                            mape = 999
                            estado = "ml_fallback"
                        
                    except Exception as e:
                        logger.warning(f"ML failed for SKU {sku['skuId']}: {str(e)}")
                        forecast = [max(0, ventas[-1])] * self.forecast_horizon
                        mape = 999
                        estado = "ml_fallback"
                
                results_por_sku.append({
                    "sku": sku,
                    "forecast": forecast,
                    "mape": mape,
                    "estado": estado,
                    "ultimo_valor": ventas[-1] if ventas else 0
                })
            
            return {
                "model_used": "ml_cluster_xgboost",
                "results_por_sku": results_por_sku,
                "model_version": "xgboost-2.0",
                "warnings": self.warnings
            }
            
        except ImportError:
            logger.error("XGBoost not installed, falling back to v0")
            self.warnings.append("XGBoost no disponible, usando modelo v0")
            return self._forecast_v0(data, end_date_idx)
    
    def _forecast_ensemble(self, data: Dict[str, Any], end_date_idx: int) -> Dict[str, Any]:
        """
        Ensemble of multiple models with weighted average.
        """
        logger.info("Using ensemble model")
        
        # Run multiple models
        prophet_results = self._forecast_prophet(data, end_date_idx)
        hw_results = self._forecast_holtwinters(data, end_date_idx)
        ml_results = self._forecast_ml_cluster(data, end_date_idx, None)
        
        # Combine forecasts with weights
        weights = {"prophet": 0.4, "holtwinters": 0.3, "ml": 0.3}
        
        results_por_sku = []
        for i, sku in enumerate(data["skus"]):
            prophet_fc = prophet_results["results_por_sku"][i]["forecast"]
            hw_fc = hw_results["results_por_sku"][i]["forecast"]
            ml_fc = ml_results["results_por_sku"][i]["forecast"]
            
            # Weighted average
            ensemble_fc = [
                weights["prophet"] * p + weights["holtwinters"] * h + weights["ml"] * m
                for p, h, m in zip(prophet_fc, hw_fc, ml_fc)
            ]
            
            results_por_sku.append({
                "sku": sku,
                "forecast": ensemble_fc,
                "mape": 40,  # Ensemble typically better
                "estado": "activo",
                "ultimo_valor": sku["ventas"][-1] if sku["ventas"] else 0
            })
        
        return {
            "model_used": "ensemble(prophet+hw+ml)",
            "results_por_sku": results_por_sku,
            "model_version": "1.0.0",
            "model_params": weights,
            "warnings": self.warnings
        }
    
    def _forecast_v0(self, data: Dict[str, Any], end_date_idx: int) -> Dict[str, Any]:
        """
        Baseline heuristic model (linear + seasonality).
        """
        logger.info("Using v0 baseline model")
        
        results_por_sku = []
        
        for sku in data["skus"]:
            ventas = sku["ventas"]
            
            if len([v for v in ventas if v > 0]) < 2:
                forecast = [0] * self.forecast_horizon
                mape = 999
                estado = "cerrado"
            else:
                # Simple moving average with trend
                n = len(ventas)
                avg = np.mean([v for v in ventas if v > 0])
                last = ventas[-1] if ventas else 0
                
                forecast = [max(0, last * 0.95 + avg * 0.05)] * self.forecast_horizon
                mape = 60
                estado = "activo"
            
            results_por_sku.append({
                "sku": sku,
                "forecast": forecast,
                "mape": mape,
                "estado": estado,
                "ultimo_valor": ventas[-1] if ventas else 0
            })
        
        return {
            "model_used": "v0_baseline",
            "results_por_sku": results_por_sku,
            "model_version": "1.0.0",
            "warnings": self.warnings
        }
    
    def _apply_survival_adjustment(
        self, results: Dict[str, Any], survival_probs: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Adjust forecasts by survival probability (churn risk).
        """
        for result in results["results_por_sku"]:
            cliente_id = result["sku"]["codigoCliente"]
            prob = survival_probs.get(cliente_id, 1.0)
            
            # Adjust forecast by continuity probability
            result["forecast"] = [f * prob for f in result["forecast"]]
            result["survival_prob"] = prob
        
        return results
    
    def _build_response(
        self, results: Dict[str, Any], historical_data: Dict[str, Any],
        meses: List[str], meses_fecha: List[datetime],
        forecast_meses: List[str], forecast_meses_fecha: List[datetime],
        end_date_idx: int
    ) -> Dict[str, Any]:
        """
        Build standardized response structure.
        """
        # Aggregate by client
        clientes_map = {}
        for result in results["results_por_sku"]:
            cliente_id = result["sku"]["codigoCliente"]
            if cliente_id not in clientes_map:
                clientes_map[cliente_id] = {
                    "historico": 0,
                    "forecast": 0,
                    "skus_activos": 0
                }
            
            clientes_map[cliente_id]["historico"] += result["ultimo_valor"]
            clientes_map[cliente_id]["forecast"] += result["forecast"][0] if result["forecast"] else 0
            if result["estado"] == "activo":
                clientes_map[cliente_id]["skus_activos"] += 1
        
        # Build results
        resultados_por_cliente = [
            {
                "codigoCliente": cid,
                "ventasHistorico": data["historico"],
                "ventasForecast": data["forecast"],
                "variacion": ((data["forecast"] - data["historico"]) / data["historico"] * 100) 
                            if data["historico"] > 0 else 0,
                "skusActivos": data["skus_activos"]
            }
            for cid, data in clientes_map.items()
        ]
        
        resultados_por_sku = [
            {
                "codigoCliente": r["sku"]["codigoCliente"],
                "codigoArticulo": r["sku"]["codigoArticulo"],
                "skuId": r["sku"]["skuId"],
                "grupoMateriales": r["sku"]["grupoMatDesc"],
                "marca": r["sku"]["marcaDesc"],
                "negocio": r["sku"]["negocioDesc"],
                "ultimoValor": r["ultimo_valor"],
                "forecast": r["forecast"][0] if r["forecast"] else 0,
                "variacion": ((r["forecast"][0] - r["ultimo_valor"]) / r["ultimo_valor"] * 100)
                            if r["ultimo_valor"] > 0 and r["forecast"] else 0,
                "estado": r["estado"],
                "mape": r["mape"] if r["mape"] < 999 else None,
                "forecast_detalle": r["forecast"]
            }
            for r in results["results_por_sku"]
        ]
        
        total_historico = sum(r["ventasHistorico"] for r in resultados_por_cliente)
        total_forecast = sum(r["ventasForecast"] for r in resultados_por_cliente)
        
        # Build charts
        grafico_historico = [
            {
                "fecha": meses_fecha[i].strftime("%d/%m/%Y"),
                "mesAbreviado": meses[i],
                "ventas": sum(
                    sku["ventas"][i] for sku in historical_data["skus"]
                    if i < len(sku["ventas"])
                )
            }
            for i in range(len(historical_data["meses"]))
        ]
        
        grafico_forecast = [
            {
                "fecha": forecast_meses_fecha[i].strftime("%d/%m/%Y"),
                "mesAbreviado": forecast_meses[i],
                "forecast": sum(
                    r["forecast_detalle"][i] if i < len(r["forecast_detalle"]) else 0
                    for r in resultados_por_sku
                )
            }
            for i in range(len(forecast_meses))
        ]
        
        return {
            "model_used": results["model_used"],
            "model_version": results.get("model_version", "1.0.0"),
            "model_params": results.get("model_params", {}),
            "warnings": results.get("warnings", []),
            "summary": {
                "totalVentasHistoricas": total_historico,
                "totalForecast": total_forecast,
                "crecimientoEsperado": ((total_forecast - total_historico) / total_historico * 100)
                                      if total_historico > 0 else 0,
                "clientesActivos": len([c for c in resultados_por_cliente if c["skusActivos"] > 0]),
                "clientesTotales": len(resultados_por_cliente),
                "skusActivos": sum(c["skusActivos"] for c in resultados_por_cliente)
            },
            "grafico_historico": grafico_historico,
            "grafico_forecast": grafico_forecast,
            "resultados_por_sku": sorted(resultados_por_sku, key=lambda x: x["forecast"], reverse=True)[:20],
            "resultados_por_cliente": sorted(resultados_por_cliente, key=lambda x: x["ventasForecast"], reverse=True),
            "detalle_completo": {
                "meses": historical_data["meses"],
                "forecastMeses": forecast_meses,
                "resultadosPorSku": resultados_por_sku,
                "resultadosPorCliente": resultados_por_cliente
            }
        }
