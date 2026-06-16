"""
SwasthAI – Synthetic Dataset Generator
Generates realistic synthetic eye/fingernail images for anemia detection training.
In production, replace with real clinical images from hospitals.
"""

import numpy as np
import cv2
import os
import random

def generate_conjunctiva_image(is_anemic: bool, img_size=224) -> np.ndarray:
    """
    Generate synthetic conjunctiva (inner eyelid) image.
    Anemic: pale pink / whitish tones (low hemoglobin = less red blood cells)
    Normal: deep red/pink tones (healthy vascularity)
    """
    img = np.zeros((img_size, img_size, 3), dtype=np.uint8)

    if is_anemic:
        # Pale pink / whitish — low hemoglobin
        base_r = random.randint(210, 245)
        base_g = random.randint(170, 200)
        base_b = random.randint(160, 195)
    else:
        # Deep red/pink — healthy
        base_r = random.randint(195, 230)
        base_g = random.randint(80, 130)
        base_b = random.randint(85, 130)

    img[:] = (base_b, base_g, base_r)  # BGR

    # Add texture — vascular pattern
    for _ in range(random.randint(8, 18)):
        x1, y1 = random.randint(0, img_size), random.randint(0, img_size)
        x2, y2 = x1 + random.randint(-60, 60), y1 + random.randint(-60, 60)
        if is_anemic:
            color = (random.randint(180, 210), random.randint(140, 170), random.randint(190, 225))
        else:
            color = (random.randint(60, 100), random.randint(40, 80), random.randint(160, 200))
        cv2.line(img, (x1, y1), (x2, y2), color, random.randint(1, 2))

    # Blur to simulate real tissue appearance
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Add slight noise
    noise = np.random.normal(0, 8, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def generate_fingernail_image(is_anemic: bool, img_size=224) -> np.ndarray:
    """
    Generate synthetic fingernail bed image.
    Anemic: pale/white nail bed
    Normal: pink nail bed with healthy capillary return
    """
    img = np.zeros((img_size, img_size, 3), dtype=np.uint8)

    if is_anemic:
        base_r = random.randint(215, 250)
        base_g = random.randint(190, 220)
        base_b = random.randint(185, 215)
    else:
        base_r = random.randint(210, 240)
        base_g = random.randint(120, 160)
        base_b = random.randint(120, 155)

    # Nail bed ellipse
    cx, cy = img_size // 2, img_size // 2
    cv2.ellipse(img, (cx, cy), (90, 70), 0, 0, 360, (base_b, base_g, base_r), -1)

    # Nail cuticle
    cuticle_color = (base_b - 15, base_g - 15, base_r - 15)
    cv2.ellipse(img, (cx, cy - 50), (55, 20), 0, 0, 360, cuticle_color, -1)

    # Highlight shine
    cv2.ellipse(img, (cx - 20, cy - 20), (25, 12), -30, 0, 360,
                (min(base_b + 40, 255), min(base_g + 40, 255), min(base_r + 40, 255)), -1)

    img = cv2.GaussianBlur(img, (7, 7), 0)
    noise = np.random.normal(0, 6, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def generate_dataset(base_dir: str, n_train=400, n_val=100):
    """Generate full training + validation dataset."""
    splits = {
        "train": n_train,
        "val": n_val,
    }

    total = 0
    for split, count in splits.items():
        for label in ["anemic", "non_anemic"]:
            out_dir = os.path.join(base_dir, "data", split, label)
            os.makedirs(out_dir, exist_ok=True)
            is_anemic = (label == "anemic")

            for i in range(count):
                # Alternate between conjunctiva and fingernail images
                if i % 2 == 0:
                    img = generate_conjunctiva_image(is_anemic)
                    prefix = "conj"
                else:
                    img = generate_fingernail_image(is_anemic)
                    prefix = "nail"

                filename = f"{prefix}_{label}_{i:04d}.jpg"
                cv2.imwrite(os.path.join(out_dir, filename), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
                total += 1

        print(f"  ✅ {split}: {count * 2} images per class generated")

    print(f"\n📦 Total images generated: {total * 2}")
    print(f"📁 Saved to: {base_dir}/data/")


if __name__ == "__main__":
    generate_dataset("/home/claude/swasthai")
