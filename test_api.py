"""Test SwasthAI API endpoints."""

import requests
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
import json
import glob
import base64
import time
from pathlib import Path

BASE_URL = "http://localhost:5000"

def test_health():
    """Test /health endpoint."""
    print("\n🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Model loaded: {data.get('model_loaded')}")
        print(f"   Service: {data.get('service')}")
        print(f"   ✅ Health check PASSED\n")
        return True
    except Exception as e:
        print(f"   ❌ Health check FAILED: {e}\n")
        return False


def test_predict_file():
    """Test /predict endpoint with file upload."""
    print("🔍 Testing /predict endpoint (file upload)...")
    
    # Find a sample image from training data
    sample_images = glob.glob(
        r"C:\Users\arpit\Downloads\SwasthAI_AnemiaModel\SwasthAI_AnemiaModel\data\train\anemic\*.jpg"
    )
    
    if not sample_images:
        print("   ❌ No training images found\n")
        return False
    
    image_path = sample_images[0]
    print(f"   Using sample image: {Path(image_path).name}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {
                'image': f,
            }
            data = {
                'scan_type': 'conjunctiva',
                'patient_id': 'TEST001'
            }
            response = requests.post(f"{BASE_URL}/predict", files=files, data=data, timeout=30)
        
        result = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Scan Type: {result.get('scan_type')}")
        print(f"   Anemia Probability: {result.get('anemia_probability'):.4f}")
        print(f"   Is Anemic: {result.get('is_anemic')}")
        print(f"   Inference Time: {result.get('inference_ms')} ms")
        print(f"   ✅ File upload prediction PASSED\n")
        return True
    except Exception as e:
        print(f"   ❌ File upload prediction FAILED: {e}\n")
        return False


def test_predict_base64():
    """Test /predict/b64 endpoint with base64 image."""
    print("🔍 Testing /predict/b64 endpoint (base64)...")
    
    # Find a sample image
    sample_images = glob.glob(
        r"C:\Users\arpit\Downloads\SwasthAI_AnemiaModel\SwasthAI_AnemiaModel\data\train\non_anemic\*.jpg"
    )
    
    if not sample_images:
        print("   ❌ No training images found\n")
        return False
    
    image_path = sample_images[0]
    print(f"   Using sample image: {Path(image_path).name}")
    
    try:
        # Read and encode image as base64
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            'image_b64': image_b64,
            'scan_type': 'fingernail',
            'patient_id': 'TEST002'
        }
        response = requests.post(
            f"{BASE_URL}/predict/b64",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Scan Type: {result.get('scan_type')}")
        print(f"   Anemia Probability: {result.get('anemia_probability'):.4f}")
        print(f"   Is Anemic: {result.get('is_anemic')}")
        print(f"   Inference Time: {result.get('inference_ms')} ms")
        print(f"   ✅ Base64 prediction PASSED\n")
        return True
    except Exception as e:
        print(f"   ❌ Base64 prediction FAILED: {e}\n")
        return False


def test_report():
    """Test /report endpoint with full screening report."""
    print("🔍 Testing /report endpoint (full screening report)...")
    
    # Find sample images
    anemic_images = glob.glob(
        r"C:\Users\arpit\Downloads\SwasthAI_AnemiaModel\SwasthAI_AnemiaModel\data\train\anemic\*.jpg"
    )
    non_anemic_images = glob.glob(
        r"C:\Users\arpit\Downloads\SwasthAI_AnemiaModel\SwasthAI_AnemiaModel\data\train\non_anemic\*.jpg"
    )
    
    if not anemic_images or not non_anemic_images:
        print("   ❌ Insufficient training images found\n")
        return False
    
    try:
        # Encode images as base64
        with open(anemic_images[0], 'rb') as f:
            conjunctiva_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        with open(non_anemic_images[0], 'rb') as f:
            fingernail_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {
            'conjunctiva_b64': conjunctiva_b64,
            'fingernail_b64': fingernail_b64,
            'patient_name': 'Test Patient',
            'patient_age': 30,
            'patient_gender': 'female',
            'symptoms': ['dizziness', 'fatigue']
        }
        response = requests.post(
            f"{BASE_URL}/report",
            json=payload,
            timeout=30
        )
        
        result = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Patient: {result.get('patient', {}).get('name')}")
        print(f"   Aggregate Anemia Probability: {result.get('aggregate', {}).get('anemia_probability'):.4f}")
        print(f"   Severity Level: {result.get('aggregate', {}).get('severity')}")
        print(f"   Doctor Alert: {result.get('doctor_alert')}")
        
        # Print recommendations
        recs = result.get('recommendations', [])
        if recs:
            print(f"   Recommendations:")
            for rec in recs[:2]:
                print(f"      - {rec}")
        
        print(f"   ✅ Screening report PASSED\n")
        return True
    except Exception as e:
        print(f"   ❌ Screening report FAILED: {e}\n")
        return False


if __name__ == "__main__":
    print("="*60)
    print("SwasthAI API Endpoint Tests")
    print("="*60)
    
    # Wait for server to be ready
    print("\n⏳ Waiting for API to be ready...")
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/health", timeout=2)
            print("   ✅ API is ready!\n")
            break
        except:
            time.sleep(1)
    
    # Run tests
    results = {
        "Health Check": test_health(),
        "File Upload Prediction": test_predict_file(),
        "Base64 Prediction": test_predict_base64(),
        "Screening Report": test_report(),
    }
    
    # Summary
    print("="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("="*60 + "\n")
