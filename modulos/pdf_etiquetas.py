"""
Paso 7 — Armar el PDF de etiquetas.

Contrato:
    armar_pdf(equipos: list[dict], ruta_pdf: str, tam_cm=config.TAM_ETIQUETA_CM) -> str

- Cada equipo trae "ruta_qr" e "id_final".
- Etiqueta de tam_cm × tam_cm: QR (~4.2 cm en 5×5) + id_final en texto debajo.
- Hoja carta, rejilla automática (4 × 5 = 20 etiquetas en 5×5), líneas de corte tenues.
- Librería reportlab. Devuelve la ruta del PDF.

Estado: PENDIENTE — se programa en su propio chat siguiendo arquitectura.md.
"""
import config


def armar_pdf(equipos, ruta_pdf, tam_cm=config.TAM_ETIQUETA_CM):
    raise NotImplementedError


if __name__ == "__main__":
    print("Prueba: generar 3 QR con generador_qr y pasarlos aquí.")
