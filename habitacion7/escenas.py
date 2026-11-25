"""Escenas ilustradas por código. Cada escena devuelve:
   base  : imagen float32 (SH, SW, 3) en 0..1 (lienzo sobredimensionado para mover la cámara)
   luces : lista de (capa float32, nombre) que se suman con intensidad animada
   extra : datos para animaciones (máscaras, posiciones)"""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
OS = 1.2
SW, SH = int(W * OS), int(H * OS)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FS = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
rng = np.random.default_rng(3)

def font(path, size): return ImageFont.truetype(path, int(size))

def to_f(img): return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0

def vgrad(top, bot, w=SW, h=SH):
    a = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) / 255 * (1 - a) + np.array(bot, np.float32) / 255 * a
    return np.repeat(g, w, axis=1)

def from_f(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def layer(draw_fn, blur=0, w=SW, h=SH):
    im = Image.new("RGB", (w, h), (0, 0, 0)); draw_fn(ImageDraw.Draw(im))
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return to_f(im)

def glow(draw_fn, blurs=(6, 30, 90), weights=(1.0, 0.8, 0.6)):
    sharp = layer(draw_fn)
    out = sharp.copy()
    for b, w_ in zip(blurs, weights):
        out += cv2.GaussianBlur(sharp, (0, 0), b) * w_
    return out

def texture(base, amount=0.05, scale=3):
    n = rng.standard_normal((SH // scale, SW // scale)).astype(np.float32)
    n = cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (SW, SH))[..., None]
    return np.clip(base * (1 + n * amount), 0, 1)

def text_c(d, xy, s, f, fill, stroke=0, sfill=(0, 0, 0)):
    d.text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sfill)

# ------------------------------------------------------------------ MOTEL (exterior)
def motel():
    base = vgrad((6, 10, 22), (14, 16, 26))
    im = from_f(base); d = ImageDraw.Draw(im)
    # cerros y bosque
    pts = [(0, 1100)] + [(x, 1050 + 60 * np.sin(x / 170) + 30 * np.sin(x / 53)) for x in range(0, SW + 40, 40)] + [(SW, SH), (0, SH)]
    d.polygon(pts, fill=(8, 10, 14))
    # edificio
    d.rectangle((0, 1180, SW, 1560), fill=(34, 30, 30))
    d.rectangle((0, 1150, SW, 1190), fill=(22, 18, 18))          # techo
    d.rectangle((0, 1540, SW, 1580), fill=(50, 46, 44))          # banqueta
    for i in range(6):
        x = 70 + i * 205
        d.rectangle((x, 1300, x + 95, 1540), fill=(58, 42, 34), outline=(20, 15, 12), width=4)
        text_c(d, (x + 48, 1270), str(i + 1), font(FB, 34), (150, 140, 120))
        lit = i in (1, 4)
        d.rectangle((x + 115, 1320, x + 185, 1420), fill=(120, 95, 50) if lit else (18, 20, 26))
    # calle mojada
    d.rectangle((0, 1580, SW, SH), fill=(12, 13, 17))
    for y in range(1700, SH, 160):
        d.rectangle((SW // 2 - 14, y, SW // 2 + 14, y + 80), fill=(70, 66, 50))
    # poste del letrero
    d.rectangle((850, 600, 880, 1580), fill=(20, 20, 22))
    base = texture(to_f(im), 0.08)

    def sign_red(dd):
        dd.rounded_rectangle((660, 420, 1070, 600), 18, outline=(255, 40, 50), width=10)
        text_c(dd, (865, 510), "MOTEL", font(FB, 110), (255, 50, 60))
    def sign_green(dd):
        text_c(dd, (865, 665), "HAY CUARTOS", font(FB, 48), (60, 255, 140))
    def windows(dd):
        for i in (1, 4):
            x = 70 + i * 205; dd.rectangle((x + 115, 1320, x + 185, 1420), fill=(255, 190, 90))
    red = glow(sign_red) * np.array([1, .35, .35], np.float32)
    green = glow(sign_green, (4, 20, 60), (1, .7, .4))
    win = glow(windows, (4, 25, 70), (.5, .4, .3)) * 0.5
    # reflejos en el asfalto
    refl = cv2.GaussianBlur(np.flipud(red[200:1580]).copy(), (0, 0), 18)
    rr = np.zeros_like(red); h = min(SH - 1580, refl.shape[0]); rr[1580:1580 + h] = refl[:h] * 0.55
    return base, [(red + rr, "neon_rojo"), (green, "neon_verde"), (win, "ventanas")], {"rain": "full"}

# ------------------------------------------------------------------ RECEPCIÓN
def recepcion(ext_text="EXT 07"):
    base = vgrad((30, 40, 40), (16, 20, 22))
    im = from_f(base); d = ImageDraw.Draw(im)
    for x in range(0, SW, 46):                                  # papel tapiz
        d.line((x, 0, x, 1450), fill=(36, 46, 45), width=3)
    # ventana
    d.rectangle((70, 330, 560, 1060), fill=(10, 14, 26))
    d.rectangle((70, 330, 560, 1060), outline=(60, 52, 44), width=22)
    d.line((315, 330, 315, 1060), fill=(60, 52, 44), width=14)
    # reloj 3:17
    cx, cy, r = 650, 240, 105
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 196, 180), outline=(40, 36, 30), width=10)
    for k in range(12):
        a = k / 12 * 2 * np.pi
        d.line((cx + 80 * np.sin(a), cy - 80 * np.cos(a), cx + 92 * np.sin(a), cy - 92 * np.cos(a)), fill=(30, 30, 30), width=5)
    ah = (3 + 17 / 60) / 12 * 2 * np.pi; am = 17 / 60 * 2 * np.pi
    d.line((cx, cy, cx + 50 * np.sin(ah), cy - 50 * np.cos(ah)), fill=(20, 20, 20), width=10)
    d.line((cx, cy, cx + 80 * np.sin(am), cy - 80 * np.cos(am)), fill=(20, 20, 20), width=6)
    # tablero de llaves 1..7 (¡la 7 no debería existir!)
    d.rectangle((760, 420, 1210, 1080), fill=(70, 45, 28), outline=(35, 22, 14), width=12)
    text_c(d, (985, 475), "LLAVES", font(FB, 36), (190, 160, 110))
    for i in range(7):
        col, row = i % 3, i // 3
        x = 850 + col * 135; y = 600 + row * 190
        if i == 6: x = 985
        text_c(d, (x, y - 40), str(i + 1), font(FB, 34), (220, 200, 150) if i < 6 else (200, 60, 50))
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(160, 150, 130))
        if i in (0, 2, 3, 5, 6):
            kc = (180, 150, 70) if i < 6 else (120, 70, 50)
            d.rectangle((x - 4, y + 5, x + 4, y + 70), fill=kc)
            d.rectangle((x - 20, y + 70, x + 20, y + 110), fill=kc)
    # mostrador
    d.rectangle((0, 1430, SW, 1470), fill=(110, 75, 45))
    d.rectangle((0, 1470, SW, SH), fill=(52, 34, 22))
    for x in range(0, SW, 160):
        d.rectangle((x + 15, 1520, x + 145, SH - 40), outline=(40, 26, 16), width=6)
    # teléfono beige antiguo
    d.rounded_rectangle((260, 1250, 720, 1440), 40, fill=(178, 166, 140), outline=(90, 80, 64), width=6)
    d.rounded_rectangle((230, 1170, 750, 1260), 45, fill=(190, 178, 150), outline=(90, 80, 64), width=6)
    d.rectangle((330, 1300, 530, 1360), fill=(25, 50, 30))
    text_c(d, (430, 1330), ext_text, font(FM, 40), (140, 255, 160))
    for i in range(3):
        for j in range(3):
            d.rounded_rectangle((560 + j * 45, 1290 + i * 45, 595 + j * 45, 1322 + i * 45), 6, fill=(220, 214, 196))
    # libro de registro y campana
    d.polygon([(800, 1440), (1180, 1440), (1140, 1395), (840, 1395)], fill=(150, 30, 30))
    d.ellipse((90, 1380, 200, 1445), fill=(200, 170, 60))
    base = texture(to_f(im), 0.06)

    def tube(dd): dd.rectangle((240, 40, 1060, 70), fill=(235, 255, 240))
    def neon(dd): dd.ellipse((140, 500, 480, 900), fill=(255, 40, 60))
    def led(dd):
        dd.ellipse((660, 1385, 690, 1415), fill=(255, 30, 30))
        dd.rectangle((330, 1300, 530, 1360), fill=(40, 120, 60))
    tl = glow(tube, (10, 80, 300), (1, .7, .9)) * np.array([.85, 1, .9], np.float32) * 0.7
    nl = cv2.GaussianBlur(layer(neon), (0, 0), 60) * 0.7
    ll = glow(led, (3, 15, 50), (1, .8, .5))
    return base, [(tl, "tubo"), (nl, "neon_rojo"), (ll, "led")], {"rain": (70, 330, 560, 1060)}

# ------------------------------------------------------------------ TELÉFONO (primer plano LCD)
def telefono():
    base = vgrad((10, 10, 12), (4, 4, 6))
    im = from_f(base); d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 520, SW - 90, 1800), 90, fill=(160, 150, 126), outline=(70, 62, 50), width=10)
    d.rounded_rectangle((170, 640, SW - 170, 1120), 30, fill=(20, 40, 26), outline=(40, 36, 30), width=12)
    for i in range(4):
        for j in range(3):
            x = 340 + j * 210; y = 1240 + i * 130
            d.rounded_rectangle((x, y, x + 170, y + 95), 18, fill=(210, 202, 182), outline=(100, 92, 76), width=4)
            text_c(d, (x + 85, y + 48), "123456789*0#"[i * 3 + j], font(FB, 50), (60, 56, 50))
    base = texture(to_f(im), 0.07)

    def lcd(dd):
        dd.rounded_rectangle((182, 652, SW - 182, 1108), 22, fill=(18, 70, 34))
        text_c(dd, (SW // 2, 740), "LLAMADA ENTRANTE", font(FM, 56), (150, 255, 170))
        text_c(dd, (SW // 2, 880), "EXT. 07", font(FM, 130), (170, 255, 185))
        text_c(dd, (SW // 2, 1020), "03:17 AM", font(FM, 50), (130, 230, 150))
    return base, [(glow(lcd, (3, 20, 80), (1, .5, .4)), "lcd")], {"wave": (230, 1130, SW - 230)}

# ------------------------------------------------------------------ PASILLO en perspectiva
def corridor(with7=True, cctv=False, ajar=True):
    cx, cy, F = SW / 2, SH * 0.47, 560
    Z = 13.0
    def P(x, y, z): return (cx + x * F / z, cy - y * F / z)
    base = np.zeros((SH, SW, 3), np.float32)
    im = from_f(base); d = ImageDraw.Draw(im)
    X, YF, YC = 1.5, -1.6, 1.25
    lamps = [2.5, 6.0, 9.5]
    def bright(z):
        b = 0.18 + sum(0.9 * np.exp(-((z - l) ** 2) / 1.6) for l in lamps)
        return b / (1 + 0.12 * z)
    zs = np.arange(0.35, Z, 0.08)
    for z0, z1 in zip(zs[:-1], zs[1:]):
        b = bright((z0 + z1) / 2)
        floor = tuple(int(c * b) for c in (95, 30, 28))      # alfombra roja vieja
        wall = tuple(int(c * b) for c in (150, 140, 105))    # pared amarillenta
        ceil = tuple(int(c * b * .8) for c in (150, 150, 140))
        d.polygon([P(-X, YF, z0), P(X, YF, z0), P(X, YF, z1), P(-X, YF, z1)], fill=floor)
        d.polygon([P(-X, YC, z0), P(X, YC, z0), P(X, YC, z1), P(-X, YC, z1)], fill=ceil)
        d.polygon([P(-X, YF, z0), P(-X, YC, z0), P(-X, YC, z1), P(-X, YF, z1)], fill=wall)
        d.polygon([P(X, YF, z0), P(X, YC, z0), P(X, YC, z1), P(X, YF, z1)], fill=wall)
    # zoclo
    for s in (-1, 1):
        d.line([P(s * X, YF + .12, .35), P(s * X, YF + .12, Z)], fill=(30, 20, 14), width=6)
    # puertas laterales 1..6
    nums = {(-1, 0): "1", (1, 0): "2", (-1, 1): "3", (1, 1): "4", (-1, 2): "5", (1, 2): "6"}
    for (s, k), n in nums.items():
        za, zb = 2.0 + k * 3.4, 2.0 + k * 3.4 + 1.0
        b = bright((za + zb) / 2)
        col = tuple(int(c * b) for c in (90, 60, 40))
        d.polygon([P(s * X, YF, za), P(s * X, .75, za), P(s * X, .75, zb), P(s * X, YF, zb)], fill=col, outline=(15, 10, 8))
        px, py = P(s * X, .95, (za + zb) / 2)
        text_c(d, (px, py), n, font(FB, max(14, 0.32 * F / ((za + zb) / 2))), tuple(int(c * b) for c in (230, 210, 160)))
    # pared del fondo
    b = bright(Z)
    d.polygon([P(-X, YF, Z), P(X, YF, Z), P(X, YC, Z), P(-X, YC, Z)], fill=tuple(int(c * b) for c in (150, 140, 105)))
    door7 = None
    if with7:
        x0, y0 = P(-.5, YF, Z); x1, y1 = P(.5, .75, Z)
        d.rectangle((x0, y1, x1, y0), fill=(40, 34, 30), outline=(10, 8, 6), width=3)
        px, py = P(0, .95, Z)
        text_c(d, (px, py), "7", font(FB, .4 * F / Z), (120, 70, 40))
        door7 = (x0, y1, x1, y0)
    base = texture(to_f(im), 0.06)
    # luces del techo
    def lamps_fn(dd):
        for l in lamps:
            a = P(-.35, YC - .02, l); b2 = P(.35, YC - .02, l + .4)
            dd.rectangle((a[0], a[1], b2[0], b2[1] + 6), fill=(255, 245, 210))
    lamp_layer = glow(lamps_fn, (8, 50, 160), (1, .6, .5)) * 0.6
    lights = [(lamp_layer, "lamparas")]
    if with7 and ajar:
        def gap(dd):
            x0, y1_, x1, y0_ = door7
            dd.rectangle((x1 - (x1 - x0) * .12, y1_, x1, y0_), fill=(180, 220, 255))
            dd.polygon([(x1 - (x1 - x0) * .12, y0_), (x1, y0_), (x1 + 60, y0_ + 70), (x1 - 40, y0_ + 70)], fill=(40, 55, 70))
        lights.append((glow(gap, (3, 20, 70), (1, .8, .6)), "luz7"))
    if cctv:
        g = base.mean(2, keepdims=True) * 1.25
        base = np.clip(g * np.array([.75, 1.0, .8], np.float32), 0, 1)
        lights = [(l.mean(2, keepdims=True) * np.array([.75, 1, .8], np.float32), n) for l, n in lights]
    return base, lights, {"door7": door7}

# ------------------------------------------------------------------ PUERTA 7 (primer plano)
def puerta():
    base = vgrad((40, 38, 30), (20, 18, 15))
    im = from_f(base); d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = 250, 1000, 260, 2000
    d.rectangle((x0 - 60, y0 - 60, x1 + 60, y1), fill=(30, 22, 16))              # marco
    d.rectangle((x0, y0, x1, y1), fill=(52, 64, 54))                               # puerta verde vieja
    for (a, b) in [((x0 + 70, y0 + 120), (x1 - 70, y0 + 760)), ((x0 + 70, y0 + 880), (x1 - 70, y1 - 120))]:
        d.rectangle((*a, *b), outline=(36, 44, 38), width=14)
    for _ in range(140):                                                          # pintura descarapelada
        px, py = rng.uniform(x0, x1), rng.uniform(y0, y1); r = rng.uniform(4, 22)
        d.ellipse((px - r, py - r * .6, px + r, py + r * .6), fill=(70, 56, 40))
    # placa con el 7 oxidado
    d.ellipse((520, 470, 760, 710), fill=(110, 70, 36), outline=(60, 36, 18), width=8)
    text_c(d, (640, 590), "7", font(FS, 200), (150, 90, 40), 4, (60, 30, 12))
    for _ in range(30):
        px, py = rng.uniform(540, 740), rng.uniform(490, 690)
        d.ellipse((px - 6, py - 4, px + 6, py + 4), fill=(90, 50, 24))
    d.ellipse((860, 1150, 930, 1220), fill=(150, 130, 70))                         # perilla
    d.rectangle((0, 2000, SW, SH), fill=(60, 20, 18))                              # alfombra
    base = texture(to_f(im), 0.1)

    def gap(dd):
        dd.rectangle((1000, 260, 1030, 2000), fill=(200, 230, 255))
        dd.polygon([(1000, 2000), (1030, 2000), (1296, 2304), (900, 2304)], fill=(45, 60, 75))
    return base, [(glow(gap, (4, 30, 110), (1, .8, .7)), "luz7")], {}

# ------------------------------------------------------------------ CELULAR
def celular_fondo():
    b, lights, _ = recepcion()
    b = cv2.GaussianBlur(b, (0, 0), 25) * 0.35
    return b

def phone_screen(mode, secs=0):
    """dibuja la pantalla del celular (RGBA) — mode: 'entrante' | 'curso'"""
    w, h = 660, 1320
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w, h), 80, fill=(14, 14, 16, 255), outline=(60, 60, 66, 255), width=10)
    scr = Image.new("RGB", (w - 40, h - 40)); sd = ImageDraw.Draw(scr)
    g = np.linspace(0, 1, h - 40)[:, None]
    arr = (np.array([30, 34, 48]) * (1 - g) + np.array([8, 8, 12]) * g)[:, None, :].repeat(w - 40, 1)
    scr = Image.fromarray(arr.astype(np.uint8)); sd = ImageDraw.Draw(scr)
    cx = (w - 40) // 2
    sd.rounded_rectangle((cx - 80, 24, cx + 80, 60), 18, fill=(0, 0, 0))
    text_c(sd, (cx, 200), "llamada entrante" if mode == "entrante" else "llamada en curso", font(FB, 34), (170, 170, 185))
    sd.ellipse((cx - 110, 300, cx + 110, 520), fill=(70, 75, 95))
    text_c(sd, (cx, 410), "R", font(FB, 120), (220, 220, 235))
    text_c(sd, (cx, 610), "Recepción", font(FB, 72), (245, 245, 250))
    text_c(sd, (cx, 690), "Motel · Ext. 07" if mode == "entrante" else f"00:{secs:02d}", font(FB, 38), (160, 160, 175))
    if mode == "entrante":
        sd.ellipse((70, 1000, 230, 1160), fill=(230, 50, 50)); sd.ellipse((390, 1000, 550, 1160), fill=(50, 200, 90))
        text_c(sd, (150, 1080), "✕", font(FB, 70), (255, 255, 255)); text_c(sd, (470, 1080), "✓", font(FB, 70), (255, 255, 255))
    else:
        sd.ellipse((cx - 80, 1010, cx + 80, 1170), fill=(230, 50, 50))
        text_c(sd, (cx, 1090), "✕", font(FB, 70), (255, 255, 255))
    mask = Image.new("L", scr.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, *scr.size), 62, fill=255)
    im.paste(scr, (20, 20), mask)
    return np.asarray(im, np.float32) / 255

# ------------------------------------------------------------------ PORTADA (título)
def titulo_overlay():
    def white(dd):
        text_c(dd, (W // 2, 330), "HABITACIÓN", font(FB, 128), (240, 236, 228), 6, (0, 0, 0))
    def red(dd):
        text_c(dd, (W // 2, 640), "7", font(FS, 430), (255, 40, 40), 4, (90, 0, 0))
    tag = layer(lambda dd: (dd.rounded_rectangle((W // 2 - 140, 120, W // 2 + 140, 190), 14, fill=(220, 30, 30)),
                            text_c(dd, (W // 2, 156), "PARTE 1", font(FB, 44), (255, 255, 255))), w=W, h=H)
    return layer(white, w=W, h=H) + tag, glow_wh(red)

def glow_wh(fn):
    sharp = layer(fn, w=W, h=H)
    return sharp + cv2.GaussianBlur(sharp, (0, 0), 12) + cv2.GaussianBlur(sharp, (0, 0), 50) * .8
