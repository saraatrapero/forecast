"""
Client clustering based on sales patterns.
"""
import numpy as np
from typing import List, Dict, Any
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class ClientClusterer:
    """
    Cluster clients based on sales behavior patterns.
    """
    
    def __init__(self, n_clusters: Any = "auto"):
        self.n_clusters = n_clusters
        self.scaler = StandardScaler()
        self.model = None
        
    def fit_predict(self, sales_data: Any) -> List[int]:
        """
        Cluster clients and return cluster assignments.
        """
        # Extract features per client
        features = []
        client_ids = []
        
        for cliente in sales_data.clientes:
            # Aggregate all SKU sales for this client
            total_sales = {}
            for sku in cliente.skus:
                for mes, valor in sku.ventasMes.items():
                    total_sales[mes] = total_sales.get(mes, 0) + valor
            
            # Convert to time series
            ventas = list(total_sales.values())
            
            if len(ventas) == 0:
                continue
            
            # Compute features
            client_features = self._extract_features(ventas)
            features.append(client_features)
            client_ids.append(cliente.codigo)
        
        if len(features) < 2:
            logger.warning("Not enough clients for clustering")
            return [0] * len(client_ids)
        
        features_array = np.array(features)
        
        # Determine number of clusters
        if self.n_clusters == "auto":
            n_clusters = min(5, max(2, len(features) // 10))
        else:
            n_clusters = int(self.n_clusters)
        
        # Scale and cluster
        features_scaled = self.scaler.fit_transform(features_array)
        self.model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = self.model.fit_predict(features_scaled)
        
        logger.info(f"Clustered {len(client_ids)} clients into {n_clusters} clusters")
        
        return labels.tolist()
    
    def analyze(self, sales_data: Any) -> Dict[str, Any]:
        """
        Full clustering analysis with cluster profiles.
        """
        labels = self.fit_predict(sales_data)
        
        # Build cluster profiles
        cluster_profiles = {}
        for i, cliente in enumerate(sales_data.clientes):
            if i >= len(labels):
                continue
            
            cluster_id = labels[i]
            if cluster_id not in cluster_profiles:
                cluster_profiles[cluster_id] = {
                    "clients": [],
                    "avg_sales": [],
                    "total_sales": 0
                }
            
            total_sales = {}
            for sku in cliente.skus:
                for mes, valor in sku.ventasMes.items():
                    total_sales[mes] = total_sales.get(mes, 0) + valor
            
            total = sum(total_sales.values())
            
            cluster_profiles[cluster_id]["clients"].append(cliente.codigo)
            cluster_profiles[cluster_id]["total_sales"] += total
        
        # Compute statistics
        for cluster_id, profile in cluster_profiles.items():
            profile["num_clients"] = len(profile["clients"])
            profile["avg_sales_per_client"] = (
                profile["total_sales"] / profile["num_clients"]
                if profile["num_clients"] > 0 else 0
            )
        
        return {
            "num_clusters": len(cluster_profiles),
            "cluster_assignments": dict(zip(
                [c.codigo for c in sales_data.clientes],
                labels
            )),
            "cluster_profiles": cluster_profiles
        }
    
    def _extract_features(self, ventas: List[float]) -> List[float]:
        """
        Extract statistical features from sales time series.
        """
        if len(ventas) == 0:
            return [0] * 8
        
        ventas_array = np.array(ventas)
        
        # Basic statistics
        mean = np.mean(ventas_array)
        std = np.std(ventas_array)
        median = np.median(ventas_array)
        
        # Trend (simple linear)
        x = np.arange(len(ventas))
        if len(x) > 1:
            trend = np.polyfit(x, ventas_array, 1)[0]
        else:
            trend = 0
        
        # Variability
        cv = std / mean if mean > 0 else 0
        
        # Seasonality indicator (simple)
        if len(ventas) >= 12:
            seasonal_strength = np.std([
                ventas[i] - ventas[i-12]
                for i in range(12, len(ventas))
            ])
        else:
            seasonal_strength = 0
        
        # Activity
        zeros = np.sum(ventas_array == 0)
        zero_ratio = zeros / len(ventas_array)
        
        # Recent trend
        if len(ventas) >= 3:
            recent_trend = (ventas[-1] - ventas[-3]) / ventas[-3] if ventas[-3] > 0 else 0
        else:
            recent_trend = 0
        
        return [
            mean,
            std,
            median,
            trend,
            cv,
            seasonal_strength,
            zero_ratio,
            recent_trend
        ]
