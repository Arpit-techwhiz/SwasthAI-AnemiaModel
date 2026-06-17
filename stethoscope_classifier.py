"""
SwasthAI - Smart Stethoscope Audio Classifier & Simulator
Classifies lung/heart sounds and generates realistic synthetic audio samples.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

import os
import wave
import struct
import math
import numpy as np

STATIC_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api", "static", "audio")

class StethoscopeClassifier:
    """Classifies breathing sounds from WAV audio files using spectral analysis."""
    
    @staticmethod
    def analyze_wav(file_path: str) -> dict:
        """
        Analyze WAV audio data to classify breathing sounds: Normal, Wheezing, or Crackles.
        """
        if not os.path.exists(file_path):
            return {"error": "Audio file not found", "class": "None"}
            
        try:
            with wave.open(file_path, 'rb') as wav:
                params = wav.getparams()
                n_channels, sampwidth, framerate, n_frames = params[:4]
                
                # Check formatting
                if sampwidth not in [1, 2]:
                    return {"error": "Unsupported sample width (only 8 or 16-bit supported)", "class": "None"}
                
                # Read frames
                raw_data = wav.readframes(n_frames)
                
                # Convert binary data to numpy array
                if sampwidth == 2:
                    data = np.frombuffer(raw_data, dtype=np.int16)
                else:
                    data = np.frombuffer(raw_data, dtype=np.uint8).astype(np.int16) - 128
                    
                # If multi-channel, average to mono
                if n_channels > 1:
                    data = data.reshape(-1, n_channels).mean(axis=1)
                    
                if len(data) == 0:
                    return {"class": "Normal", "confidence": 0.5, "details": "Silent file"}
                
                # ── FEATURE EXTRACTION ──
                # 1. Zero Crossing Rate (ZCR) - high ZCR correlates with crackles/high noise
                zero_crossings = np.nonzero(np.diff(data > 0))[0]
                zcr = len(zero_crossings) / len(data)
                
                # 2. Spectral Analysis (FFT) - wheezing has high energy in 400-1200 Hz
                fft_data = np.fft.fft(data)
                fft_freqs = np.fft.fftfreq(len(data), 1.0 / framerate)
                
                # Keep positive frequencies
                pos_indices = np.where(fft_freqs > 0)[0]
                freqs = fft_freqs[pos_indices]
                magnitudes = np.abs(fft_data[pos_indices])
                
                # Energy in specific bands
                low_band = np.where((freqs >= 50) & (freqs < 300))[0]
                wheeze_band = np.where((freqs >= 400) & (freqs < 1200))[0]
                high_band = np.where(freqs >= 1500)[0]
                
                low_energy = np.sum(magnitudes[low_band]) if len(low_band) > 0 else 1.0
                wheeze_energy = np.sum(magnitudes[wheeze_band]) if len(wheeze_band) > 0 else 0.0
                high_energy = np.sum(magnitudes[high_band]) if len(high_band) > 0 else 0.0
                
                total_energy = low_energy + wheeze_energy + high_energy
                wheeze_ratio = wheeze_energy / (total_energy + 1e-6)
                high_ratio = high_energy / (total_energy + 1e-6)
                
                # 3. Peak Transient analysis - crackles have sharp, short peaks
                # Calculate rolling envelope variance
                frame_size = int(framerate * 0.02) # 20ms frames
                if frame_size > 0:
                    num_frames = len(data) // frame_size
                    frame_peaks = []
                    for i in range(num_frames):
                        frame = data[i*frame_size : (i+1)*frame_size]
                        frame_peaks.append(np.max(np.abs(frame)))
                    
                    frame_peaks = np.array(frame_peaks)
                    peak_std = np.std(frame_peaks) / (np.mean(frame_peaks) + 1e-6)
                else:
                    peak_std = 0.0
                
                # ── CLASSIFICATION HEURISTICS ──
                # Wheezing: high proportion of energy in the 400-1200 Hz musical range
                # Crackles: high variance in peaks (short bursts) + higher zero crossings
                if wheeze_ratio > 0.35 and wheeze_ratio > high_ratio:
                    classification = "Wheezing"
                    confidence = min(0.5 + wheeze_ratio * 0.5, 0.98)
                    details = "Continuous high-pitched musical sound indicating airway restriction (Asthma/COPD)."
                elif peak_std > 1.2 or (zcr > 0.08 and peak_std > 0.8):
                    classification = "Crackles"
                    confidence = min(0.5 + peak_std * 0.2, 0.95)
                    details = "Discontinuous, bubbling or clicking sounds indicating fluid in the lungs (Pneumonia/Bronchitis)."
                else:
                    classification = "Normal"
                    confidence = 0.90
                    details = "Healthy vesicular breathing. Regular low-frequency respiratory cycle."
                    
                return {
                    "class": classification,
                    "confidence": round(float(confidence), 2),
                    "details": details,
                    "metrics": {
                        "zcr": round(float(zcr), 4),
                        "wheeze_ratio": round(float(wheeze_ratio), 4),
                        "peak_variance": round(float(peak_std), 4)
                    }
                }
        except Exception as e:
            return {"error": f"Audio processing error: {str(e)}", "class": "None"}


def generate_synthesized_samples():
    """Generate mock lung sound WAV files so user has files to test immediately."""
    os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)
    
    sample_rate = 8000
    duration = 4.0 # 4 seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # 1. Normal Lung Audio: Slow cyclic breathing (100 Hz carrier, modulated at 0.25 Hz)
    breath_cycle = 0.5 * (1 + np.sin(2 * np.pi * 0.25 * t)) # breathing envelope
    normal_wave = 0.6 * breath_cycle * np.sin(2 * np.pi * 120 * t)
    # Add low-frequency chest noise
    normal_wave += 0.2 * np.random.normal(0, 0.5, len(t))
    normal_wave = np.clip(normal_wave * 32767, -32768, 32767).astype(np.int16)
    
    write_wav(os.path.join(STATIC_AUDIO_DIR, "normal_lung.wav"), normal_wave, sample_rate)
    
    # 2. Wheezing Lung Audio: Cyclic breathing + 600 Hz whistle during inhale
    inhale_phase = np.sin(2 * np.pi * 0.25 * t) > 0.0
    whistle = 0.45 * np.sin(2 * np.pi * 580 * t) * inhale_phase
    wheeze_wave = 0.4 * breath_cycle * np.sin(2 * np.pi * 120 * t) + whistle
    wheeze_wave += 0.1 * np.random.normal(0, 0.3, len(t))
    wheeze_wave = np.clip(wheeze_wave * 32767, -32768, 32767).astype(np.int16)
    
    write_wav(os.path.join(STATIC_AUDIO_DIR, "wheezing_lung.wav"), wheeze_wave, sample_rate)
    
    # 3. Crackles Lung Audio: Cyclic breathing + short random clicking transients
    crackles_wave = 0.4 * breath_cycle * np.sin(2 * np.pi * 120 * t)
    # Add clicks
    click_density = 0.003
    for idx in range(len(t)):
        if inhale_phase[idx] and np.random.random() < click_density:
            # Generate short impulse spike
            spike_len = min(80, len(t) - idx)
            for j in range(spike_len):
                crackles_wave[idx + j] += 0.95 * np.sin(2 * np.pi * 350 * (j / sample_rate)) * math.exp(-0.1 * j)
                
    crackles_wave += 0.1 * np.random.normal(0, 0.3, len(t))
    crackles_wave = np.clip(crackles_wave * 32767, -32768, 32767).astype(np.int16)
    
    write_wav(os.path.join(STATIC_AUDIO_DIR, "crackles_lung.wav"), crackles_wave, sample_rate)
    print("🎵 Synthetic lung audio samples generated in static/audio/")

def write_wav(file_path, data_array, sample_rate):
    with wave.open(file_path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2) # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(data_array.tobytes())

if __name__ == "__main__":
    generate_synthesized_samples()
    # Test analysis
    for name in ["normal_lung.wav", "wheezing_lung.wav", "crackles_lung.wav"]:
        path = os.path.join(STATIC_AUDIO_DIR, name)
        res = StethoscopeClassifier.analyze_wav(path)
        print(f"Sample {name} classified as: {res['class']} (conf: {res['confidence']})")
