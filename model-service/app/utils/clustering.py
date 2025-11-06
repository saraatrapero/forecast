"""
Customer clustering for segmentation
"""
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class CustomerClusterer:
    def __init__(self, n_clusters: int = 5, method: str = "kmeans"):
        self.n_clusters = n_clusters
        self.method = method
        self.scaler = StandardScaler()
        self.model = None
        
    def fit_predict(self, sales_data: Any, end_date: str) -> Dict[str, int]:
        """
        Cluster customers based on their purchasing patterns
        Returns dict: {cliente_codigo: cluster_id}
        """
        logger.info(f"Clustering {len(sales_data.clientes)} clientes into {self.n_clusters} groups")
        
        # Extract features per cliente
        features_list = []
        cliente_ids = []
        
        meses = sales_data.meses
        end_idx = meses.index(end_date)
        
        for cliente in sales_data.clientes:
            # Aggregate features across SKUs for this cliente
            total_sales = []
            for sku in cliente.skus:
                historico = [sku.ventasMes.get(m, 0) for m in meses[:end_idx + 1]]
                total_sales.append(sum(historico))
            
            if not total_sales or sum(total_sales) == 0:
                continue
            
            # Calculate features
            ventas_totales = sum(total_sales)
            ventas_promedio = np.mean(total_sales)
            ventas_std = np.std(total_sales)
            n_skus = len(cliente.skus)
            
            # Recency (months since last purchase)
            last_purchase_idx = -1
            for i in range(end_idx, -1, -1):
                mes = meses[i]
                if any(sku.ventasMes.get(mes, 0) > 0 for sku in cliente.skus):
                    last_purchase_idx = i
                    break
            recency = end_idx - last_purchase_idx if last_purchase_idx >= 0 else 999
            
            # Frequency (average purchases per month)
            n_months_active = sum(
                1 for i in range(end_idx + 1)
                if any(sku.ventasMes.get(meses[i], 0) > 0 for sku in cliente.skus)
            )
            frequency = n_months_active / (end_idx + 1) if end_idx >= 0 else 0
            
            # Trend (slope of recent months)
            recent_months = min(6, end_idx + 1)
            recent_sales = []
            for i in range(end_idx - recent_months + 1, end_idx + 1):
                if i >= 0:
                    mes_sales = sum(sku.ventasMes.get(meses[i], 0) for sku in cliente.skus)
                    recent_sales.append(mes_sales)
            
            trend = 0
            if len(recent_sales) >= 2:
                x = np.arange(len(recent_sales))
                if np.std(recent_sales) > 0:
                    trend = np.polyfit(x, recent_sales, 1)[0]
            
            features = [
                ventas_totales,
                ventas_promedio,
                ventas_std,
                n_skus,
                recency,
                frequency,
                trend
            ]
            
            features_list.append(features)
            cliente_ids.append(cliente.codigo)
        
        if len(features_list) < self.n_clusters:
            logger.warning(f"Not enough data for clustering: {len(features_list)} < {self.n_clusters}")
            # Return all in cluster 0
            return {cid: 0 for cid in cliente_ids}
        
        # Normalize features
        X = np.array(features_list)
        X_scaled = self.scaler.fit_transform(X)
        
        # Cluster
        if self.method == "kmeans":
            self.model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
            labels = self.model.fit_predict(X_scaled)
        else:
            # Fallback
            labels = np.zeros(len(cliente_ids), dtype=int)
        
        cluster_map = {cid: int(label) for cid, label in zip(cliente_ids, labels)}
        
        logger.info(f"Clustering complete: {dict(zip(*np.unique(labels, return_counts=True)))}")
        
        return cluster_map
