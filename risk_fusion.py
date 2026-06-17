"""
SwasthAI - Multi-Parameter Fusion Risk Scoring Engine
Aggregates camera-based anemia probabilities, voice symptoms, vitals, and stethoscope findings.
Uses a clinical-style point allocation system (total 100 points).
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

def calculate_fusion_risk(conjunctiva_prob: float, fingernail_prob: float, symptoms: list,
                          stethoscope_result: str, heart_rate: int, spo2: int, temperature: float) -> dict:
    """
    Computes a unified health risk score using a clinical point-based scoring system:
    - Anemia AI Score: 0 - 40 points
    - Symptoms: 0 - 25 points
    - Respiratory Findings: 0 - 20 points
    - Vitals: 0 - 15 points
    Total = 100 points.
    """
    # ── Safe Type Conversions & Validations ──
    try:
        conjunctiva_prob = float(conjunctiva_prob) if conjunctiva_prob is not None and str(conjunctiva_prob).strip() != "" else None
    except (ValueError, TypeError):
        conjunctiva_prob = None

    try:
        fingernail_prob = float(fingernail_prob) if fingernail_prob is not None and str(fingernail_prob).strip() != "" else None
    except (ValueError, TypeError):
        fingernail_prob = None

    try:
        heart_rate = int(float(heart_rate)) if heart_rate is not None and str(heart_rate).strip() != "" else None
    except (ValueError, TypeError):
        heart_rate = None

    try:
        spo2 = int(float(spo2)) if spo2 is not None and str(spo2).strip() != "" else None
    except (ValueError, TypeError):
        spo2 = None

    try:
        temperature = float(temperature) if temperature is not None and str(temperature).strip() != "" else None
    except (ValueError, TypeError):
        temperature = None

    if symptoms is None:
        symptoms = []
    elif isinstance(symptoms, str):
        symptoms = [s.strip() for s in symptoms.split(",") if s.strip()]
    elif not isinstance(symptoms, list):
        symptoms = list(symptoms)

    stethoscope_result = str(stethoscope_result).strip().lower() if stethoscope_result is not None else "none"

    # ── 1. Anemia AI Score (Max 40 points) ──
    scans = []
    if conjunctiva_prob is not None:
        scans.append(conjunctiva_prob)
    if fingernail_prob is not None:
        scans.append(fingernail_prob)
        
    avg_anemia_prob = sum(scans) / len(scans) if scans else 0.15
    anemia_points = round(avg_anemia_prob * 40.0, 2)
    
    # ── 2. Symptoms Score (Max 25 points) ──
    symptom_weights = {
        "pale skin": 8.0,
        "breathless": 8.0,
        "chest pain": 8.0,
        "dizziness": 5.0,
        "fatigue": 4.0,
        "cold extremities": 4.0,
        "loss of appetite": 4.0,
        "brittle nails": 3.0,
        "headache": 3.0,
        "hair loss": 2.0
    }
    symptom_points = 0.0
    if symptoms:
        symptom_points = sum(symptom_weights.get(s.strip().lower(), 0.0) for s in symptoms)
        symptom_points = min(symptom_points, 25.0) # Cap at 25 points
        
    # ── 3. Respiratory Findings (Max 20 points) ──
    steth_map = {
        "normal": 0.0,
        "wheezing": 12.0,
        "crackles": 20.0,
        "none": 0.0
    }
    steth_points = steth_map.get(str(stethoscope_result).strip().lower(), 0.0)
    
    # ── 4. Vitals Score (Max 15 points) ──
    vitals_points = 0.0
    
    # SpO2
    if spo2 is not None and spo2 > 0:
        if spo2 < 90:
            vitals_points += 12.0  # Severe hypoxia
        elif spo2 < 95:
            vitals_points += 6.0   # Mild hypoxia
            
    # Heart Rate
    if heart_rate is not None and heart_rate > 0:
        if heart_rate > 105 or heart_rate < 50:
            vitals_points += 4.0   # Tachycardia/Bradycardia
            
    # Temperature
    if temperature is not None and temperature > 0:
        if temperature > 100.4 or temperature < 95.0:
            vitals_points += 4.0   # Fever/Hypothermia
            
    vitals_points = min(vitals_points, 15.0) # Cap at 15 points
    
    # ── TOTAL CLINICAL SCORE (Max 100 points) ──
    total_score = round(anemia_points + symptom_points + steth_points + vitals_points, 2)
    
    # ── CLINICAL SEVERITY THRESHOLDS ──
    # 0 - 25: LOW
    # 26 - 50: MODERATE
    # 51 - 75: HIGH
    # 76 - 100: CRITICAL
    if total_score <= 25.0:
        severity = "LOW RISK"
        icon = "✅"
        advice = "Physiological scores within healthy limits. Maintain balanced nutrition."
        hindi_advice = "शारीरिक स्कोर स्वस्थ सीमा के भीतर। संतुलित पोषण बनाए रखें।"
    elif total_score <= 50.0:
        severity = "MODERATE RISK"
        icon = "⚠️"
        advice = "Mild physiological deviation. Routine Complete Blood Count (CBC) test recommended."
        hindi_advice = "हल्का शारीरिक विचलन। हीमोग्लोबिन और सीबीसी रक्त जांच की सिफारिश की जाती है।"
    elif total_score <= 75.0:
        severity = "HIGH RISK"
        icon = "🔴"
        advice = "Significant risk indicators. Consultation with a doctor is advised within 48 hours."
        hindi_advice = "महत्वपूर्ण जोखिम संकेतक। 48 घंटे के भीतर डॉक्टर से परामर्श की सलाह दी जाती है।"
    else:
        severity = "CRITICAL"
        icon = "🚨"
        advice = "Severe physiological distress. Immediate medical intervention or hospital evaluation required."
        hindi_advice = "गंभीर स्थिति। तत्काल चिकित्सा सहायता या अस्पताल जाने की आवश्यकता है।"
        
    return {
        "risk_score": total_score,
        "severity": severity,
        "icon": icon,
        "advice": advice,
        "hindi_advice": hindi_advice,
        "details": {
            "anemia_component": round(anemia_points, 2),
            "symptom_component": round(symptom_points, 2),
            "steth_component": round(steth_points, 2),
            "vitals_component": round(vitals_points, 2)
        }
    }

if __name__ == "__main__":
    # Test healthy patient
    print("Normal Patient:")
    print(calculate_fusion_risk(0.15, 0.12, [], "Normal", 72, 98, 98.6))
    
    # Test critical patient
    print("\nCritical Patient:")
    print(calculate_fusion_risk(0.85, 0.78, ["fatigue", "dizziness", "breathless", "chest pain"], "Crackles", 112, 88, 101.5))
