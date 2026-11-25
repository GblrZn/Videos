"""Diseño de sonido 100% sintetizado + mezcla con la narración.
Uso: python3 sonido.py <build_dir>   (lee voz.wav y tiempos.json, escribe mezcla.wav)"""
import json, sys, os
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly, fftconvolve

B = sys.argv[1]
SR = 48000
rng = np.random.default_rng(7)
tm = json.load(open(os.path.join(B, "tiempos.json")))
SEG = tm["segments"]
TOTAL = tm["duration"] + 3.0            # cola para la pantalla de elección
N = int(TOTAL * SR)
t = np.arange(N) / SR

def scene_span(name):
    s = [x for x in SEG if x["scene"] == name]
    return s[0]["start"], s[-1]["end"]

def filt(x, kind, f, order=4):
    f = np.atleast_1d(f) / (SR / 2)
    return sosfilt(butter(order, f if len(f) > 1 else f[0], btype=kind, output="sos"), x)

def env(a, b, fade=0.5):
    """envolvente 0..1 activa entre a y b con fades"""
    e = np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1)
    return e

def place(buf, clip, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf): return
    clip = clip[: len(buf) - i]
    buf[i:i + len(clip)] += clip * gain

def reverb(x, secs=1.8, wet=0.35, damp=3000):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / secs))
    ir = filt(ir, "low", damp)
    y = fftconvolve(x, ir)[: len(x)]
    y /= np.abs(y).max() + 1e-9
    return x * (1 - wet) + y * wet * np.abs(x).max()

noise = rng.standard_normal(N)

# ---------- capas ambientales ----------
pre_cam = scene_span("camaras")[0]
pas0 = scene_span("pasillo")[0]
cel0, cel1 = scene_span("celular")
ele0 = scene_span("eleccion")[0]

# lluvia: ruido filtrado + gotas
rain = filt(noise, "band", [400, 7000]) * 0.5 + filt(noise, "low", 300) * 0.6
drops = np.zeros(N)
for _ in range(int(TOTAL * 60)):
    place(drops, np.exp(-np.arange(300) / 40) * rng.standard_normal(300), rng.uniform(0, TOTAL), rng.uniform(.05, .25))
rain = rain + filt(drops, "high", 1500)
rain_lvl = 0.10 * env(0, pre_cam + 1, 0.8) + 0.035 * env(pre_cam, ele0, 1.5) + 0.08 * env(ele0, TOTAL + 1, 1)
rain_lvl += 0.05 * env(scene_span("motel")[0] - .3, scene_span("motel")[1] + .3, .6)  # exterior más fuerte
amb = rain * rain_lvl

# zumbido fluorescente 60 Hz con armónicos y parpadeos
hum = sum(np.sin(2 * np.pi * 60 * h * t) / h for h in (1, 2, 3, 5, 7)) + filt(noise, "band", [2000, 6000]) * 0.15
flick = np.ones(N)
for _ in range(60):
    a = rng.uniform(0, TOTAL); d = rng.uniform(.04, .25)
    flick[int(a * SR):int((a + d) * SR)] = rng.uniform(0, .3)
hum_lvl = 0.018 * env(scene_span("recepcion")[0] - .5, cel1 + 1, .6)
amb += hum * flick * hum_lvl

# drone de tensión: sube progresivamente
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.7 * np.sin(2 * np.pi * 41.9 * t)
         + 0.4 * np.sin(2 * np.pi * 82.4 * t + 2 * np.sin(2 * np.pi * .1 * t))
         + 0.25 * filt(noise, "band", [90, 220]))
tension = np.clip(t / tm["duration"], 0, 1) ** 1.3
amb += drone * (0.05 + 0.16 * tension) * np.clip(t / 1.5, 0, 1) * (1 - 0.85 * env(ele0 + .3, TOTAL + 2, .3))

# ---------- efectos puntuales ----------
fx = np.zeros(N)

def ring_old(dur=1.6, f1=700, f2=1020):
    tt = np.arange(int(dur * SR)) / SR
    am = (np.sin(2 * np.pi * 20 * tt) > 0).astype(float)          # campana electromecánica
    tone = (np.sin(2 * np.pi * f1 * tt) + np.sin(2 * np.pi * f2 * tt) + .3 * np.sin(2 * np.pi * 2730 * tt))
    return tone * am * np.clip(tt / .02, 0, 1) * np.clip((dur - tt) / .05, 0, 1) * 0.25

def impact():
    n = int(3.5 * SR); tt = np.arange(n) / SR
    sweep = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-tt * 3)) / SR) * np.exp(-tt * 1.2)
    burst = filt(rng.standard_normal(n), "low", 900) * np.exp(-tt * 9)
    return reverb(sweep * 0.9 + burst * 0.6, 2.5, 0.4)

def riser(dur=1.6):
    tt = np.arange(int(dur * SR)) / SR
    x = filt(rng.standard_normal(len(tt)), "band", [800, 6000]) * (tt / dur) ** 3
    return x * 0.5

def static_burst(dur=0.18):
    n = int(dur * SR)
    return filt(rng.standard_normal(n), "band", [1200, 7000]) * np.exp(-np.arange(n) / n * 2) * 0.35

# teléfono de recepción: suena 2 veces antes de "sonó el teléfono"
rec0 = scene_span("recepcion")[0]
for k in range(2):
    place(fx, ring_old(), rec0 - 0.4 + k * 2.4, 0.55)

# respiración al otro lado de la línea (banda telefónica)
tel0, tel1 = scene_span("telefono")
br = filt(noise, "band", [500, 2200]) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.32 * t - 1)) ** 3
amb += br * 0.07 * env(tel0 + 0.6, tel1 + 0.4, .4)
# susurro: ráfaga sibilante con reverb
wh = filt(rng.standard_normal(int(1.4 * SR)), "band", [2500, 7500]) * np.hanning(int(1.4 * SR))
place(fx, reverb(wh, 1.5, .5) * 0.25, SEG[7]["end"] - 0.6)

# golpes (stingers)
place(fx, riser(), 5.5 - 1.6, 0.5); place(fx, impact(), 5.5, 0.9)         # "desde la siete"
for s in SEG:
    if "oxidado" in s["text"]:
        place(fx, riser(), s["end"] - 0.6 - 1.6, 0.4); place(fx, impact(), s["end"] - 0.6, 0.8)
    if "era la mía" in s["text"]:
        place(fx, riser(2.2), s["end"] - 0.5 - 2.2, 0.6); place(fx, impact(), s["end"] - 0.4, 1.0)

# estática en cada corte de escena
scenes = []
for s in SEG:
    if not scenes or scenes[-1][0] != s["scene"]:
        scenes.append((s["scene"], s["start"]))
for name, st in scenes[1:]:
    place(fx, static_burst(), st - 0.35, 0.8)

# pasos en el pasillo (con eco)
p0, p1 = scene_span("pasillo")
steps = np.zeros(N)
x = p0 - 0.3
while x < p1 + 0.6:
    n = int(0.12 * SR); tt = np.arange(n) / SR
    step = filt(rng.standard_normal(n), "low", 700) * np.exp(-tt * 40) + np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 30)
    place(steps, step, x, 0.5)
    x += 0.62
fx += reverb(steps, 1.4, .45)

# latido: desde el pasillo hasta el final de la llamada, acelerando
hb = np.zeros(N)
x = p0
while x < cel1 + 0.5:
    n = int(0.15 * SR); tt = np.arange(n) / SR
    beat = np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 25)
    place(hb, beat, x, 0.7); place(hb, beat, x + 0.22, 0.45)
    prog = (x - p0) / (cel1 - p0)
    x += 0.95 - 0.35 * prog
fx += filt(hb, "low", 160)

# teléfono sonando DENTRO de la habitación 7 (lejano, con reverb)
pu0, pu1 = scene_span("puerta")
far = np.zeros(N)
for k in range(3):
    place(far, ring_old(1.3), pu0 + 0.4 + k * 2.2, 1)
fx += reverb(filt(far, "band", [300, 2500]), 2.2, .6) * 0.25

# vibración del celular
vib = np.zeros(N)
for k in range(3):
    n = int(0.45 * SR); tt = np.arange(n) / SR
    v = np.sin(2 * np.pi * 165 * tt) * (1 + 0.5 * np.sign(np.sin(2 * np.pi * 330 * tt))) * np.hanning(n)
    place(vib, v, cel0 - 0.2 + k * 0.85, 0.22)
fx += vib

# silencio casi total antes de "no entres" -> y tic-tac en la elección
for s in SEG:
    if s["phone"]:
        amb *= 1 - 0.75 * env(s["start"] - .2, s["end"] + .3, .15)
tick = np.zeros(N)
x = ele0
while x < TOTAL - 0.2:
    n = int(0.03 * SR)
    place(tick, filt(rng.standard_normal(n), "band", [2000, 5000]) * np.hanning(n), x, 0.35)
    x += 0.5
fx += tick

# ---------- voz ----------
v, vsr = sf.read(os.path.join(B, "voz.wav"))
v = resample_poly(v, SR, vsr)
voice = np.zeros(N); voice[: len(v)] = v[:N]
voice = filt(voice, "high", 70)
voice = reverb(voice, 0.9, 0.13, 5000)          # leve sala, más "presencia"

# ducking del ambiente bajo la voz
venv = np.convolve(np.abs(voice), np.ones(4800) / 4800, mode="same")
duck = 1 - 0.45 * np.clip(venv / (venv.max() * 0.25), 0, 1)

mix = voice * 1.0 + (amb + fx * 0.8) * duck
# estéreo con leve ensanchamiento del ambiente
L = mix + 0.15 * filt(amb, "band", [200, 4000]) * duck
R = mix - 0.15 * filt(amb, "band", [200, 4000]) * duck
st = np.stack([L, R], 1)
st = np.tanh(st / (np.abs(st).max() + 1e-9) * 1.4) / np.tanh(1.4) * 0.92
sf.write(os.path.join(B, "mezcla.wav"), st.astype(np.float32), SR)
print("mezcla.wav", round(TOTAL, 2), "s")
