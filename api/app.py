"""
SwasthAI – Anemia Detection REST API
======================================
Flask API that accepts:
  - POST /predict      → image file upload → JSON result
  - POST /predict/b64  → base64 image → JSON result (for Flutter app)
  - GET  /health       → API health check

Deploy on:
  - Raspberry Pi (edge, offline)
  - AWS/GCP (cloud, with sync)
  - Android via TFLite (embedded)
"""

from flask import Flask, request, jsonify
import numpy as np
import cv2
import base64
import os
import sys
import time
import json

# Add parent directory to path so we can import anemia_model
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# ── Load model on startup ──
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "swasthai_anemia.tflite")
KERAS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "best_anemia_model.keras")

detector = None

def load_detector():
    global detector
    if detector is not None:
        return
    from anemia_model import AnemiaDetector
    if os.path.exists(MODEL_PATH):
        detector = AnemiaDetector(MODEL_PATH)
    elif os.path.exists(KERAS_PATH):
        detector = AnemiaDetector(KERAS_PATH)
    else:
        print("⚠️  No trained model found. Run anemia_model.py first.")

load_detector()


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────

@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def welcome():
    """API Welcome & Documentation"""
    return jsonify({
        "service": "SwasthAI - Anemia Detection API",
        "version": "1.0.0",
        "status": "operational",
        "description": "Deep learning model for anemia detection from eye and nail images",
        "endpoints": {
            "GET /health": "Health check and service status",
            "GET /": "This welcome page",
            "POST /predict": "Single image prediction (file upload)",
            "POST /predict/b64": "Single image prediction (base64 image, for mobile apps)",
            "POST /report": "Comprehensive screening report"
        },
        "usage": {
            "/predict": {
                "method": "POST",
                "content_type": "multipart/form-data",
                "parameters": {
                    "image": "image file (required)",
                    "scan_type": "conjunctiva or fingernail (optional)",
                    "patient_id": "patient identifier (optional)"
                },
                "example": "curl -X POST -F 'image=@photo.jpg' http://localhost:5000/predict"
            },
            "/predict/b64": {
                "method": "POST",
                "content_type": "application/json",
                "parameters": {
                    "image_b64": "base64 encoded image (required)",
                    "scan_type": "conjunctiva or fingernail (optional)",
                    "patient_id": "patient identifier (optional)"
                }
            },
            "/report": {
                "method": "POST",
                "content_type": "application/json",
                "parameters": {
                    "conjunctiva_b64": "base64 conjunctiva image",
                    "fingernail_b64": "base64 fingernail image",
                    "patient_name": "patient name",
                    "patient_age": "patient age",
                    "patient_gender": "female or male",
                    "symptoms": "list of symptoms"
                }
            }
        },
        "response_format": {
            "anemia_probability": "0.0-1.0 (higher = more likely anemic)",
            "is_anemic": "true/false based on 0.5 threshold",
            "severity": "NO RISK, LOW RISK, MODERATE RISK, HIGH RISK",
            "inference_ms": "inference time in milliseconds"
        },
        "documentation": "See /health for service status"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "SwasthAI Anemia Detection API",
        "version": "1.0.0",
        "model_loaded": detector is not None,
        "timestamp": time.time(),
    })


@app.route("/predict", methods=["POST"])
def predict_file():
    """
    Predict anemia from uploaded image file.
    
    curl -X POST http://localhost:5000/predict \
         -F "image=@patient_eye.jpg" \
         -F "scan_type=conjunctiva"
    """
    if detector is None:
        return jsonify({"error": "Model not loaded. Run training first."}), 503

    if "image" not in request.files:
        return jsonify({"error": "No image file provided. Use field name 'image'"}), 400

    file = request.files["image"]
    scan_type = request.form.get("scan_type", "conjunctiva")  # conjunctiva | fingernail
    patient_id = request.form.get("patient_id", "unknown")

    # Read image
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Could not decode image"}), 400

    # Run inference
    start = time.time()
    result = detector.predict_from_array(img)
    inference_ms = round((time.time() - start) * 1000, 1)

    return jsonify({
        "patient_id": patient_id,
        "scan_type": scan_type,
        "inference_ms": inference_ms,
        **result,
    })


@app.route("/predict/b64", methods=["POST"])
def predict_base64():
    """
    Predict anemia from base64-encoded image.
    Used by Flutter mobile app.

    Body (JSON):
    {
        "image_b64": "<base64 string>",
        "scan_type": "conjunctiva",
        "patient_id": "P001"
    }
    """
    if detector is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json()
    if not data or "image_b64" not in data:
        return jsonify({"error": "Missing 'image_b64' field"}), 400

    try:
        img_bytes = base64.b64decode(data["image_b64"])
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"error": f"Invalid base64 image: {str(e)}"}), 400

    if img is None:
        return jsonify({"error": "Could not decode image"}), 400

    start = time.time()
    result = detector.predict_from_array(img)
    inference_ms = round((time.time() - start) * 1000, 1)

    return jsonify({
        "patient_id": data.get("patient_id", "unknown"),
        "scan_type": data.get("scan_type", "conjunctiva"),
        "inference_ms": inference_ms,
        **result,
    })


@app.route("/report", methods=["POST"])
def generate_report():
    """
    Generate a full health screening report.
    Aggregates conjunctiva + fingernail predictions.
    
    Body (JSON):
    {
        "conjunctiva_b64": "<base64>",
        "fingernail_b64": "<base64>",
        "patient_name": "Priya Sharma",
        "patient_age": 34,
        "patient_gender": "female",
        "symptoms": ["dizziness", "fatigue", "pale skin"]
    }
    """
    if detector is None:
        return jsonify({"error": "Model not loaded"}), 503

    data = request.get_json()
    results = {}

    for scan_type in ["conjunctiva", "fingernail"]:
        key = f"{scan_type}_b64"
        if key in data:
            try:
                img_bytes  = base64.b64decode(data[key])
                img_array  = np.frombuffer(img_bytes, np.uint8)
                img        = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                results[scan_type] = detector.predict_from_array(img)
            except Exception as e:
                results[scan_type] = {"error": str(e)}

    # Aggregate probability (average of available scans)
    probs = [r["anemia_probability"] for r in results.values() if "anemia_probability" in r]
    avg_prob = np.mean(probs) if probs else 0.5
    severity_info = detector.get_severity(avg_prob)

    # Symptom risk boost
    symptoms = data.get("symptoms", [])
    symptom_flags = {
        "dizziness":   "Dizziness is a common anemia symptom",
        "fatigue":     "Fatigue suggests possible low hemoglobin",
        "pale skin":   "Pallor strongly indicates anemia",
        "breathless":  "Breathlessness may indicate severe anemia",
        "headache":    "Headaches can occur with anemia",
    }
    symptom_matches = [symptom_flags[s] for s in symptoms if s in symptom_flags]

    report = {
        "patient": {
            "name":   data.get("patient_name", "Unknown"),
            "age":    data.get("patient_age"),
            "gender": data.get("patient_gender"),
        },
        "scan_results": results,
        "aggregate": {
            "anemia_probability": round(float(avg_prob), 4),
            "is_anemic":          bool(avg_prob >= 0.5),
            "severity":           severity_info["level"],
            "icon":               severity_info["icon"],
            "advice":             severity_info["advice"],
            "hindi_advice":       detector._get_hindi_advice(severity_info["level"]),
            "hemoglobin_estimate": detector._estimate_hemoglobin(avg_prob),
        },
        "symptoms": {
            "reported": symptoms,
            "clinical_flags": symptom_matches,
        },
        "recommendations": _get_recommendations(avg_prob, data.get("patient_gender", "female")),
        "doctor_alert": bool(avg_prob > 0.55),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return jsonify(report)


def _get_recommendations(prob: float, gender: str) -> list:
    recs = []
    threshold = 12.0 if gender == "female" else 13.0  # WHO thresholds g/dL

    if prob > 0.3:
        recs.append("Complete Blood Count (CBC) test recommended")
        recs.append("Iron-rich diet: spinach, lentils, jaggery, sesame seeds")
    if prob > 0.55:
        recs.append("Consult doctor within 48 hours")
        recs.append("Check for underlying causes: malnutrition, parasites, blood loss")
        recs.append("Consider iron supplementation (under medical supervision)")
    if prob > 0.75:
        recs.append("URGENT: Immediate hospital visit required")
        recs.append("Blood transfusion may be needed")
        recs.append("Emergency contact activated on doctor dashboard")
    return recs


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    load_detector()
    print("\n🌐 SwasthAI API running at http://0.0.0.0:5000")
    print("   Endpoints:")
    print("   GET  /health       → Health check")
    print("   POST /predict      → File upload")
    print("   POST /predict/b64  → Base64 image (Flutter)")
    print("   POST /report       → Full screening report\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
