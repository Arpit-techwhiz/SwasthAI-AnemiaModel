"""
SwasthAI – Anemia & Rural Health Screening REST API
=====================================================
Flask API that supports:
  - GET  /             → Serves the premium interactive Web Dashboard
  - GET  /api          → API Documentation & Endpoints list
  - GET  /health       → API health check
  - POST /predict      → Single image file upload → JSON result
  - POST /predict/b64  → Base64 image → JSON result
  - POST /report       → Original screening report endpoint
  
  Ecosystem Features:
  - POST /api/voice-symptoms     → Hindi spoken/typed symptoms extraction
  - POST /api/predict/stethoscope→ Stethoscope WAV audio classifier
  - POST /api/screen             → Consolidated multi-parameter screening (saves to DB)
  - GET  /api/cases              → Fetch all patient screening cases for Doctor Dashboard
  - POST /api/prescribe          → Submits remote doctor prescription
"""

from flask import Flask, request, jsonify
import numpy as np
import cv2
import base64
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
import time
import json
from flask_cors import CORS

# Add parent directory to path so we can import models and sub-modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Import Ecosystem Modules
import db_manager
import voice_nlp
import stethoscope_classifier
import risk_fusion

# Initialize SQLite database and generate mock audio samples
db_manager.init_db()
stethoscope_classifier.generate_synthesized_samples()

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
        print("⚠️ No trained model found. Run anemia_model.py first.")

load_detector()


# ──────────────────────────────────────────────
# CORE DASHBOARD SERVING
# ──────────────────────────────────────────────

@app.route("/", methods=["GET"])
def serve_dashboard():
    """Serve the SwasthAI Web Dashboard."""
    return app.send_static_file("index.html")


@app.route("/static/swasthai_anemia.tflite", methods=["GET"])
def serve_tflite_model():
    """Serve the TFLite model file statically."""
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"),
        "swasthai_anemia.tflite"
    )


# ──────────────────────────────────────────────
# API DOCUMENTATION & HEALTH
# ──────────────────────────────────────────────

@app.route("/api", methods=["GET"])
def welcome():
    """API Welcome & Documentation"""
    return jsonify({
        "service": "SwasthAI - Rural Health Screening API",
        "version": "1.1.0",
        "status": "operational",
        "description": "Deep learning and multi-parameter health screening API",
        "endpoints": {
            "GET /": "Serves the interactive Web Dashboard",
            "GET /health": "Health check and service status",
            "POST /predict": "Single image prediction (file upload)",
            "POST /predict/b64": "Single base64 image prediction",
            "POST /report": "Original screening report endpoint",
            "POST /api/voice-symptoms": "Extract symptoms from Hindi text transcript",
            "POST /api/predict/stethoscope": "Classify breathing sound WAV files",
            "POST /api/screen": "Consolidated screening with risk fusion (Saves to DB)",
            "GET /api/cases": "List all patient records for Doctor Dashboard",
            "POST /api/prescribe": "Submit prescription for a patient case"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "SwasthAI Anemia Detection API",
        "version": "1.1.0",
        "model_loaded": detector is not None,
        "timestamp": time.time(),
    })


# ──────────────────────────────────────────────
# CAMERA SCAN PREDICTIONS (ANEMIA)
# ──────────────────────────────────────────────

@app.route("/predict", methods=["POST"])
def predict_file():
    """Predict anemia from uploaded image file."""
    if detector is None:
        return jsonify({"error": "Model not loaded"}), 503

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    scan_type = request.form.get("scan_type", "conjunctiva")
    patient_id = request.form.get("patient_id", "unknown")

    # Read image
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({"error": "Could not decode image"}), 400

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
    """Predict anemia from base64-encoded image."""
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


# ──────────────────────────────────────────────
# RURAL SCREENING ECOSYSTEM ENDPOINTS
# ──────────────────────────────────────────────

@app.route("/api/voice-symptoms", methods=["POST"])
def extract_voice_symptoms():
    """Extract symptoms from Devanagari or Latin Hindi script transcript."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
        
    text = data["text"]
    symptoms = voice_nlp.extract_symptoms_from_text(text)
    hindi_response = voice_nlp.get_hindi_response_for_symptoms(symptoms)
    
    return jsonify({
        "original_text": text,
        "symptoms": symptoms,
        "hindi_response": hindi_response
    })


@app.route("/api/predict/stethoscope", methods=["POST"])
def predict_stethoscope():
    """Classify lung sounds from an uploaded WAV audio file."""
    if "audio" not in request.files:
        return jsonify({"error": "Missing 'audio' file upload"}), 400
        
    file = request.files["audio"]
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    # Save file temporarily
    temp_path = os.path.join(os.path.dirname(__file__), "temp_stethoscope.wav")
    file.save(temp_path)
    
    # Analyze
    result = stethoscope_classifier.StethoscopeClassifier.analyze_wav(temp_path)
    
    # Clean up temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if "error" in result:
        return jsonify(result), 400
        
    return jsonify(result)


@app.route("/api/screen", methods=["POST"])
def full_screening():
    """
    Consolidated health screening endpoint.
    Fuses camera scans, voice symptoms, vitals, and stethoscope findings.
    Saves the final screening record into the SQLite DB.
    """
    # 1. Parse payload. Support both JSON and multipart form data
    if request.is_json:
        data = request.get_json()
    else:
        # Load from form fields
        data = request.form.to_dict()
        # Parse symptoms if passed as a string representation of list
        if "symptoms" in data:
            try:
                data["symptoms"] = json.loads(data["symptoms"])
            except Exception:
                data["symptoms"] = [s.strip() for s in data["symptoms"].split(",") if s.strip()]
                
    if not data:
        return jsonify({"error": "No payload provided"}), 400

    name = data.get("patient_name", "Anonymous")
    phone = data.get("patient_phone", "")
    try:
        age = int(data.get("patient_age")) if data.get("patient_age") else 30
    except (ValueError, TypeError):
        age = 30
    gender = data.get("patient_gender", "unknown")
    location = data.get("location", "Rural Hub")
    
    # Vitals
    try:
        heart_rate = int(data.get("heart_rate")) if data.get("heart_rate") else None
    except (ValueError, TypeError):
        heart_rate = None

    try:
        spo2 = int(data.get("spo2")) if data.get("spo2") else None
    except (ValueError, TypeError):
        spo2 = None

    try:
        temperature = float(data.get("temperature")) if data.get("temperature") else None
    except (ValueError, TypeError):
        temperature = None
    
    # Symptoms & Stethoscope
    symptoms = data.get("symptoms", [])
    if isinstance(symptoms, str):
        symptoms = [s.strip() for s in symptoms.split(",") if s.strip()]
        
    stethoscope_result = data.get("stethoscope_result", "None")

    # ── CAMERA PREDICTIONS (ANEMIA) ──
    conjunctiva_prob = None
    fingernail_prob = None

    # Handle file uploads if present
    if "conjunctiva_image" in request.files:
        conj_file = request.files["conjunctiva_image"]
        img_bytes = np.frombuffer(conj_file.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            res = detector.predict_from_array(img)
            conjunctiva_prob = res["anemia_probability"]
            
    if "fingernail_image" in request.files:
        nail_file = request.files["fingernail_image"]
        img_bytes = np.frombuffer(nail_file.read(), np.uint8)
        img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            res = detector.predict_from_array(img)
            fingernail_prob = res["anemia_probability"]

    # Handle Base64 strings if present in JSON payload
    if conjunctiva_prob is None and data.get("conjunctiva_b64"):
        try:
            img_bytes = base64.b64decode(data["conjunctiva_b64"])
            img_array = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                res = detector.predict_from_array(img)
                conjunctiva_prob = res["anemia_probability"]
        except Exception:
            pass

    if fingernail_prob is None and data.get("fingernail_b64"):
        try:
            img_bytes = base64.b64decode(data["fingernail_b64"])
            img_array = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                res = detector.predict_from_array(img)
                fingernail_prob = res["anemia_probability"]
        except Exception:
            pass

    # Support default probability fallback if no images provided
    if conjunctiva_prob is None and data.get("conjunctiva_prob") is not None:
        try:
            val = str(data["conjunctiva_prob"]).strip()
            conjunctiva_prob = float(val) if val != "" else None
        except (ValueError, TypeError):
            conjunctiva_prob = None

    if fingernail_prob is None and data.get("fingernail_prob") is not None:
        try:
            val = str(data["fingernail_prob"]).strip()
            fingernail_prob = float(val) if val != "" else None
        except (ValueError, TypeError):
            fingernail_prob = None

    # ── RISK FUSION COMPUTATION ──
    fusion_report = risk_fusion.calculate_fusion_risk(
        conjunctiva_prob=conjunctiva_prob,
        fingernail_prob=fingernail_prob,
        symptoms=symptoms,
        stethoscope_result=stethoscope_result,
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature
    )

    # ── DB PERSISTENCE ──
    patient_id, screening_id = db_manager.save_screening(
        name=name,
        age=age,
        gender=gender,
        location=location,
        conjunctiva_prob=conjunctiva_prob,
        fingernail_prob=fingernail_prob,
        symptoms=symptoms,
        stethoscope_result=stethoscope_result,
        heart_rate=heart_rate,
        spo2=spo2,
        temperature=temperature,
        risk_score=fusion_report["risk_score"],
        severity=fusion_report["severity"],
        phone=phone
    )

    # Prepare detailed response
    response_data = {
        "screening_id": screening_id,
        "patient_id": patient_id,
        "patient": {
            "name": name,
            "age": age,
            "gender": gender,
            "location": location
        },
        "scans": {
            "conjunctiva_prob": conjunctiva_prob,
            "fingernail_prob": fingernail_prob
        },
        "vitals": {
            "heart_rate": heart_rate,
            "spo2": spo2,
            "temperature": temperature
        },
        "symptoms": symptoms,
        "stethoscope_result": stethoscope_result,
        **fusion_report
    }

    return jsonify(response_data)


@app.route("/api/cases", methods=["GET"])
def get_cases():
    """Retrieve list of patient screenings for the Doctor Dashboard."""
    cases = db_manager.get_all_cases()
    return jsonify(cases)


@app.route("/api/patient-history/<int:patient_id>", methods=["GET"])
def get_patient_history_route(patient_id):
    """Fetch historical screenings for a given patient ID."""
    history = db_manager.get_patient_history(patient_id)
    return jsonify(history)


@app.route("/api/prescribe", methods=["POST"])
def prescribe():
    """Submit a remote doctor prescription and update case review status."""
    data = request.get_json()
    if not data or "patient_id" not in data or "doctor_notes" not in data:
        return jsonify({"error": "Missing patient_id or doctor_notes"}), 400
        
    patient_id = int(data["patient_id"])
    doctor_notes = data["doctor_notes"]
    prescribed_meds = data.get("prescribed_meds", [])
    status = data.get("status", "Prescribed")
    
    success = db_manager.add_prescription(patient_id, doctor_notes, prescribed_meds, status)
    
    return jsonify({
        "success": success,
        "message": f"Prescription successfully registered for patient ID {patient_id}."
    })


# ──────────────────────────────────────────────
# ORIGINAL COMPATIBILITY PORT FOR FLUTTER APP
# ──────────────────────────────────────────────

@app.route("/report", methods=["POST"])
def generate_report():
    """
    Original screening report endpoint.
    Saves report directly to SQLite DB as well to show up on the Doctor Dashboard.
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

    # Aggregate probability
    probs = [r["anemia_probability"] for r in results.values() if "anemia_probability" in r]
    avg_prob = np.mean(probs) if probs else 0.15
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

    # Calculate fusion report parameters
    gender = data.get("patient_gender", "female")
    age = data.get("patient_age", 30)
    name = data.get("patient_name", "Unknown")
    
    fusion_report = risk_fusion.calculate_fusion_risk(
        conjunctiva_prob=results.get("conjunctiva", {}).get("anemia_probability"),
        fingernail_prob=results.get("fingernail", {}).get("anemia_probability"),
        symptoms=symptoms,
        stethoscope_result="None",
        heart_rate=None,
        spo2=None,
        temperature=None
    )

    # Write to local DB so it is visible in dashboard
    db_manager.save_screening(
        name=name,
        age=age,
        gender=gender,
        location="Mobile Sync",
        conjunctiva_prob=results.get("conjunctiva", {}).get("anemia_probability"),
        fingernail_prob=results.get("fingernail", {}).get("anemia_probability"),
        symptoms=symptoms,
        stethoscope_result="None",
        heart_rate=None,
        spo2=None,
        temperature=None,
        risk_score=fusion_report["risk_score"],
        severity=fusion_report["severity"]
    )

    # Recommendations helper
    def _get_recommendations(prob, gender):
        recs = []
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

    report = {
        "patient": {
            "name":   name,
            "age":    age,
            "gender": gender,
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
        "recommendations": _get_recommendations(avg_prob, gender),
        "risk_score": fusion_report["risk_score"],
        "fused_severity": fusion_report["severity"],
        "doctor_alert": bool(avg_prob > 0.55),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return jsonify(report)


if __name__ == "__main__":
    load_detector()
    print("\n🌐 SwasthAI API running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
