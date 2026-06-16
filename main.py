"""
SwasthAI – Main Runner
========================
Run this to: generate data → train model → test inference → start API

Usage:
    python main.py --train       # Full pipeline
    python main.py --demo        # Demo inference on test images
    python main.py --api         # Start Flask API server
    python main.py --all         # Train + start API
"""

import argparse
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')
import json
import numpy as np
import cv2

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR  = os.path.join(BASE_DIR, "data")

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "utils"))


def run_training():
    print("\n" + "═" * 60)
    print("  SwasthAI – Anemia Detection AI  |  Training Pipeline")
    print("═" * 60)

    # Step 1: Generate dataset
    print("\n📸 Step 1: Generating synthetic training dataset...")
    from utils.generate_dataset import generate_dataset
    generate_dataset(BASE_DIR, n_train=300, n_val=80)

    # Step 2: Train model
    print("\n🧠 Step 2: Training CNN model...")
    from anemia_model import train_model
    model, metrics = train_model(
        data_dir=DATA_DIR,
        model_dir=MODEL_DIR,
    )

    print("\n" + "═" * 60)
    print("  ✅ TRAINING COMPLETE")
    print("═" * 60)
    print(f"  Accuracy  : {metrics.get('accuracy', 0):.4f}")
    print(f"  AUC       : {metrics.get('auc', 0):.4f}")
    print(f"  Precision : {metrics.get('precision', 0):.4f}")
    print(f"  Recall    : {metrics.get('recall', 0):.4f}")
    print("═" * 60)

    return model


def run_demo():
    print("\n" + "═" * 60)
    print("  SwasthAI – Demo Inference")
    print("═" * 60)

    # Find model
    tflite_path = os.path.join(MODEL_DIR, "swasthai_anemia.tflite")
    keras_path  = os.path.join(MODEL_DIR, "best_anemia_model.keras")

    if not os.path.exists(tflite_path) and not os.path.exists(keras_path):
        print("❌ No trained model found. Run: python main.py --train")
        return

    from anemia_model import AnemiaDetector
    from utils.generate_dataset import generate_conjunctiva_image, generate_fingernail_image

    model_path = tflite_path if os.path.exists(tflite_path) else keras_path
    detector   = AnemiaDetector(model_path)

    print("\n🔬 Running inference on 4 test cases:\n")

    test_cases = [
        ("Anemic patient – conjunctiva",    generate_conjunctiva_image(is_anemic=True),  True),
        ("Healthy patient – conjunctiva",   generate_conjunctiva_image(is_anemic=False), False),
        ("Anemic patient – fingernail",     generate_fingernail_image(is_anemic=True),   True),
        ("Healthy patient – fingernail",    generate_fingernail_image(is_anemic=False),  False),
    ]

    correct = 0
    for name, img, ground_truth in test_cases:
        result  = detector.predict_from_array(img)
        correct += (result["is_anemic"] == ground_truth)

        status = "✅ CORRECT" if result["is_anemic"] == ground_truth else "❌ WRONG"
        print(f"  {status} | {name}")
        print(f"          Probability: {result['anemia_probability']:.4f}")
        print(f"          Severity:    {result['icon']} {result['severity']}")
        print(f"          Hgb Est:     {result['hemoglobin_estimate']}")
        print(f"          Advice (HI): {result['hindi_advice']}")
        print()

    print(f"  Demo Accuracy: {correct}/4 ({correct * 25}%)")
    print("═" * 60)


def start_api():
    print("\n🌐 Starting SwasthAI API server...")
    os.chdir(BASE_DIR)
    sys.path.insert(0, os.path.join(BASE_DIR, "api"))
    from api.app import app, load_detector
    load_detector()
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SwasthAI Anemia Detection")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--demo",  action="store_true", help="Run demo inference")
    parser.add_argument("--api",   action="store_true", help="Start API server")
    parser.add_argument("--all",   action="store_true", help="Train + demo + API")
    args = parser.parse_args()

    if args.all or args.train:
        run_training()

    if args.all or args.demo:
        run_demo()

    if args.all or args.api:
        start_api()

    if not any(vars(args).values()):
        # Default: full pipeline
        run_training()
        run_demo()
