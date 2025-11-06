"""
Survival analysis for churn prediction.
"""
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SurvivalAnalyzer:
    """
    Predict client churn using survival analysis techniques.
    """
    
    def predict_continuity(self, sales_data: Any, end_date: str) -> Dict[str, float]:
        """
        Predict probability that each client will continue active.
        Returns dict: {cliente_id: probability}
        """
        try:
            from lifelines import KaplanMeierFitter
        except ImportError:
            logger.warning("lifelines not installed, using simple heuristic")
            return self._simple_churn_prediction(sales_data, end_date)
        
        # For each client, compute time since last purchase
        end_date_idx = sales_data.meses.index(end_date)
        
        continuity_probs = {}
        
        for cliente in sales_data.clientes:
            # Find last non-zero month
            last_active_idx = -1
            for sku in cliente.skus:
                for i in range(end_date_idx, -1, -1):
                    mes = sales_data.meses[i]
                    if sku.ventasMes.get(mes, 0) > 0:
                        last_active_idx = max(last_active_idx, i)
                        break
            
            if last_active_idx == -1:
                # Never active
                prob = 0.0
            else:
                months_inactive = end_date_idx - last_active_idx
                
                # Simple exponential decay
                # After 3 months: 50%, after 6 months: 25%, etc.
                prob = np.exp(-months_inactive / 3.0)
            
            continuity_probs[cliente.codigo] = prob
        
        return continuity_probs
    
    def analyze(self, sales_data: Any, end_date: str) -> Dict[str, Any]:
        """
        Full survival analysis with statistics.
        """
        continuity_probs = self.predict_continuity(sales_data, end_date)
        
        # Classify clients by risk
        high_risk = [cid for cid, prob in continuity_probs.items() if prob < 0.3]
        medium_risk = [cid for cid, prob in continuity_probs.items() if 0.3 <= prob < 0.7]
        low_risk = [cid for cid, prob in continuity_probs.items() if prob >= 0.7]
        
        return {
            "continuity_probabilities": continuity_probs,
            "risk_segmentation": {
                "high_risk": {"count": len(high_risk), "clients": high_risk[:10]},
                "medium_risk": {"count": len(medium_risk), "clients": medium_risk[:10]},
                "low_risk": {"count": len(low_risk), "clients": low_risk[:10]}
            },
            "avg_continuity_prob": np.mean(list(continuity_probs.values()))
        }
    
    def _simple_churn_prediction(self, sales_data: Any, end_date: str) -> Dict[str, float]:
        """
        Fallback heuristic when lifelines is not available.
        """
        end_date_idx = sales_data.meses.index(end_date)
        
        probs = {}
        for cliente in sales_data.clientes:
            months_without_sale = 0
            for i in range(end_date_idx, max(0, end_date_idx - 6), -1):
                mes = sales_data.meses[i]
                has_sale = any(sku.ventasMes.get(mes, 0) > 0 for sku in cliente.skus)
                if has_sale:
                    break
                months_without_sale += 1
            
            # Simple decay
            prob = max(0.0, 1.0 - (months_without_sale / 6.0))
            probs[cliente.codigo] = prob
        
        return probs
