"""Anima las escenas, agrega subtítulos/efectos y exporta el MP4 final.
Uso: python3 render.py <build_dir> <salida.mp4> [portada.png]"""
import json, sys, os, subprocess, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
import escenas as E

B, OUT = sys.argv[1], sys.argv[2]
COVER = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else None
W, H, FPS = E.W, E.H, 30
tm = json.load(open(os.path.join(B, "tiempos.json")))
SEG = tm["segments"]
TOTAL = tm["duration"] + 3.0
NF = int(TOTAL * FPS)
rng = np.random.default_rng(11)

# ---------------------------------------------------------------- línea de tiempo
def span(name):
    s = [x for x in SEG if x["scene"] == name]
    return s[0]["start"], s[-1]["end"], s
order = []
for s in SEG:
    if not order or order[-1] != s["scene"]: order.append(s["scene"])
starts = {n: (0.0 if i == 0 else span(n)[0] - 0.35) for i, n in enumerate(order)}
def scene_at(t):
    cur = order[0]
    for n in order:
        if t >= starts[n]: cur = n
    return cur

# ---------------------------------------------------------------- recursos
print("dibujando escenas…")
R = {
    "motel": E.motel(), "recepcion": E.recepcion(), "telefono": E.telefono(),
    "cam1": E.corridor(with7=False, cctv=True), "cam2": E.corridor(with7=True, cctv=True, ajar=False),
    "pasillo": E.corridor(with7=True), "puerta": E.puerta(),
}
cover_bg = (R["puerta"][0] * 0.45 + R["puerta"][1][0][0] * 0.6)
title_w, title_r = E.titulo_overlay()
cel_bg = E.celular_fondo()
vign = np.ones((H, W), np.float32)
yy, xx = np.mgrid[0:H, 0:W]
vign = (1 - 0.75 * (((xx - W / 2) / (W * .72)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2)).clip(0.15, 1)[..., None].astype(np.float32)
grains = [rng.standard_normal((H // 2, W // 2)).astype(np.float32) for _ in range(6)]
grains = [cv2.resize(g, (W, H), interpolation=cv2.INTER_NEAREST)[..., None] for g in grains]
scan = (1 - 0.18 * (np.arange(H) % 4 < 2)).astype(np.float32)[:, None, None]

# gotas de lluvia
drops = np.column_stack([rng.uniform(0, W, 260), rng.uniform(0, H, 260), rng.uniform(40, 110, 260), rng.uniform(1400, 2400, 260)])
wdrops = np.column_stack([rng.uniform(0, 1, 70), rng.uniform(0, 1, 70), rng.uniform(20, 60, 70), rng.uniform(900, 1500, 70)])

# ---------------------------------------------------------------- subtítulos
FONT = ImageFont.truetype(E.FB, 84)
HL_RED = {"SIETE.", "SIETE", "SIETE...", "7", "MÍA.", "NOMBRE.", "ENTRES."}
HL_YEL = {"TELÉFONO", "OXIDADO.", "RESPIRACIÓN.", "SUSURRO...", "CELULAR.", "TRES", "DIECISIETE,", "PUERTA", "VOZ"}
chunks = []
for s in SEG:
    if s["scene"] == "eleccion": continue
    words = s["text"].upper().split()
    groups, g = [], []
    for w in words:
        if g and len(" ".join(g + [w])) > 17:
            groups.append(g); g = []
        g.append(w)
        if w.endswith((".", ",", "...", ":", "?")):
            groups.append(g); g = []
    if g: groups.append(g)
    total = sum(len(" ".join(x)) for x in groups)
    t0 = s["start"]
    for gr in groups:
        d = (s["end"] - s["start"]) * len(" ".join(gr)) / total
        chunks.append((t0, t0 + d, gr, s["phone"])); t0 += d

_cache = {}
def chunk_img(i):
    if i in _cache: return _cache[i]
    _, _, words, phone = chunks[i]
    sp = FONT.getlength(" ")
    widths = [FONT.getlength(w) for w in words]
    tw = int(sum(widths) + sp * (len(words) - 1)) + 40
    im = Image.new("RGBA", (tw, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 20
    for w, ww in zip(words, widths):
        col = (255, 60, 60) if w in HL_RED or phone else (255, 214, 50) if w in HL_YEL else (255, 255, 255)
        d.text((x, 20), w, font=FONT, fill=col, stroke_width=9, stroke_fill=(0, 0, 0))
        x += ww + sp
    a = np.asarray(im, np.float32) / 255
    _cache[i] = a
    return a

def overlay(frame, rgba, cx, cy, scale=1.0):
    if scale != 1.0:
        rgba = cv2.resize(rgba, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = rgba.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs, ys = max(0, -x0), max(0, -y0)
    x1, y1 = min(W, x0 + w), min(H, y0 + h)
    if x1 <= max(x0, 0) or y1 <= max(y0, 0): return
    src = rgba[ys:ys + (y1 - max(y0, 0)), xs:xs + (x1 - max(x0, 0))]
    a = src[..., 3:4]
    region = frame[max(y0, 0):y1, max(x0, 0):x1]
    region[:] = region * (1 - a) + src[..., :3] * a

# ---------------------------------------------------------------- utilidades
def ease(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def flicker(t, seed, rate=9, depth=0.6):
    v = math.sin(t * rate + seed) * math.sin(t * rate * 2.37 + seed * 3)
    k = int(t * 12 + seed * 7)
    drop = 1 - depth if (k * 2654435761 % 97) < 9 else 1
    return (0.85 + 0.15 * v) * drop

def camera(canvas, z, fx, fy, rot=0.0):
    hw, hh = W / (2 * z), H / (2 * z)
    fx = min(max(fx, hw), E.SW - hw); fy = min(max(fy, hh), E.SH - hh)
    M = cv2.getRotationMatrix2D((fx, fy), rot, z)
    M[0, 2] += W / 2 - fx; M[1, 2] += H / 2 - fy
    return cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def compose(name, intens):
    base, lights, _ = R[name]
    c = base.copy()
    for (l, n) in lights:
        k = intens.get(n, 1.0)
        if k: c += l * k
    return c

def rain(frame, t, n=260, alpha=0.22):
    for i in range(n):
        x, y0, ln, sp = drops[i]
        y = (y0 + t * sp) % (H + 200) - 100
        xx = x - 0.18 * ln
        cv2.line(frame, (int(x), int(y)), (int(xx), int(y + ln)), (alpha, alpha, alpha * 1.1), 2, cv2.LINE_AA)

def win_rain(canvas, t, rect):
    x0, y0, x1, y1 = rect
    for fx_, fy_, ln, sp in wdrops:
        x = x0 + fx_ * (x1 - x0); y = y0 + ((fy_ * (y1 - y0) + t * sp) % (y1 - y0))
        cv2.line(canvas, (int(x), int(y)), (int(x - 8), int(min(y + ln, y1))), (0.35, 0.38, 0.45), 2, cv2.LINE_AA)

def seg_t(name, idx):
    return span(name)[2][idx]["start"]

# ---------------------------------------------------------------- escenas
def f_cover(t):
    c = cover_bg
    fr = camera(c, 1.0 + 0.05 * t, E.SW / 2, E.SH / 2 + 120)
    fr = fr * 0.8
    k = flicker(t, 1.3, 13, 0.85)
    fr += title_w * min(1, t * 3) + title_r * k * min(1, t * 4)
    if 5.45 < t < 5.75: fr += 0.35 * (1 - (t - 5.45) / .3)       # golpe "desde la siete"
    return fr

def f_motel(t, lt):
    c = compose("motel", {"neon_rojo": flicker(t, 2.0, 11, .9), "neon_verde": flicker(t, 4.0, 7, .7), "ventanas": 1})
    fr = camera(c, 1.0 + 0.06 * lt, E.SW / 2 - 40 + 30 * lt, E.SH / 2 + 60)
    rain(fr, t)
    if 0.35 < lt < 0.5 or 0.62 < lt < 0.72: fr += 0.45           # relámpago
    return fr

def f_recepcion(t, lt):
    ring = any(r0 < t < r0 + 1.6 for r0 in (span("recepcion")[0] - 0.4, span("recepcion")[0] + 2.0))
    led = (1.0 if int(t * 8) % 2 else 0.15) if ring or t > seg_t("recepcion", 1) else 0.0
    c = compose("recepcion", {"tubo": flicker(t, 5.0, 14, .85), "neon_rojo": 0.6 + 0.4 * flicker(t, 2.0, 11, 1), "led": led})
    win_rain(c, t, R["recepcion"][2]["rain"])
    p = ease((t - seg_t("recepcion", 1) + 0.2) / 1.4)             # acercamiento al teléfono
    z = 1.0 + 0.04 * lt + 0.9 * p
    fx = E.SW / 2 + (430 - E.SW / 2) * p; fy = E.SH / 2 + (1300 - E.SH / 2) * p
    sh = 6 * math.sin(t * 40) * (1 if ring else 0)
    return camera(c, z, fx + sh, fy)

def f_telefono(t, lt):
    s0 = seg_t("telefono", 1)
    lcd = 1.0 if t < s0 else 0.75 + 0.25 * flicker(t, 3.0, 17, 0.9)
    c = compose("telefono", {"lcd": lcd})
    x0, y, x1 = R["telefono"][2]["wave"]
    pts = []
    amp = 0.5 + 0.5 * math.sin(2 * math.pi * 0.32 * t - 1)
    for i, x in enumerate(np.linspace(x0, x1, 120)):
        v = math.sin(x * 0.05 + t * 20) * math.sin(x * 0.013 + t * 3)
        pts.append((x, y + 40 + v * 34 * amp ** 3 + rng.normal(0, 3 * amp)))
    cv2.polylines(c, [np.array(pts, np.int32)], False, (0.1, 0.25, 0.12), 6, cv2.LINE_AA)
    z = 1.05 + 0.25 * ease(lt / 7)
    return camera(c, z, E.SW / 2 + 8 * math.sin(t * 1.7), E.SH / 2 - 100 + 6 * math.sin(t * 2.3), 0.4 * math.sin(t * .8))

def put_text(fr, txt, org, scale, color, th):
    (tw, tht), bl = cv2.getTextSize(txt, cv2.FONT_HERSHEY_DUPLEX, scale, th)
    x, y = org; y0 = max(0, y - tht - 10); x1 = min(W, x + tw + 10); y1 = min(H, y + bl + 10)
    m = np.zeros((y1 - y0, x1 - x), np.uint8)
    cv2.putText(m, txt, (0, y - y0), cv2.FONT_HERSHEY_DUPLEX, scale, 255, th, cv2.LINE_AA)
    a = (m.astype(np.float32) / 255)[..., None]
    fr[y0:y1, x:x1] = fr[y0:y1, x:x1] * (1 - a) + np.array(color, np.float32) * a

def f_camaras(t, lt):
    s1 = seg_t("camaras", 1)
    name = "cam1" if t < s1 else "cam2"
    c = compose(name, {"lamparas": flicker(t, 6.0, 10, .8)})
    if name == "cam1":
        fr = camera(c, 1.0, E.SW / 2, E.SH / 2)
    else:
        d7 = R["cam2"][2]["door7"]
        p = ease((t - (span("camaras")[1] - 1.8)) / 1.2)
        z = 1.0 + 3.0 * p
        fr = camera(c, z, E.SW / 2 + ((d7[0] + d7[2]) / 2 - E.SW / 2) * p, E.SH / 2 + ((d7[1] + d7[3]) / 2 - E.SH / 2) * p)
    fr = fr * scan
    g = (0.75, 1.0, 0.8)
    cam = "CAM 01  PASILLO 1" if name == "cam1" else "CAM 02  PASILLO 2"
    put_text(fr, cam, (50, 110), 1.7, g, 3)
    secs = int(t - starts["camaras"]) + 4
    put_text(fr, f"03:21:{secs:02d}", (50, 180), 1.5, g, 2)
    if int(t * 2) % 2:
        cv2.circle(fr, (W - 190, 95), 18, (1.0, 0.1, 0.1), -1)
        put_text(fr, "REC", (W - 160, 112), 1.5, (0.9, 0.9, 0.9), 3)
    for (x, y, dx, dy) in [(40, 40, 1, 1), (W - 40, 40, -1, 1), (40, H - 40, 1, -1), (W - 40, H - 40, -1, -1)]:
        cv2.line(fr, (x, y), (x + 90 * dx, y), g, 4); cv2.line(fr, (x, y), (x, y + 90 * dy), g, 4)
    if (int(t * 30) * 7919) % 41 < 3:                               # salto de señal
        k = rng.integers(0, H - 200); fr[k:k + 120] = np.roll(fr[k:k + 120], rng.integers(-80, 80), axis=1)
    return fr

def f_pasillo(t, lt):
    c = compose("pasillo", {"lamparas": flicker(t, 7.0, 12, .9), "luz7": 0.6 + 0.4 * math.sin(t * 3)})
    dur = span("pasillo")[1] - starts["pasillo"] + 0.4
    p = lt / dur
    z = 1.0 + 1.3 * p
    bob_y = 14 * abs(math.sin(math.pi * t / 0.62)); bob_x = 9 * math.sin(math.pi * t / 0.62)
    return camera(c, z, E.SW / 2 + bob_x, E.SH * 0.47 + bob_y, 0.6 * math.sin(math.pi * t / 1.24))

def f_puerta(t, lt):
    ringing = any(r0 < t < r0 + 1.3 for r0 in [span("puerta")[0] + 0.4 + k * 2.2 for k in range(3)])
    c = compose("puerta", {"luz7": (0.7 + 0.5 * (int(t * 10) % 2)) if ringing else 0.55})
    z = 1.0 + 0.18 * ease(lt / 4.5)
    return camera(c, z, E.SW / 2 + 60, E.SH / 2 - 100, 0.3 * math.sin(t))

phone_cache = {}
def f_celular(t, lt):
    s = span("celular")[2]
    answered = t >= s[2]["start"] - 0.1
    key = ("curso", int(t - s[2]["start"]) + 1) if answered else ("entrante", 0)
    if key not in phone_cache: phone_cache[key] = E.phone_screen(*key)
    scr = phone_cache[key]
    fr = camera(cel_bg, 1.05, E.SW / 2, E.SH / 2)
    vib = (not answered) and any(v0 < t < v0 + 0.45 for v0 in [s[0]["start"] - 0.2 + k * 0.85 for k in range(3)])
    sx = rng.normal(0, 9) if vib else 3 * math.sin(t * 1.3)
    sy = rng.normal(0, 9) if vib else 4 * math.sin(t * 1.1)
    zoom = 1.0 + (0.12 * ease((t - s[2]["start"]) / 3.0) if answered else 0)
    overlay(fr, scr, W / 2 + sx, H / 2 - 60 + sy, zoom)
    if answered:
        cx, cy = int(W / 2 + sx), int(H / 2 + 260 * zoom + sy)
        pts = [(int(cx - 220 + i * 4.4), int(cy + math.sin(i * .5 + t * 25) * (20 + 25 * math.sin(t * 7)) * (1 if i % 3 else .4))) for i in range(101)]
        cv2.polylines(fr, [np.array(pts)], False, (0.4, 0.9, 0.5), 4, cv2.LINE_AA)
    ph = [x for x in s if x["phone"]][0]
    if ph["start"] - .2 < t < ph["end"] + .8:                       # tinte rojo cuando habla "su" voz
        k = 0.5 + 0.5 * math.sin(t * 12)
        fr[..., 0] += 0.18 * k; fr[..., 1:] *= 0.85
    return fr

# --- pantalla de elección
def build_choice():
    pu = camera(compose("puerta", {"luz7": 0.8}), 1.3, E.SW / 2 + 60, E.SH / 2 - 200)
    re = camera(compose("recepcion", {"tubo": 1, "neon_rojo": .8, "led": 1}), 1.25, E.SW / 2, E.SH / 2 + 200)
    cards = []
    for img, letter, label in [(pu, "A", "ENTRO A LA 7"), (re, "B", "REGRESO A RECEPCIÓN")]:
        crop = img[H // 2 - 330: H // 2 + 330, :]
        crop = cv2.resize(crop, (900, 560)) * 0.8
        im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(im)
        d.rectangle((0, 420, 900, 560), fill=(0, 0, 0, 200))
        d.ellipse((24, 434, 136, 546), fill=(220, 30, 30))
        d.text((80, 490), letter, font=ImageFont.truetype(E.FB, 76), fill=(255, 255, 255), anchor="mm")
        d.text((165, 490), label, font=ImageFont.truetype(E.FB, 56), fill=(255, 255, 255), anchor="lm")
        cards.append(np.asarray(im, np.float32) / 255)
    top = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(top)
    d.text((W / 2, 130), "TÚ DECIDES", font=ImageFont.truetype(E.FB, 120), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((W / 2, 240), "¿qué hago ahora?", font=ImageFont.truetype(E.FB, 50), fill=(200, 200, 200), anchor="mm")
    bot = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(bot)
    d.text((W / 2, 70), "COMENTA  A  o  B", font=ImageFont.truetype(E.FB, 86), fill=(255, 214, 50), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
    # corazón
    hx, hy, r = 150, 220, 34
    d.ellipse((hx - 2 * r, hy - r - 20, hx, hy + r - 20), fill=(255, 40, 70)); d.ellipse((hx, hy - r - 20, hx + 2 * r, hy + r - 20), fill=(255, 40, 70))
    d.polygon([(hx - 2 * r + 3, hy - 5), (hx + 2 * r - 3, hy - 5), (hx, hy + 2 * r + 5)], fill=(255, 40, 70))
    d.text((250, 215), "LIKE + SÍGUEME", font=ImageFont.truetype(E.FB, 58), fill=(255, 255, 255), anchor="lm")
    d.text((250, 285), "para la PARTE 2", font=ImageFont.truetype(E.FB, 46), fill=(255, 80, 80), anchor="lm")
    return cards, np.asarray(top, np.float32) / 255, np.asarray(bot, np.float32) / 255
CHOICE = build_choice()

def f_eleccion(t, lt):
    cards, top, bot = CHOICE
    fr = np.zeros((H, W, 3), np.float32) + np.array([0.03, 0.02, 0.02], np.float32)
    rain(fr, t, 120, 0.12)
    overlay(fr, top, W / 2, 170 - 60 * (1 - ease(lt / .4)))
    ya = 640; yb = 1240
    for i, (card, y) in enumerate(zip(cards, (ya, yb))):
        p = ease((lt - 0.2 - i * 0.25) / 0.45)
        x = W / 2 + (1 - p) * (W if i else -W)
        active = int(t * 2) % 2 == i
        if p > 0.99:
            col = (1.0, 0.2, 0.2) if active else (0.4, 0.4, 0.4)
            cv2.rectangle(fr, (int(x - 460), int(y - 290)), (int(x + 460), int(y + 290)), col, 10 if active else 4)
        overlay(fr, card, x, y, 1.0 + (0.02 if active and p > .99 else 0))
    ev = span("eleccion")[2][1]["start"]
    pb = ease((t - ev + 0.2) / 0.4)
    if pb > 0:
        overlay(fr, bot, W / 2, 1720 + 80 * (1 - pb), 1.0)
    return fr

FN = {"motel": f_motel, "recepcion": f_recepcion, "telefono": f_telefono, "camaras": f_camaras,
      "pasillo": f_pasillo, "puerta": f_puerta, "celular": f_celular, "eleccion": f_eleccion}

def glitch(fr, k):
    out = fr.copy()
    s = int(12 + 30 * k)
    out[..., 2] = np.roll(fr[..., 2], s, 1); out[..., 0] = np.roll(fr[..., 0], -s, 1)
    for _ in range(int(4 + 8 * k)):
        y = rng.integers(0, H - 80); h = rng.integers(10, 80)
        out[y:y + h] = np.roll(out[y:y + h], rng.integers(-150, 150), 1)
    out += (rng.random((H // 4, W // 4, 1)).astype(np.float32).repeat(4, 0).repeat(4, 1) - .5) * 0.5 * k
    return out

def frame_at(t, subs=True):
    n = scene_at(t)
    lt = t - starts[n]
    fr = f_cover(t) if n == "cover" else FN[n](t, lt)
    # glitch en cortes
    nxt = [starts[x] for x in order if starts[x] > t]
    if lt < 0.14 and n != "cover": fr = glitch(fr, 1 - lt / 0.14)
    elif nxt and nxt[0] - t < 0.06: fr = glitch(fr, 0.6)
    fr = fr * vign
    fr += grains[int(t * FPS) % 6] * (0.045 if n != "camaras" else 0.08)
    # fade final
    if t > TOTAL - 0.6: fr *= max(0, (TOTAL - t) / 0.6)
    if subs:
        for i, (a, b, _, _) in enumerate(chunks):
            if a <= t < b:
                pop = 1.0 + 0.18 * max(0, 1 - (t - a) / 0.12)
                ci = chunk_img(i); overlay(fr, ci, W / 2, 1790 if n == "celular" else 1480, pop * min(1.0, 990 / ci.shape[1]))
                break
    return fr

# ---------------------------------------------------------------- export
if COVER:
    fr = frame_at(2.2, subs=False)
    cv2.imwrite(COVER, (np.clip(fr[..., ::-1], 0, 1) * 255).astype(np.uint8))

if "--preview" in sys.argv:
    os.makedirs(OUT, exist_ok=True)
    for tt in [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]:
        cv2.imwrite(os.path.join(OUT, f"f_{tt:05.1f}.png"), cv2.resize((np.clip(frame_at(tt)[..., ::-1], 0, 1) * 255).astype(np.uint8), (540, 960)))
    sys.exit()

cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", os.path.join(B, "mezcla.wav"), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for i in range(NF):
    fr = frame_at(i / FPS)
    p.stdin.write((np.clip(fr, 0, 1) * 255).astype(np.uint8).tobytes())
    if i % 150 == 0: print(f"{i}/{NF}", flush=True)
p.stdin.close(); p.wait()
print("listo:", OUT)
