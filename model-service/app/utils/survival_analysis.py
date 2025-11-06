"""
Survival analysis for customer churn prediction
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter
import logging

logger = logging.getLogger(__name__)

class SurvivalAnalyzer:
    def __init__(self):
        self.km_fitter = KaplanMeierFitter()
        
    def compute_survival_probabilities(
        self,
        sales_data: Any,
        end_date: str,
        forecast_months: int
    ) -> Dict[str, List[float]]:
        """
        Compute survival probabilities for each SKU/cliente
        Returns dict: {sku_id: [prob_month_1, prob_month_2, ...]}
        """
        logger.info("Computing survival probabilities...")
        
        meses = sales_data.meses
        end_idx = meses.index(end_date)
        
        survival_probs = {}
        
        for cliente in sales_data.clientes:
            for sku in cliente.skus:
                # Calculate time since last purchase
                historico = [sku.ventasMes.get(m, 0) for m in meses[:end_idx + 1]]
                
                # Find last non-zero purchase
                last_purchase_idx = -1
                for i in range(len(historico) - 1, -1, -1):
                    if historico[i] > 0:
                        last_purchase_idx = i
                        break
                
                if last_purchase_idx < 0:
                    # Never purchased - very low survival
                    survival_probs[sku.skuId] = [0.1] * forecast_months
                    continue
                
                months_since_last = len(historico) - 1 - last_purchase_idx
                
                # Simple exponential decay based on recency
                # More sophisticated: fit KM curve on historical data
                base_survival = np.exp(-0.2 * months_since_last)  # Decay rate
                
                # Forecast survival for each future month
                future_probs = []
                for month_ahead in range(1, forecast_months + 1):
                    total_months = months_since_last + month_ahead
                    prob = np.exp(-0.2 * total_months)
                    prob = max(0.05, min(1.0, prob))  # Clamp between 5% and 100%
                    future_probs.append(prob)
                
                survival_probs[sku.skuId] = future_probs
        
        logger.info(f"Computed survival probs for {len(survival_probs)} SKUs")
        
        return survival_probs
    
    def fit_kaplan_meier(self, durations: List[int], events: List[bool]) -> Any:
        """
        Fit Kaplan-Meier survival curve
        durations: time to event or censoring
        events: True if event occurred (churn), False if censored
        """
        self.km_fitter.fit(durations, events)
        return self.km_fitter
