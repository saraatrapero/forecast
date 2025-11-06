"""
Simple test script for the model service.
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("\n=== Testing /health ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200

def test_models():
    """Test models list endpoint."""
    print("\n=== Testing /models ===")
    response = requests.get(f"{BASE_URL}/models")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Available models: {len(data['available_models'])}")
    for model in data['available_models']:
        print(f"  - {model['id']}: {model['name']}")
    assert response.status_code == 200

def generate_mock_data():
    """Generate mock sales data for testing."""
    meses = []
    meses_fecha = []
    
    # Generate 24 months of history
    base_date = datetime(2023, 1, 1)
    for i in range(24):
        date = base_date + timedelta(days=30 * i)
        meses.append(date.strftime("%Y-%m"))
        meses_fecha.append(date.isoformat())
    
    # Create mock clients and SKUs
    clientes = []
    for client_idx in range(5):
        skus = []
        for sku_idx in range(3):
            ventas_mes = {}
            base_value = 100 + client_idx * 20 + sku_idx * 10
            
            for idx, mes in enumerate(meses):
                # Add trend and seasonality
                trend = idx * 2
                seasonal = 20 * (1 if idx % 12 < 6 else -1)
                noise = (idx % 3) * 5
                ventas_mes[mes] = max(0, base_value + trend + seasonal + noise)
            
            skus.append({
                "codigoCliente": f"CLIENT{client_idx:03d}",
                "codigoArticulo": f"ART{sku_idx:04d}",
                "skuId": f"CLIENT{client_idx:03d}-ART{sku_idx:04d}",
                "ventasMes": ventas_mes,
                "envaseDesc": "Envase A",
                "formatoDesc": "Formato B",
                "grupoMat": "GM001",
                "grupoMatDesc": "Grupo Material 1",
                "marcaDesc": "Marca X",
                "materialId": "MAT001",
                "marcaDesglose": "Marca X Desglose",
                "negocioDesc": "Negocio Y"
            })
        
        clientes.append({
            "codigo": f"CLIENT{client_idx:03d}",
            "skus": skus
        })
    
    return {
        "clientes": clientes,
        "meses": meses,
        "mesesFecha": meses_fecha,
        "conceptos": {},
        "totalSkus": len(clientes) * 3
    }

def test_forecast(model="prophet"):
    """Test forecast endpoint."""
    print(f"\n=== Testing /predict with model={model} ===")
    
    sales_data = generate_mock_data()
    
    payload = {
        "salesData": sales_data,
        "forecastMonths": 6,
        "endDate": sales_data["meses"][-1],
        "model": model,
        "options": {}
    }
    
    print(f"Sending request with {len(sales_data['clientes'])} clients, {len(sales_data['meses'])} periods...")
    
    response = requests.post(
        f"{BASE_URL}/predict",
        json=payload,
        timeout=120
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Model used: {result['modelUsed']}")
        print(f"Training time: {result['diagnostics']['training_time_s']:.2f}s")
        print(f"Total historico: €{result['summary']['totalVentasHistoricas']:.2f}")
        print(f"Total forecast: €{result['summary']['totalForecast']:.2f}")
        print(f"Crecimiento: {result['summary']['crecimientoEsperado']:.1f}%")
        print(f"Warnings: {len(result['warnings'])}")
        if result['warnings']:
            for w in result['warnings']:
                print(f"  - {w}")
    else:
        print(f"Error: {response.text}")
    
    assert response.status_code == 200

def test_all_models():
    """Test all available models."""
    models = ["v0", "holtwinters", "prophet", "sarimax", "ml_cluster", "ensemble"]
    
    for model in models:
        try:
            test_forecast(model)
        except Exception as e:
            print(f"Warning: Model {model} failed: {str(e)}")

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Model Service Test Suite")
        print("=" * 60)
        
        test_health()
        test_models()
        
        # Test individual models
        print("\n" + "=" * 60)
        print("Testing Individual Models")
        print("=" * 60)
        
        test_forecast("v0")
        test_forecast("prophet")
        test_forecast("ml_cluster")
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
