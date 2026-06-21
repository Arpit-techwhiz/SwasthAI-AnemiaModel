"""
SwasthAI - Hindi Voice Assistant NLP Engine
Extracts clinical symptoms from Hindi and Hinglish voice transcripts.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

import re

# Mapping of Hindi/Hinglish and Regional Indian keywords to standardized English symptom tags
SYMPTOM_KEYWORD_MAPS = {
    "dizziness": [
        "chakkar", "chakar", "sar ghumna", "sir ghumna", "sir dard aur chakkar", "giddiness", "dizzy",
        "चक्कर", "सिर घूमना", "सर घूमना", "चक्कर येणे", "doke ghumne", "thalaichutru", "thalaivali", "தலைச்சுற்றல்",
        "thala thiruguta", "kallu thirugadam", "తల తిరగడం", "thale thiruguvudu", "ತಲೆ ತಿರುಗುವಿಕೆ", "matha ghora", "মাথা ঘোরা"
    ],
    "fatigue": [
        "thakan", "thakawat", "kamzori", "kamjori", "alas", "thak", "tired", "weakness", "fatigue",
        "थकान", "थकावट", "कमजोरी", "कमज़ोरी", "आलस", "कमजोर", "thakva", "ashaktapana", "थकवा", "अशक्तपणा",
        "soarvu", "பலவீனம்", "nirasam", "alasata", "నీరసం", "అలసట", "susthu", "alasike", "ಸುಸ್ತು", "ಆಲಸಿಕೆ",
        "klanti", "durbolta", "ক্লান্তি", "দুর্বলতা"
    ],
    "breathless": [
        "saans", "saas", "haapna", "hafna", "breathless", "shortness of breath", "saans phoolna",
        "सांस", "साँस", "हाफ", "हाफने", "सांस फूलना", "shwas", "dama lagne", "श्वास घ्यायला त्रास", "दम लागणे",
        "moochu thinaral", "moochuvanguthal", "மூச்சுத்திணறல்", "shwasa adakadam", "dumu", "శ్వాస ఆడకపోవడం",
        "ushiru kattuva", "ಉಸಿರಾಟದ தೊಂದರೆ", "hapa", "kosto", "হাঁপানির", "শ্বাসকষ্ট"
    ],
    "headache": [
        "sar dard", "sir dard", "sardard", "sirdard", "headache", "head ache",
        "सर दर्द", "सिर दर्द", "सरदर्द", "सिरदर्द", "doke dukhne", "डोकेदुखी", "thalai vali", "தலைவலி",
        "thala noppi", "తల నొప్పి", "thale noovu", "ತಲೆನೋವು", "matha betha", "মাথা ব্যথা"
    ],
    "pale skin": [
        "peela", "peeli", "peelapan", "white skin", "safed", "pale", "pallor",
        "पीला", "पीली", "पीलापन", "सफेद", "सफ़εδ", "pandharepadne", "पांढरे पडणे", "veluththal", "வெளுத்த சருமம்",
        "telipovatam", "పాలిపోవడం", "biḷupuvudu", "ಬಿಳುಚಿಕೊಳ್ಳುವುದು", "fika", "ফ্যাকাশে"
    ],
    "cold extremities": [
        "thande hath", "thanda per", "cold hands", "cold feet", "thande pair", "thanda hath", "thanda pair",
        "ठंडे हाथ", "ठंडे पैर", "हाथ पैर ठंडे", "हात पाय थंड", "kai kal kulirchi", "கை கால் குளிர்ச்சி",
        "kallu chethulu challaga", "కాళ్లు చేతులు చల్లబడటం", "kai kalu thandaguvudu", "ಕೈ காಲು ತಣ್ಣಗಾಗುವುದು",
        "hath pa thanda", "হাত পা ঠান্ডা"
    ],
    "chest pain": [
        "seene me dard", "seene me jalan", "chest pain", "seena dard", "chestpain",
        "छाती में दर्द", "सीने में दर्द", "सीना दर्द", "chati madhye dukhne", "छातीत दुखणे", "nenju vali", "நெஞ்சு வலி",
        "chathi noppi", "ఛాతి నొప్పి", "ede noovu", "ಎದೆ నోవు", "buke betha", "বুকে ব্যথা"
    ],
    "brittle nails": [
        "nakhun tutna", "nakhun kharab", "brittle nails", "brittlenails", "nakhun kamzor",
        "कमजोर नाखून", "नाखून टूटना", "नखे तुटणे", "nagam udayal", "நகங்கள் உடைவது",
        "gollu viruguta", "గోళ్లు విరిగిపోవడం", "uguru odeyuvudu", "ಉಗುರು ಒಡೆಯುವುದು", "nokh bhenge", "নখ ভেঙে যাওয়া"
    ],
    "hair loss": [
        "baal jhadna", "hair fall", "hair loss", "hairfall", "hairloss",
        "बाल झड़ना", "बालों का झड़ना", "बाल गिरना", "kese ghalne", "केस गळणे", "mudi kottuthal", "முடி உதிர்தல்",
        "ventrukalu udi", "జుట్టు రాలడం", "koodalu udiruvudu", "ಕೂದಲು ಉದುರುವಿಕೆ", "chul pora", "চুল পড়া"
    ],
    "loss of appetite": [
        "bhukh na lagna", "bhukh kam lagna", "loss of appetite", "loss of appetite", "bhukh kam",
        "भूख न लगना", "भूख कम लगना", "कम भूख", "bhuk na lagne", "भूख न लागणे", "basiyinmai", "பசியின்மை",
        "akali lekapovadam", "ఆకలి లేకపోవడం", "hasivagadiruvudu", "ಹಸಿವಾಗದಿರುವುದು", "khude manda", "খিদে না পাওয়া"
    ]
}

def extract_symptoms_from_text(text: str) -> list:
    """
    Parse text transcript of Hindi voice query.
    Returns a list of standardized symptom tags.
    """
    if not text:
        return []
        
    text_lower = text.lower().strip()
    extracted_symptoms = set()
    
    for symptom, keywords in SYMPTOM_KEYWORD_MAPS.items():
        for keyword in keywords:
            # Match keywords as words or substrings depending on characters
            if keyword in text_lower:
                extracted_symptoms.add(symptom)
                break # Move to next symptom category once matched
                
    return list(extracted_symptoms)

def get_hindi_response_for_symptoms(symptoms: list) -> str:
    """
    Generate dynamic spoken advice in Hindi based on identified symptoms.
    """
    if not symptoms:
        return "मुझे कोई लक्षण समझ नहीं आया। क्या आप फिर से बता सकते हैं?"
        
    advices = []
    if "fatigue" in symptoms or "pale skin" in symptoms:
        advices.append("कमजोरी और पीलापन खून की कमी (एनीमिया) के मुख्य लक्षण हैं।")
    if "dizziness" in symptoms:
        advices.append("चक्कर आना हीमोग्लोबिन की कमी का संकेत हो सकता है, कृपया अचानक न उठें।")
    if "breathless" in symptoms or "chest pain" in symptoms:
        advices.append("सांस फूलना और छाती में दर्द होना ऑक्सीजन की कमी या गंभीर एनीमिया का संकेत हो सकता है। तुरंत आराम करें।")
    if "cold extremities" in symptoms:
        advices.append("हाथ-पैर ठंडे होना रक्त परिसंचरण (circulation) की कमी दर्शाता है।")
    if "brittle nails" in symptoms:
        advices.append("नाखूनों का कमजोर होकर टूटना पोषण और आयरन की भारी कमी का सूचक है।")
    if "loss of appetite" in symptoms:
        advices.append("भूख कम लगना कमजोरी बढ़ाता है, थोड़ा-थोड़ा करके पौष्टिक भोजन लें।")
        
    advices.append("आपको आयरन युक्त भोजन जैसे पालक, दालें, और गुड़ का सेवन करना चाहिए और डॉक्टर से संपर्क करना चाहिए।")
    return " ".join(advices)

if __name__ == "__main__":
    test_phrases = [
        "मुझे बहुत थकान लग रही है और चक्कर आ रहे हैं।",
        "Chakkar aa raha hai aur saans phoolti hai",
        "मरीज का चेहरा पीला पड़ गया है और कमजोरी है।"
    ]
    for p in test_phrases:
        print(f"Text: {p}")
        print(f"Extracted: {extract_symptoms_from_text(p)}")
        print(f"Advice: {get_hindi_response_for_symptoms(extract_symptoms_from_text(p))}\n")
