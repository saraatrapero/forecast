"""
Time series data validation
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class TimeSeriesValidator:
    def __init__(self):
        pass
    
    def validate_data(self, sales_data: Any, end_date: str) -> Dict[str, Any]:
        """
        Validate input data for forecasting
        Returns: {"valid": bool, "errors": List[str], "warnings": List[str]}
        """
        errors = []
        warnings = []
        
        # Check clientes exist
        if not hasattr(sales_data, 'clientes') or not sales_data.clientes:
            errors.append("No clientes data provided")
        
        # Check meses exist
        if not hasattr(sales_data, 'meses') or not sales_data.meses:
            errors.append("No meses data provided")
        
        # Check end_date is valid
        if hasattr(sales_data, 'meses') and end_date not in sales_data.meses:
            errors.append(f"end_date '{end_date}' not found in meses")
        
        # Check for sufficient data
        if hasattr(sales_data, 'meses'):
            if len(sales_data.meses) < 3:
                warnings.append("Less than 3 months of data - forecasts may be unreliable")
            
            if len(sales_data.meses) > 100:
                warnings.append("More than 100 months of data - processing may be slow")
        
        # Check for missing data
        if hasattr(sales_data, 'clientes'):
            for cliente in sales_data.clientes:
                if not hasattr(cliente, 'skus') or not cliente.skus:
                    warnings.append(f"Cliente {cliente.codigo} has no SKUs")
        
        valid = len(errors) == 0
        
        if not valid:
            logger.error(f"Validation failed: {errors}")
        elif warnings:
            logger.warning(f"Validation warnings: {warnings}")
        
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings
        }
