"""
Data validation utilities.
"""
from typing import List, Any
import logging

logger = logging.getLogger(__name__)


def validate_sales_data(sales_data: Any) -> List[str]:
    """
    Validate sales data structure and contents.
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    # Check basic structure
    if not hasattr(sales_data, 'clientes'):
        errors.append("Missing 'clientes' field")
        return errors
    
    if not hasattr(sales_data, 'meses'):
        errors.append("Missing 'meses' field")
        return errors
    
    if not hasattr(sales_data, 'mesesFecha'):
        errors.append("Missing 'mesesFecha' field")
        return errors
    
    # Check data presence
    if len(sales_data.clientes) == 0:
        errors.append("No clients provided")
    
    if len(sales_data.meses) == 0:
        errors.append("No months provided")
    
    if len(sales_data.meses) != len(sales_data.mesesFecha):
        errors.append("Mismatch between meses and mesesFecha lengths")
    
    # Validate clients and SKUs
    for idx, cliente in enumerate(sales_data.clientes):
        if not hasattr(cliente, 'codigo') or not cliente.codigo:
            errors.append(f"Client at index {idx} missing codigo")
        
        if not hasattr(cliente, 'skus'):
            errors.append(f"Client {cliente.codigo if hasattr(cliente, 'codigo') else idx} missing skus")
            continue
        
        if len(cliente.skus) == 0:
            logger.warning(f"Client {cliente.codigo} has no SKUs")
        
        for sku_idx, sku in enumerate(cliente.skus):
            if not hasattr(sku, 'skuId'):
                errors.append(f"SKU at client {cliente.codigo}, index {sku_idx} missing skuId")
            
            if not hasattr(sku, 'ventasMes'):
                errors.append(f"SKU {sku.skuId if hasattr(sku, 'skuId') else sku_idx} missing ventasMes")
    
    # Validate date format
    try:
        from datetime import datetime
        for fecha_str in sales_data.mesesFecha[:5]:  # Check first 5
            datetime.fromisoformat(fecha_str)
    except Exception as e:
        errors.append(f"Invalid date format in mesesFecha: {str(e)}")
    
    return errors


def validate_forecast_request(
    forecast_months: int,
    end_date: str,
    meses: List[str],
    model: str
) -> List[str]:
    """
    Validate forecast request parameters.
    """
    errors = []
    
    if forecast_months < 1 or forecast_months > 24:
        errors.append("forecastMonths must be between 1 and 24")
    
    if end_date not in meses:
        errors.append(f"endDate '{end_date}' not found in available months")
    
    valid_models = ["v0", "holtwinters", "prophet", "sarimax", "ml_cluster", "ensemble"]
    if model not in valid_models:
        errors.append(f"Invalid model '{model}'. Valid options: {valid_models}")
    
    return errors
