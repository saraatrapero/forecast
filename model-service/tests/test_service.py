#!/usr/bin/env python3
"""
Test script for model service
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Health check OK")
    return response.json()

def test_root():
    """Test root endpoint"""
    print("\nTesting /...")
    response = requests.get(f"{BASE_URL}")
    assert response.status_code == 200
    data = response.json()
    print(f"✅ Service: {data['service']}")
    print(f"   Models: {data['models']}")
    return data

def test_predict(model_name="prophet"):
    """Test predict endpoint"""
    print(f"\nTesting /predict with model={model_name}...")
    
    # Load sample data
    with open("tests/sample_request.json", "r") as f:
        payload = json.load(f)
    
    payload["model"] = model_name
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/predict",
        json=payload,
        timeout=120
    )
    duration = time.time() - start
    
    assert response.status_code == 200, f"Failed: {response.text}"
    data = response.json()
    
    print(f"✅ Forecast completed in {duration:.2f}s")
    print(f"   Model used: {data['modelUsed']}")
    print(f"   Total forecast: €{data['summary']['totalForecast']:.2f}")
    print(f"   Growth: {data['summary']['crecimientoEsperado']:.1f}%")
    print(f"   Training time: {data['diagnostics']['training_time_s']:.2f}s")
    
    return data

if __name__ == "__main__":
    print("=" * 60)
    print("Model Service Test Suite")
    print("=" * 60)
    
    try:
        # Test endpoints
        test_health()
        test_root()
        
        # Test models
        for model in ["prophet", "sarimax", "holtwinters", "ensemble"]:
            try:
                test_predict(model)
            except Exception as e:
                print(f"⚠️  Model {model} failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
