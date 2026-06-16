"""
SwasthAI – Anemia Detection CNN Model
=======================================
Architecture: MobileNetV2 Transfer Learning + Custom Head
Input: 224x224 RGB image (conjunctiva or fingernail)
Output: Anemia probability (0.0 – 1.0) + severity level

Clinical basis:
  - Anemic patients have reduced hemoglobin → pale conjunctiva & nail beds
  - CNN learns color/texture features correlated with hemoglobin levels
  - Validated approach: doi.org/10.1038/s41746-020-0253-3
"""

import numpy as np
import os
import json



# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
IMG_SIZE    = 224
BATCH_SIZE  = 16
EPOCHS      = 30
LR          = 1e-4
NUM_CLASSES = 1          # Binary: anemic / non-anemic
MODEL_DIR   = "models"


# ──────────────────────────────────────────────
# DATA PIPELINE
# ──────────────────────────────────────────────
def build_data_generators(data_dir: str):
    """
    Build augmented training and validation data generators.
    Augmentation simulates real-world phone camera conditions:
      - Rotation: phone held at angles
      - Brightness: different lighting / outdoors
      - Zoom: distance from eye/finger varies
      - Flip: left/right hand, left/right eye
    """
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    train_datagen = ImageDataGenerator(
        rescale=1.0 / 255,
        rotation_range=20,
        width_shift_range=0.15,
        height_shift_range=0.15,
        brightness_range=[0.6, 1.4],   # Key: simulate different lighting
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode="nearest",
        channel_shift_range=20.0,      # Simulate white balance variation
    )

    val_datagen = ImageDataGenerator(rescale=1.0 / 255)

    train_gen = train_datagen.flow_from_directory(
        os.path.join(data_dir, "train"),
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode="binary",
        shuffle=True,
        seed=42,
    )

    val_gen = val_datagen.flow_from_directory(
        os.path.join(data_dir, "val"),
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode="binary",
        shuffle=False,
    )

    return train_gen, val_gen


# ──────────────────────────────────────────────
# MODEL ARCHITECTURE
# ──────────────────────────────────────────────
def build_anemia_model(fine_tune_layers: int = 30):
    """
    MobileNetV2 Transfer Learning for Anemia Detection.

    Why MobileNetV2?
      - Lightweight (3.4M params) → runs on TensorFlow Lite / mobile
      - Pre-trained on ImageNet → strong low-level feature extraction
      - Depthwise separable convolutions → fast on edge devices

    Architecture:
      MobileNetV2 (frozen base)
        → Global Average Pooling
        → Dropout(0.4)
        → Dense(256, ReLU) + BatchNorm
        → Dropout(0.3)
        → Dense(64, ReLU)
        → Dense(1, Sigmoid)  → Anemia probability
    """
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, Model
    from tensorflow.keras.applications import MobileNetV2

    # Base model — ImageNet pretrained
    base_model = MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights="imagenet",
    )

    # Freeze all layers initially
    base_model.trainable = False

    # Unfreeze last N layers for fine-tuning
    if fine_tune_layers > 0:
        for layer in base_model.layers[-fine_tune_layers:]:
            layer.trainable = True

    # ── Custom classification head ──
    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="image_input")

    # Preprocessing: MobileNetV2 expects [-1, 1] scaled inputs
    x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs * 255.0)

    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D(name="gap")(x)

    x = layers.Dropout(0.4, name="dropout_1")(x)
    x = layers.Dense(256, activation="relu", name="dense_256")(x)
    x = layers.BatchNormalization(name="bn_256")(x)

    x = layers.Dropout(0.3, name="dropout_2")(x)
    x = layers.Dense(64, activation="relu", name="dense_64")(x)

    # Output: probability of anemia
    output = layers.Dense(1, activation="sigmoid", name="anemia_probability")(x)

    model = Model(inputs=inputs, outputs=output, name="SwasthAI_AnemiaDetector")
    return model


# ──────────────────────────────────────────────
# TRAINING
# ──────────────────────────────────────────────
def train_model(data_dir: str, model_dir: str = MODEL_DIR):
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau

    os.makedirs(model_dir, exist_ok=True)

    print("\n🔬 SwasthAI – Anemia Detection Model Training")
    print("=" * 55)

    # Data
    print("\n📦 Loading dataset...")
    train_gen, val_gen = build_data_generators(data_dir)
    print(f"   Train: {train_gen.samples} images | Val: {val_gen.samples} images")
    print(f"   Classes: {train_gen.class_indices}")

    # Model
    print("\n🧠 Building MobileNetV2 model...")
    model = build_anemia_model(fine_tune_layers=30)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            keras.metrics.AUC(name="auc"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
        ],
    )

    trainable = sum(p.numpy().size for p in model.trainable_variables)
    total     = sum(p.numpy().size for p in model.variables)
    print(f"   Trainable params: {trainable:,} / {total:,}")

    # Callbacks
    callbacks = [
        ModelCheckpoint(
            filepath=os.path.join(model_dir, "best_anemia_model.keras"),
            monitor="val_auc",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        EarlyStopping(
            monitor="val_auc",
            patience=8,
            mode="max",
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.4,
            patience=4,
            min_lr=1e-7,
            verbose=1,
        ),
    ]

    # ── Phase 1: Train head only ──
    print("\n🚀 Phase 1: Training classification head (base frozen)...")
    base = model.get_layer("mobilenetv2_1.00_224")
    base.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss="binary_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc"),
                 keras.metrics.Precision(name="precision"),
                 keras.metrics.Recall(name="recall")],
    )

    history1 = model.fit(
        train_gen,
        epochs=15,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1,
    )

    # ── Phase 2: Fine-tune top layers ──
    print("\n🔧 Phase 2: Fine-tuning top 30 MobileNetV2 layers...")
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR / 10),
        loss="binary_crossentropy",
        metrics=["accuracy", keras.metrics.AUC(name="auc"),
                 keras.metrics.Precision(name="precision"),
                 keras.metrics.Recall(name="recall")],
    )

    history2 = model.fit(
        train_gen,
        epochs=EPOCHS,
        initial_epoch=15,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1,
    )

    # ── Save final model ──
    final_path = os.path.join(model_dir, "swasthai_anemia_final.keras")
    model.save(final_path)
    print(f"\n✅ Model saved: {final_path}")

    # ── Export to TFLite (for mobile/Raspberry Pi) ──
    print("\n📱 Exporting TensorFlow Lite model...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_model = converter.convert()

    tflite_path = os.path.join(model_dir, "swasthai_anemia.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"✅ TFLite model saved: {tflite_path}")
    print(f"   Size: {os.path.getsize(tflite_path) / 1024:.1f} KB")

    # ── Save class map ──
    meta = {
        "classes": train_gen.class_indices,
        "img_size": IMG_SIZE,
        "model_version": "1.0.0",
        "architecture": "MobileNetV2 + Custom Head",
        "threshold": 0.5,
    }
    with open(os.path.join(model_dir, "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # ── Final metrics ──
    print("\n📊 Evaluating on validation set...")
    
    # Get ground truth labels
    y_true = val_gen.classes
    
    # Predict probabilities on validation set
    y_pred_probs = model.predict(val_gen, verbose=0).ravel()
    y_pred = (y_pred_probs >= 0.5).astype(int)
    
    # Compute metrics using sklearn
    from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
    
    accuracy = float(accuracy_score(y_true, y_pred))
    auc = float(roc_auc_score(y_true, y_pred_probs))
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    
    metrics = {
        'accuracy': accuracy,
        'auc': auc,
        'precision': precision,
        'recall': recall,
    }
    
    print(f"   Accuracy  : {accuracy:.4f}")
    print(f"   AUC       : {auc:.4f}")
    print(f"   Precision : {precision:.4f}")
    print(f"   Recall    : {recall:.4f}")

    return model, metrics


# ──────────────────────────────────────────────
# INFERENCE ENGINE
# ──────────────────────────────────────────────
class AnemiaDetector:
    """
    Production inference class for SwasthAI anemia detection.
    Supports both Keras and TFLite models.

    Usage:
        detector = AnemiaDetector("models/swasthai_anemia.tflite")
        result = detector.predict_from_path("patient_eye.jpg")
        print(result)
    """

    SEVERITY_LEVELS = {
        (0.0, 0.3):  ("LOW RISK",      "✅", "Hemoglobin likely normal. No immediate concern."),
        (0.3, 0.55): ("MODERATE RISK", "⚠️", "Possible mild anemia. Recommend blood test."),
        (0.55, 0.75):("HIGH RISK",     "🔴", "Likely anemia. Urgent CBC test recommended."),
        (0.75, 1.0): ("CRITICAL",      "🚨", "Severe anemia suspected. Immediate medical care."),
    }

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.use_tflite = model_path.endswith(".tflite")

        if self.use_tflite:
            try:
                import tflite_runtime.interpreter as tflite
                self.interpreter = tflite.Interpreter(model_path=model_path)
            except ImportError:
                import tensorflow as tf
                self.interpreter = tf.lite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details  = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
        else:
            from tensorflow import keras
            self.model = keras.models.load_model(model_path)

        print(f"✅ AnemiaDetector loaded: {'TFLite' if self.use_tflite else 'Keras'}")

    def preprocess(self, image_path: str) -> np.ndarray:
        """Load, resize, normalize image for inference."""
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        img = img.astype(np.float32) / 255.0
        return np.expand_dims(img, axis=0)  # (1, 224, 224, 3)

    def _run_tflite(self, input_data: np.ndarray) -> float:
        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()
        return float(self.interpreter.get_tensor(self.output_details[0]["index"])[0][0])

    def _run_keras(self, input_data: np.ndarray) -> float:
        return float(self.model.predict(input_data, verbose=0)[0][0])

    def get_severity(self, prob: float) -> dict:
        for (low, high), (level, icon, advice) in self.SEVERITY_LEVELS.items():
            if low <= prob < high:
                return {"level": level, "icon": icon, "advice": advice}
        return {"level": "CRITICAL", "icon": "🚨", "advice": "Severe anemia suspected."}

    def predict_from_path(self, image_path: str) -> dict:
        """
        Run anemia detection on an image file.
        Returns structured result dict.
        """
        input_data = self.preprocess(image_path)

        if self.use_tflite:
            prob = self._run_tflite(input_data)
        else:
            prob = self._run_keras(input_data)

        severity = self.get_severity(prob)
        is_anemic = prob >= 0.5

        return {
            "anemia_probability": round(prob, 4),
            "is_anemic": is_anemic,
            "confidence": round(max(prob, 1 - prob) * 100, 1),
            "severity": severity["level"],
            "icon": severity["icon"],
            "advice": severity["advice"],
            "hindi_advice": self._get_hindi_advice(severity["level"]),
            "hemoglobin_estimate": self._estimate_hemoglobin(prob),
        }

    def predict_from_array(self, img_array: np.ndarray) -> dict:
        """Run prediction on a pre-loaded numpy array (for Flask/API)."""
        import cv2
        img = cv2.resize(img_array, (IMG_SIZE, IMG_SIZE))
        img = img.astype(np.float32) / 255.0
        input_data = np.expand_dims(img, axis=0)

        if self.use_tflite:
            prob = self._run_tflite(input_data)
        else:
            prob = self._run_keras(input_data)

        severity = self.get_severity(prob)
        return {
            "anemia_probability": round(prob, 4),
            "is_anemic": prob >= 0.5,
            "confidence": round(max(prob, 1 - prob) * 100, 1),
            "severity": severity["level"],
            "icon": severity["icon"],
            "advice": severity["advice"],
            "hindi_advice": self._get_hindi_advice(severity["level"]),
            "hemoglobin_estimate": self._estimate_hemoglobin(prob),
        }

    def _get_hindi_advice(self, severity: str) -> str:
        advice_map = {
            "LOW RISK":      "आपका स्वास्थ्य सामान्य है। स्वस्थ आहार लेते रहें।",
            "MODERATE RISK": "हल्की खून की कमी हो सकती है। खून की जांच करवाएं।",
            "HIGH RISK":     "खून की कमी की संभावना है। तुरंत डॉक्टर से मिलें।",
            "CRITICAL":      "गंभीर खून की कमी। अभी अस्पताल जाएं!",
        }
        return advice_map.get(severity, "")

    def _estimate_hemoglobin(self, prob: float) -> str:
        """
        Rough hemoglobin estimate based on anemia probability.
        Normal: Men >13 g/dL, Women >12 g/dL
        """
        if prob < 0.3:
            return "~12–16 g/dL (Normal range)"
        elif prob < 0.55:
            return "~10–12 g/dL (Mild anemia)"
        elif prob < 0.75:
            return "~7–10 g/dL (Moderate anemia)"
        else:
            return "<7 g/dL (Severe anemia)"


if __name__ == "__main__":
    import sys

    base_dir = "/home/claude/swasthai"

    # Generate synthetic dataset
    print("📸 Generating synthetic training dataset...")
    sys.path.insert(0, os.path.join(base_dir, "utils"))
    from generate_dataset import generate_dataset
    generate_dataset(base_dir, n_train=300, n_val=80)

    # Train model
    model, metrics = train_model(
        data_dir=os.path.join(base_dir, "data"),
        model_dir=os.path.join(base_dir, "models"),
    )
    print("\n🎉 Training complete!")
