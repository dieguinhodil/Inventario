"""
qr.py — Código QR de un equipo (versión 2).

El QR solo lleva la dirección pública de la ficha:
    config.BASE_URL + config.RUTA_FICHA + codigo   →   https://bi0medic4crm.pythonanywhere.com/e/k7q2xpm4

Base: generador_qr.py de la versión 1 (mismo nivel de corrección config.CORRECCION_QR, "M").
Diferencias con la versión 1:
    - No guarda archivos: devuelve el PNG en memoria (bytes) o la cuadrícula de módulos.
    - La versión del QR ya no depende de los datos del equipo: el enlace siempre mide
      50 caracteres → versión 4 (33 módulos por lado) para todos los equipos.
    - El aviso de "módulo demasiado pequeño" ahora lo hace etiquetas.py, que es quien sabe
      a qué tamaño se imprime.

Funciones:
    enlace_equipo(codigo) -> str             dirección que va dentro del QR
    matriz(enlace) -> list[list[bool]]       módulos del QR, sin zona blanca (True = negro)
    png(enlace) -> bytes                     imagen PNG en blanco y negro (para la pantalla)

No depende de Flask ni de la base de datos.
"""

import io

import qrcode
from qrcode import constants

import config

# Píxeles por módulo del PNG. Con 33 módulos + 4 de zona blanca por lado: 410 × 410 px.
MODULO_PX = 10

# Zona blanca alrededor del PNG, en módulos. El estándar pide al menos 4: así el PNG se puede
# imprimir o leer tal cual. (En el PDF la zona blanca la pone etiquetas.py.)
BORDE_PNG = 4


def enlace_equipo(codigo):
    """Dirección pública de la ficha de un equipo (lo que va dentro del QR)."""
    codigo = str(codigo or "").strip().lower()
    if len(codigo) != config.LARGO_CODIGO or any(c not in config.ALFABETO_CODIGO for c in codigo):
        raise ValueError(f"Código de QR no válido: {codigo!r}")
    return f"{config.BASE_URL}{config.RUTA_FICHA}{codigo}"


def _crear_qr(enlace, borde=0):
    """Objeto QR con la versión mínima que le cabe al enlace."""
    qr = qrcode.QRCode(
        version=None,                      # la elige sola según el largo del enlace
        error_correction=getattr(constants, f"ERROR_CORRECT_{config.CORRECCION_QR}"),
        box_size=MODULO_PX,
        border=borde,
    )
    qr.add_data(enlace)
    qr.make(fit=True)
    return qr


def matriz(enlace):
    """Cuadrícula de módulos del QR sin zona blanca: lista de filas (arriba → abajo) de
    booleanos (True = módulo negro). etiquetas.py la dibuja como figuras vectoriales."""
    return _crear_qr(enlace).get_matrix()


def png(enlace):
    """PNG del QR en memoria (bytes), en blanco y negro puro (1 bit), con BORDE_PNG módulos de
    zona blanca. Se usa en la pantalla de la etiqueta (/equipo/<num>/qr.png)."""
    imagen = _crear_qr(enlace, BORDE_PNG).make_image(fill_color="black", back_color="white")
    salida = io.BytesIO()
    imagen.save(salida, format="PNG")
    return salida.getvalue()