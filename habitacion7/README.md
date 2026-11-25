# La habitación 7 — Parte 1

Video vertical 9:16 (1080×1920, 30 fps, 70.8 s) de suspenso para TikTok / Reels / Shorts,
con final abierto y elección del público (A o B).

- `salida/habitacion7_parte1.mp4` — video final
- `salida/portada.jpg` — portada / miniatura

## Guion

> **Gancho:** El hotel donde trabajo tiene seis habitaciones. Anoche... me llamaron desde la siete.
>
> Trabajo el turno de noche en un motel de carretera. Después de la una, no llega nadie. Solo la lluvia... y el zumbido de las luces.
> A las tres diecisiete, sonó el teléfono de recepción. En la pantalla decía: extensión siete.
> Contesté. Del otro lado, solo se escuchaba una respiración. Y luego, un susurro... dijo mi nombre.
> Revisé las cámaras. Pasillo uno: nada. Pasillo dos... había una puerta que yo nunca había visto. Con un siete oxidado.
> Fui a ver. Mis pasos eran lo único que se escuchaba.
> La puerta estaba entreabierta. Y adentro... sonaba un teléfono.
> Entonces, vibró mi celular. Llamada de recepción. Pero yo no estaba en recepción.
> Contesté... y la voz del otro lado era la mía. Me dijo: *no entres. Todavía no.*
>
> **Elección:** Ahora tú decides. ¿Entro a la habitación siete... o regreso corriendo a recepción?
> **Cierre:** Comenta A o B. Dale like y sígueme para la parte dos.

## Texto sugerido para publicar

> El hotel tiene 6 habitaciones... ¿quién llamó desde la 7? 🚪📞
> A) Entro a la habitación 7  B) Regreso a recepción. Comenta y la parte 2 sigue lo que elija la mayoría.
> #terror #historiasdeterror #suspenso #creepy #miedo #parte1 #historias #hotel

## Herramientas (sin créditos)

| Parte | Herramienta |
|---|---|
| Voz | **Kokoro TTS** (modelo abierto, corre local), voz `em_alex`, velocidad 0.9 |
| Visuales | Escenas ilustradas por código (Pillow + OpenCV): motel, recepción, LCD, cámaras CCTV, pasillo, puerta 7, celular |
| Sonido | Sintetizado: lluvia, zumbido fluorescente, drone, teléfono antiguo, respiración, pasos, latidos, vibración, golpes |
| Montaje | FFmpeg (H.264 + AAC) |

## Regenerar

```bash
pip install kokoro-onnx soundfile numpy scipy pillow opencv-python-headless
# modelos: kokoro-v1.0.onnx y voices-v1.0.bin desde
# https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
python3 voz.py <carpeta_modelos> <build>        # narración + tiempos
python3 sonido.py <build>                       # diseño sonoro + mezcla
python3 render.py <build> salida/video.mp4 salida/portada.png
```

Para cambiar el texto, edita `guion.py` y vuelve a correr los tres pasos.
