import os
import numpy as np
from tensorflow import keras

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "swasthai_anemia_final.keras")

print("Loading model:", MODEL_PATH)
model = keras.models.load_model(MODEL_PATH)
print("Model loaded.")

# Import the generator builder from repo
import sys
sys.path.insert(0, BASE_DIR)
from anemia_model import build_data_generators

_, val_gen = build_data_generators(DATA_DIR)
print(f"Validation samples: {val_gen.samples}")

# Evaluate with model.evaluate()
print('\nRunning model.evaluate()...')
results = model.evaluate(val_gen, verbose=1)
names = list(model.metrics_names)
metrics_map = dict(zip(names, results))
print('evaluate() results:')
for k, v in metrics_map.items():
    print(f"  {k}: {v}")

# Also compute scikit-learn metrics using predictions
try:
    from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
    print('\nRunning sklearn-based evaluation...')
    y_true = val_gen.classes
    # Predict probs
    y_pred_probs = model.predict(val_gen, verbose=1).ravel()
    y_pred = (y_pred_probs >= 0.5).astype(int)

    acc = accuracy_score(y_true, y_pred)
    try:
        auc = roc_auc_score(y_true, y_pred_probs)
    except Exception:
        auc = float('nan')
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)

    print(f"  Accuracy  : {acc:.4f}")
    print(f"  AUC       : {auc:.4f}")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
except Exception as e:
    print('sklearn evaluation failed:', e)

print('\nDone.')
