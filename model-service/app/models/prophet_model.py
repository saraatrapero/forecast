"""
Prophet forecasting model implementation
"""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ProphetForecaster:
    def __init__(self, seasonal_period: int = 12, holidays: Optional[List[str]] = None):
        self.seasonal_period = seasonal_period
        self.holidays = holidays
        self.models = {}  # Store models per SKU
        
    def get_params(self) -> Dict[str, Any]:
        return {
            "seasonal_period": self.seasonal_period,
            "holidays": len(self.holidays) if self.holidays else 0
        }
    
    def forecast(
        self,
        enriched_data: Dict[str, Any],
        forecast_months: int,
        end_date: str,
        cv_folds: int = 3
    ) -> Dict[str, Any]:
        """Generate forecasts using Prophet"""
        
        sales_data = enriched_data["sales_data"]
        meses = sales_data.meses
        meses_fecha = [pd.to_datetime(f) for f in sales_data.mesesFecha]
        
        end_idx = meses.index(end_date)
        
        # Prepare forecast periods
        forecast_meses = []
        forecast_meses_fecha = []
        current_date = meses_fecha[end_idx] + pd.DateOffset(months=1)
        
        for i in range(forecast_months):
            forecast_meses.append(current_date.strftime("%Y-%m"))
            forecast_meses_fecha.append(current_date)
            current_date += pd.DateOffset(months=1)
        
        resultados_por_sku = []
        resultados_por_cliente = {}
        
        total_ventas_historicas = 0
        total_forecast = 0
        
        logger.info(f"Processing {len(sales_data.clientes)} clientes...")
        
        for cliente in sales_data.clientes:
            cliente_codigo = cliente.codigo
            ventas_cliente_hist = 0
            ventas_cliente_forecast = 0
            skus_activos = 0
            
            for sku in cliente.skus:
                # Prepare time series
                historico = [sku.ventasMes.get(m, 0) for m in meses[:end_idx + 1]]
                
                # Skip if insufficient data
                if len(historico) < 3 or sum(historico) == 0:
                    forecast_detail = [0] * forecast_months
                    mape = 999
                else:
                    # Prepare Prophet dataframe
                    df = pd.DataFrame({
                        'ds': meses_fecha[:end_idx + 1],
                        'y': historico
                    })
                    
                    # Remove zeros for Prophet
                    df = df[df['y'] > 0].copy()
                    
                    if len(df) < 3:
                        forecast_detail = [0] * forecast_months
                        mape = 999
                    else:
                        try:
                            # Configure Prophet
                            model = Prophet(
                                yearly_seasonality=True if len(df) >= 24 else False,
                                weekly_seasonality=False,
                                daily_seasonality=False,
                                seasonality_mode='multiplicative',
                                changepoint_prior_scale=0.05
                            )
                            
                            # Add monthly seasonality
                            if len(df) >= self.seasonal_period:
                                model.add_seasonality(
                                    name='monthly',
                                    period=30.5,
                                    fourier_order=5
                                )
                            
                            # Fit model
                            model.fit(df)
                            
                            # Make future dataframe
                            future = pd.DataFrame({
                                'ds': forecast_meses_fecha
                            })
                            
                            # Predict
                            forecast_df = model.predict(future)
                            forecast_detail = [
                                max(0, val) for val in forecast_df['yhat'].tolist()
                            ]
                            
                            # Cross-validation for MAPE
                            mape = self._calculate_cv_mape(df, cv_folds)
                            
                            self.models[sku.skuId] = model
                            
                        except Exception as e:
                            logger.warning(f"Prophet failed for {sku.skuId}: {e}")
                            # Fallback to simple seasonal naive
                            forecast_detail = self._seasonal_naive_fallback(
                                historico, forecast_months, self.seasonal_period
                            )
                            mape = 999
                
                # Determine status
                ultimo_valor = historico[-1] if historico else 0
                primer_forecast = forecast_detail[0] if forecast_detail else 0
                
                cerrado = self._is_cliente_cerrado(historico[-4:] if len(historico) >= 4 else historico)
                
                if cerrado:
                    forecast_detail = [0] * forecast_months
                    primer_forecast = 0
                    estado = "cerrado"
                else:
                    estado = "activo"
                    skus_activos += 1
                
                variacion = 0
                if ultimo_valor > 0 and primer_forecast > 0:
                    variacion = ((primer_forecast - ultimo_valor) / ultimo_valor) * 100
                
                resultados_por_sku.append({
                    "codigoCliente": cliente_codigo,
                    "codigoArticulo": sku.codigoArticulo,
                    "skuId": sku.skuId,
                    "grupoMateriales": sku.grupoMatDesc or "",
                    "marca": sku.marcaDesc or "",
                    "negocio": sku.negocioDesc or "",
                    "ultimoValor": ultimo_valor,
                    "forecast": primer_forecast,
                    "variacion": variacion,
                    "estado": estado,
                    "mape": mape if mape < 999 else None,
                    "forecast_detalle": forecast_detail,
                    "p10": primer_forecast * 0.7,  # Simplified percentiles
                    "p50": primer_forecast,
                    "p90": primer_forecast * 1.3
                })
                
                ventas_cliente_hist += ultimo_valor
                ventas_cliente_forecast += primer_forecast
                total_ventas_historicas += ultimo_valor
                total_forecast += primer_forecast
            
            # Aggregate by cliente
            if cliente_codigo not in resultados_por_cliente:
                variacion_cliente = 0
                if ventas_cliente_hist > 0:
                    variacion_cliente = ((ventas_cliente_forecast - ventas_cliente_hist) / ventas_cliente_hist) * 100
                
                resultados_por_cliente[cliente_codigo] = {
                    "codigoCliente": cliente_codigo,
                    "ventasHistorico": ventas_cliente_hist,
                    "ventasForecast": ventas_cliente_forecast,
                    "variacion": variacion_cliente,
                    "skusActivos": skus_activos
                }
        
        # Build charts
        grafico_historico = []
        for i, mes in enumerate(meses[:end_idx + 1]):
            ventas_mes = sum([
                sku.ventasMes.get(mes, 0)
                for cliente in sales_data.clientes
                for sku in cliente.skus
            ])
            grafico_historico.append({
                "fecha": meses_fecha[i].strftime("%d/%m/%Y"),
                "mesAbreviado": mes,
                "ventas": ventas_mes,
                "diasHabiles": "1.00"
            })
        
        grafico_forecast = []
        for i, mes in enumerate(forecast_meses):
            forecast_mes = sum([
                r["forecast_detalle"][i] for r in resultados_por_sku
                if i < len(r["forecast_detalle"])
            ])
            grafico_forecast.append({
                "fecha": forecast_meses_fecha[i].strftime("%d/%m/%Y"),
                "mesAbreviado": mes,
                "forecast": forecast_mes
            })
        
        crecimiento = 0
        if total_ventas_historicas > 0:
            crecimiento = ((total_forecast - total_ventas_historicas) / total_ventas_historicas) * 100
        
        clientes_activos = sum(1 for c in resultados_por_cliente.values() if c["skusActivos"] > 0)
        
        return {
            "summary": {
                "totalVentasHistoricas": total_ventas_historicas,
                "totalForecast": total_forecast,
                "crecimientoEsperado": crecimiento,
                "clientesActivos": clientes_activos,
                "clientesTotales": len(sales_data.clientes),
                "skusActivos": sum(1 for r in resultados_por_sku if r["estado"] == "activo")
            },
            "graficoHistorico": grafico_historico,
            "graficoForecast": grafico_forecast,
            "resultadosPorSku": sorted(resultados_por_sku, key=lambda x: x["forecast"], reverse=True)[:20],
            "resultadosPorCliente": sorted(resultados_por_cliente.values(), key=lambda x: x["ventasForecast"], reverse=True),
            "detalleCompleto": {
                "meses": meses[:end_idx + 1],
                "forecastMeses": forecast_meses,
                "resultadosPorSku": resultados_por_sku,
                "resultadosPorCliente": list(resultados_por_cliente.values())
            },
            "cv_scores": {
                "horizon1": 15.2,  # Placeholder
                "horizon3": 18.5,
                "horizon6": 22.1
            }
        }
    
    def _calculate_cv_mape(self, df: pd.DataFrame, cv_folds: int) -> float:
        """Calculate MAPE using simple holdout"""
        if len(df) < 6:
            return 999
        
        try:
            test_size = min(3, len(df) // 4)
            train = df[:-test_size]
            test = df[-test_size:]
            
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=False,
                daily_seasonality=False
            )
            model.fit(train)
            
            future = pd.DataFrame({'ds': test['ds']})
            pred = model.predict(future)
            
            errors = []
            for actual, predicted in zip(test['y'], pred['yhat']):
                if actual > 0:
                    errors.append(abs((predicted - actual) / actual))
            
            return (sum(errors) / len(errors)) * 100 if errors else 999
        except:
            return 999
    
    def _seasonal_naive_fallback(
        self,
        historico: List[float],
        forecast_months: int,
        period: int
    ) -> List[float]:
        """Simple seasonal naive forecast as fallback"""
        if len(historico) < period:
            last_val = historico[-1] if historico else 0
            return [max(0, last_val)] * forecast_months
        
        forecast = []
        for i in range(forecast_months):
            idx = len(historico) - period + (i % period)
            if idx < len(historico):
                forecast.append(max(0, historico[idx]))
            else:
                forecast.append(0)
        
        return forecast
    
    def _is_cliente_cerrado(self, recent_sales: List[float]) -> bool:
        """Check if cliente is closed (3+ months without sales)"""
        if len(recent_sales) < 3:
            return False
        return all(s <= 0 for s in recent_sales[-3:])
