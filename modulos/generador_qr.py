"""
Paso 6 — Generar la imagen QR.

Contrato:
    generar_qr(enlace: str, ruta_salida: str) -> str

- Librería qrcode, corrección de errores config.CORRECCION_QR ("M").
- Sin borde extra (border=0); el margen lo pone el PDF.
- Guarda PNG y devuelve la ruta.

Estado: PENDIENTE — se programa en su propio chat siguiendo arquitectura.md.
"""
import config


def generar_qr(enlace, ruta_salida):
    raise NotImplementedError


if __name__ == "__main__":
    print(generar_qr("https://dieguinhodil.github.io/Inventario/#id=PRUEBA", "prueba_qr.png"))
