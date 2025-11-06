"""
Ensemble forecasting - combines multiple models with weighted average
"""
from typing import Dict, List, Any, Optional
import numpy as np
import logging

from .prophet_model import ProphetForecaster
from .sarimax_model import SARIMAXForecaster
from .holtwinters_model import HoltWintersForecaster

logger = logging.getLogger(__name__)

class EnsembleForecaster:
    def __init__(
        self,
        models: List[str] = ["prophet", "sarimax", "holtwinters"],
        weights: Optional[List[float]] = None,
        clusters: Optional[Dict[str, int]] = None
    ):
        self.model_names = models
        self.weights = weights or [1.0 / len(models)] * len(models)
        self.clusters = clusters
        
        # Normalize weights
        total = sum(self.weights)
        self.weights = [w / total for w in self.weights]
        
        # Initialize forecasters
        self.forecasters = []
        for model_name in models:
            if model_name == "prophet":
                self.forecasters.append(ProphetForecaster())
            elif model_name == "sarimax":
                self.forecasters.append(SARIMAXForecaster())
            elif model_name == "holtwinters":
                self.forecasters.append(HoltWintersForecaster())
            # Add XGBoost/LightGBM support here if needed
        
    def get_params(self) -> Dict[str, Any]:
        return {
            "models": self.model_names,
            "weights": self.weights,
            "n_models": len(self.forecasters)
        }
    
    def forecast(
        self,
        enriched_data: Dict[str, Any],
        forecast_months: int,
        end_date: str,
        cv_folds: int = 3
    ) -> Dict[str, Any]:
        """Generate ensemble forecast by combining multiple models"""
        
        logger.info(f"Running ensemble with {len(self.forecasters)} models")
        
        # Get forecasts from all models
        all_forecasts = []
        for i, forecaster in enumerate(self.forecasters):
            try:
                logger.info(f"Running model {i+1}/{len(self.forecasters)}: {self.model_names[i]}")
                forecast_result = forecaster.forecast(
                    enriched_data,
                    forecast_months,
                    end_date,
                    cv_folds
                )
                all_forecasts.append(forecast_result)
            except Exception as e:
                logger.error(f"Model {self.model_names[i]} failed: {e}")
                # Continue with other models
        
        if not all_forecasts:
            raise Exception("All ensemble models failed")
        
        # Combine forecasts using weighted average
        combined_result = self._combine_forecasts(all_forecasts, self.weights[:len(all_forecasts)])
        
        return combined_result
    
    def _combine_forecasts(
        self,
        forecasts: List[Dict[str, Any]],
        weights: List[float]
    ) -> Dict[str, Any]:
        """Combine multiple forecast results using weighted average"""
        
        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]
        
        # Use first forecast as template
        base = forecasts[0]
        
        # Combine SKU forecasts
        sku_dict = {}
        for forecast_result in forecasts:
            for sku in forecast_result["resultadosPorSku"]:
                sku_id = sku["skuId"]
                if sku_id not in sku_dict:
                    sku_dict[sku_id] = []
                sku_dict[sku_id].append(sku)
        
        combined_skus = []
        for sku_id, sku_list in sku_dict.items():
            if not sku_list:
                continue
            
            # Get base SKU info from first
            base_sku = sku_list[0].copy()
            
            # Weighted average of forecasts
            forecast_details = []
            for i in range(len(sku_list[0]["forecast_detalle"])):
                weighted_vals = [
                    sku["forecast_detalle"][i] * weights[j]
                    for j, sku in enumerate(sku_list)
                    if i < len(sku["forecast_detalle"])
                ]
                forecast_details.append(sum(weighted_vals))
            
            base_sku["forecast_detalle"] = forecast_details
            base_sku["forecast"] = forecast_details[0] if forecast_details else 0
            
            # Recalculate variation
            if base_sku["ultimoValor"] > 0 and base_sku["forecast"] > 0:
                base_sku["variacion"] = (
                    (base_sku["forecast"] - base_sku["ultimoValor"]) / base_sku["ultimoValor"]
                ) * 100
            
            # Average MAPE
            mapes = [sku.get("mape") for sku in sku_list if sku.get("mape") and sku.get("mape") < 999]
            base_sku["mape"] = np.mean(mapes) if mapes else None
            
            combined_skus.append(base_sku)
        
        # Recalculate cliente aggregates
        resultados_por_cliente = {}
        for sku in combined_skus:
            cliente_codigo = sku["codigoCliente"]
            if cliente_codigo not in resultados_por_cliente:
                resultados_por_cliente[cliente_codigo] = {
                    "codigoCliente": cliente_codigo,
                    "ventasHistorico": 0,
                    "ventasForecast": 0,
                    "skusActivos": 0
                }
            
            resultados_por_cliente[cliente_codigo]["ventasHistorico"] += sku["ultimoValor"]
            resultados_por_cliente[cliente_codigo]["ventasForecast"] += sku["forecast"]
            if sku["estado"] == "activo":
                resultados_por_cliente[cliente_codigo]["skusActivos"] += 1
        
        # Calculate variations
        for cliente in resultados_por_cliente.values():
            if cliente["ventasHistorico"] > 0:
                cliente["variacion"] = (
                    (cliente["ventasForecast"] - cliente["ventasHistorico"]) / cliente["ventasHistorico"]
                ) * 100
            else:
                cliente["variacion"] = 0
        
        # Recalculate totals
        total_ventas_historicas = sum(sku["ultimoValor"] for sku in combined_skus)
        total_forecast = sum(sku["forecast"] for sku in combined_skus)
        crecimiento = 0
        if total_ventas_historicas > 0:
            crecimiento = ((total_forecast - total_ventas_historicas) / total_ventas_historicas) * 100
        
        clientes_activos = sum(1 for c in resultados_por_cliente.values() if c["skusActivos"] > 0)
        
        # Rebuild forecast chart
        grafico_forecast = []
        for i in range(len(base["graficoForecast"])):
            mes_data = base["graficoForecast"][i].copy()
            forecast_mes = sum([
                sku["forecast_detalle"][i] for sku in combined_skus
                if i < len(sku["forecast_detalle"])
            ])
            mes_data["forecast"] = forecast_mes
            grafico_forecast.append(mes_data)
        
        return {
            "summary": {
                "totalVentasHistoricas": total_ventas_historicas,
                "totalForecast": total_forecast,
                "crecimientoEsperado": crecimiento,
                "clientesActivos": clientes_activos,
                "clientesTotales": len(resultados_por_cliente),
                "skusActivos": sum(1 for sku in combined_skus if sku["estado"] == "activo")
            },
            "graficoHistorico": base["graficoHistorico"],
            "graficoForecast": grafico_forecast,
            "resultadosPorSku": sorted(combined_skus, key=lambda x: x["forecast"], reverse=True)[:20],
            "resultadosPorCliente": sorted(resultados_por_cliente.values(), key=lambda x: x["ventasForecast"], reverse=True),
            "detalleCompleto": {
                "meses": base["detalleCompleto"]["meses"],
                "forecastMeses": base["detalleCompleto"]["forecastMeses"],
                "resultadosPorSku": combined_skus,
                "resultadosPorCliente": list(resultados_por_cliente.values())
            },
            "cv_scores": {
                "horizon1": np.mean([f["cv_scores"]["horizon1"] for f in forecasts]),
                "horizon3": np.mean([f["cv_scores"]["horizon3"] for f in forecasts]),
                "horizon6": np.mean([f["cv_scores"]["horizon6"] for f in forecasts])
            }
        }
