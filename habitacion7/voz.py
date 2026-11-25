"""Genera la narración con Kokoro TTS (local, gratis) y guarda tiempos por segmento."""
import json, sys, os
import numpy as np, soundfile as sf
from scipy.signal import butter, lfilter
from kokoro_onnx import Kokoro
from guion import SEGMENTOS, VOZ_TELEFONO

MODELS = sys.argv[1]          # carpeta con kokoro-v1.0.onnx y voices-v1.0.bin
OUT = sys.argv[2]             # carpeta de salida
VOICE, SPEED, SR = "em_alex", 0.9, 24000
LEAD = 0.6                    # silencio inicial

k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))

def bandpass(x, lo, hi):
    b, a = butter(4, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)

pieces, timings, t = [np.zeros(int(LEAD * SR))], [], LEAD
for scene, text, pause in SEGMENTOS:
    audio, sr = k.create(text, voice=VOICE, speed=SPEED, lang="es")
    assert sr == SR
    audio = audio.astype(np.float32)
    # recortar silencios de los bordes
    idx = np.where(np.abs(audio) > 0.01)[0]
    audio = audio[max(idx[0] - 600, 0): idx[-1] + 1200]
    if text in VOZ_TELEFONO:  # su propia voz por el teléfono: banda estrecha + leve distorsión
        audio = np.tanh(bandpass(audio, 350, 3200) * 2.2) * 0.8
    dur = len(audio) / SR
    timings.append({"scene": scene, "text": text, "start": round(t, 3), "end": round(t + dur, 3),
                    "phone": text in VOZ_TELEFONO})
    pieces += [audio, np.zeros(int(pause * SR))]
    t += dur + pause

voice = np.concatenate(pieces)
voice = voice / (np.abs(voice).max() + 1e-9) * 0.9
sf.write(os.path.join(OUT, "voz.wav"), voice, SR)
json.dump({"duration": round(len(voice) / SR, 3), "segments": timings},
          open(os.path.join(OUT, "tiempos.json"), "w"), ensure_ascii=False, indent=1)
print("duración total:", round(len(voice) / SR, 2), "s")
