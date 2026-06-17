"""
SwasthAI API Comprehensive Testing Suite
Tests original endpoints and all new ecosystem extensions:
  - Health check
  - File prediction & Base64 prediction
  - Original reports
  - Hindi voice assistant NLP symptoms extraction
  - Stethoscope audio classification
  - Consolidated screening & SQLite DB storage
  - Case retrieval & Remote prescribing
"""

import requests
import sys
import os
import glob
import json
import base64
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:5000"

print("\n" + "="*70)
print(" SWASTHAI API - COMPREHENSIVE TESTING ".center(70, "="))
print("="*70)

# Test 1: Health Check
print("\n[TEST 1] Health Check Endpoint")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    data = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Service: {data.get('service')}")
    print(f"   Version: {data.get('version')}")
    print(f"   Model Loaded: {data.get('model_loaded')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: File Upload Prediction
print("\n[TEST 2] File Upload Prediction (/predict)")
print("-" * 70)
try:
    images = glob.glob(r"data/train/anemic/*.jpg")
    if not images:
        images = glob.glob(r"SwasthAI_AnemiaModel/data/train/anemic/*.jpg")
        
    if images:
        with open(images[0], 'rb') as f:
            files = {'image': f}
            data_form = {'scan_type': 'conjunctiva', 'patient_id': 'TEST-001'}
            response = requests.post(f"{BASE_URL}/predict", files=files, data=data_form, timeout=30)
        
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Anemia Probability: {result.get('anemia_probability', 0):.4f}")
        print(f"   Classification: {'ANEMIC' if result.get('is_anemic') else 'NON-ANEMIC'}")
        print(f"   Inference Time: {result.get('inference_ms')} ms")
        print(f"   Severity: {result.get('severity')}")
    else:
        print("⚠️ No images found in data folder for testing /predict. Skip.")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Base64 Prediction
print("\n[TEST 3] Base64 Prediction (/predict/b64)")
print("-" * 70)
try:
    images = glob.glob(r"data/train/non_anemic/*.jpg")
    if not images:
        images = glob.glob(r"SwasthAI_AnemiaModel/data/train/non_anemic/*.jpg")
        
    if images:
        with open(images[0], 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        payload = {
            'image_b64': image_b64,
            'scan_type': 'fingernail',
            'patient_id': 'TEST-002'
        }
        response = requests.post(f"{BASE_URL}/predict/b64", json=payload, timeout=30)
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Patient ID: {result.get('patient_id')}")
        print(f"   Anemia Probability: {result.get('anemia_probability', 0):.4f}")
        print(f"   Classification: {'ANEMIC' if result.get('is_anemic') else 'NON-ANEMIC'}")
        print(f"   Inference Time: {result.get('inference_ms')} ms")
    else:
        print("⚠️ No images found for testing /predict/b64. Skip.")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Full Screening Report
print("\n[TEST 4] Full Screening Report (/report)")
print("-" * 70)
try:
    anemic_imgs = glob.glob(r"data/train/anemic/*.jpg")
    non_anemic_imgs = glob.glob(r"data/train/non_anemic/*.jpg")
    
    if not anemic_imgs:
        anemic_imgs = glob.glob(r"SwasthAI_AnemiaModel/data/train/anemic/*.jpg")
        non_anemic_imgs = glob.glob(r"SwasthAI_AnemiaModel/data/train/non_anemic/*.jpg")
        
    if anemic_imgs and non_anemic_imgs:
        with open(anemic_imgs[0], 'rb') as f:
            conj_b64 = base64.b64encode(f.read()).decode()
        with open(non_anemic_imgs[0], 'rb') as f:
            nail_b64 = base64.b64encode(f.read()).decode()
        
        payload = {
            'conjunctiva_b64': conj_b64,
            'fingernail_b64': nail_b64,
            'patient_name': 'Priya Sharma',
            'patient_age': 28,
            'patient_gender': 'female',
            'symptoms': ['dizziness', 'fatigue', 'pale skin']
        }
        response = requests.post(f"{BASE_URL}/report", json=payload, timeout=30)
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Patient: {result['patient']['name']} ({result['patient']['age']} yo, {result['patient']['gender']})")
        print(f"   Aggregate Probability: {result['aggregate']['anemia_probability']:.4f}")
        print(f"   Severity: {result['aggregate']['severity']}")
        print(f"   Hemoglobin Estimate: {result['aggregate']['hemoglobin_estimate']}")
        print(f"   Doctor Alert: {'YES' if result['doctor_alert'] else 'NO'}")
    else:
        print("⚠️ No images found for testing /report. Skip.")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Hindi Voice NLP Symptom Extraction
print("\n[TEST 5] Hindi Voice NLP Symptom Assistant (/api/voice-symptoms)")
print("-" * 70)
try:
    payload = {
        "text": "Mujhe bahut kamzori lag rahi hai aur kal se chakkar aa raha hai"
    }
    response = requests.post(f"{BASE_URL}/api/voice-symptoms", json=payload, timeout=5)
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Transcript: {result.get('original_text')}")
    print(f"   Symptoms Extracted: {result.get('symptoms')}")
    print(f"   Hindi Spoken Advice: {result.get('hindi_response')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 6: Stethoscope Audio Classification
print("\n[TEST 6] Stethoscope Audio Classifier (/api/predict/stethoscope)")
print("-" * 70)
try:
    # Use the generated wheezing WAV file
    audio_path = os.path.join(os.path.dirname(__file__), "api", "static", "audio", "wheezing_lung.wav")
    if os.path.exists(audio_path):
        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            response = requests.post(f"{BASE_URL}/api/predict/stethoscope", files=files, timeout=10)
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"   Sound Classified: {result.get('class')}")
        print(f"   Confidence: {result.get('confidence')}")
        print(f"   Details: {result.get('details')}")
    else:
        print("⚠️ Wheezing WAV sample file not found. Skip.")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 7: Consolidated Multi-parameter Screening
print("\n[TEST 7] Consolidated Screening with Risk Fusion (/api/screen)")
print("-" * 70)
try:
    payload = {
        "patient_name": "Ramesh Kumar",
        "patient_age": 42,
        "patient_gender": "male",
        "location": "Kelwa Village, Rajasthan",
        "conjunctiva_prob": 0.62,
        "fingernail_prob": 0.58,
        "symptoms": ["fatigue", "breathless"],
        "stethoscope_result": "Wheezing",
        "heart_rate": 96,
        "spo2": 93,
        "temperature": 99.8
    }
    response = requests.post(f"{BASE_URL}/api/screen", json=payload, timeout=10)
    result = response.json()
    print(f"✅ Status: {response.status_code}")
    print(f"   Patient ID: {result.get('patient_id')} | Screening ID: {result.get('screening_id')}")
    print(f"   Unified Risk Score: {result.get('risk_score')}")
    print(f"   Unified Severity: {result.get('severity')} {result.get('icon')}")
    print(f"   Advice: {result.get('advice')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 8: Case Retrieval & Doctor Prescribing
print("\n[TEST 8] Case Retrieval & Remote Prescribing (/api/cases & /api/prescribe)")
print("-" * 70)
try:
    # 1. Fetch cases
    response_cases = requests.get(f"{BASE_URL}/api/cases", timeout=5)
    cases = response_cases.json()
    print(f"✅ Cases Retrieved: {len(cases)}")
    
    if len(cases) > 0:
        # Get the first case ID
        first_patient_id = cases[0]['patient_id']
        patient_name = cases[0]['name']
        print(f"   Selected Patient for Rx: {patient_name} (ID: {first_patient_id})")
        
        # 2. Prescribe
        payload_presc = {
            "patient_id": first_patient_id,
            "doctor_notes": "Recommend iron-rich diet and iron supplements for 30 days. Repeat CBC test in 1 month.",
            "prescribed_meds": ["Iron Supplement 100mg", "Vitamin C 500mg"],
            "status": "Prescribed"
        }
        response_presc = requests.post(f"{BASE_URL}/api/prescribe", json=payload_presc, timeout=5)
        res_presc = response_presc.json()
        print(f"✅ Prescription Status: {response_presc.status_code}")
        print(f"   Response Message: {res_presc.get('message')}")
    else:
        print("⚠️ No cases available to test prescription.")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print(" ALL TESTS COMPLETED ".center(70, "="))
print("="*70 + "\n")
