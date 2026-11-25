# Guion de "La habitación 7" — cada segmento: (escena, texto, pausa_despues_seg)
# Escenas: cover, motel, recepcion, telefono, camaras, pasillo, puerta, celular, eleccion

SEGMENTOS = [
    ("cover",     "El hotel donde trabajo tiene seis habitaciones.", 0.35),
    ("cover",     "Anoche... me llamaron desde la siete.", 0.9),
    ("motel",     "Trabajo el turno de noche en un motel de carretera.", 0.25),
    ("motel",     "Después de la una, no llega nadie. Solo la lluvia... y el zumbido de las luces.", 0.6),
    ("recepcion", "A las tres diecisiete, sonó el teléfono de recepción.", 0.3),
    ("recepcion", "En la pantalla decía: extensión siete.", 0.8),
    ("telefono",  "Contesté. Del otro lado, solo se escuchaba una respiración.", 0.4),
    ("telefono",  "Y luego, un susurro... dijo mi nombre.", 0.9),
    ("camaras",   "Revisé las cámaras. Pasillo uno: nada.", 0.3),
    ("camaras",   "Pasillo dos... había una puerta que yo nunca había visto. Con un siete oxidado.", 0.7),
    ("pasillo",   "Fui a ver. Mis pasos eran lo único que se escuchaba.", 0.4),
    ("puerta",    "La puerta estaba entreabierta. Y adentro... sonaba un teléfono.", 0.7),
    ("celular",   "Entonces, vibró mi celular. Llamada de recepción.", 0.3),
    ("celular",   "Pero yo no estaba en recepción.", 0.5),
    ("celular",   "Contesté... y la voz del otro lado era la mía.", 0.4),
    ("celular",   "Me dijo: no entres. Todavía no.", 1.0),
    ("eleccion",  "Ahora tú decides. ¿Entro a la habitación siete... o regreso corriendo a recepción?", 0.3),
    ("eleccion",  "Comenta A o B. Dale like y sígueme para la parte dos.", 0.6),
]

# Segmento que se procesa con efecto "voz telefónica" (su propia voz)
VOZ_TELEFONO = {"Me dijo: no entres. Todavía no."}
