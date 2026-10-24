"""
generador_qr.py — Paso 6 del diagrama de flujo: genera la imagen QR de cada enlace.

Contrato (arquitectura.md, sección 7):
    generar_qr(enlace: str, ruta_salida: str) -> str

- Librería qrcode, corrección de errores config.CORRECCION_QR ("M").
- Sin borde extra (border=0); el margen blanco lo pone el PDF.
- Guarda PNG y devuelve la ruta.

Detalles de esta implementación:
- La versión del QR (tamaño de la cuadrícula) se elige sola según el largo del enlace.
  Con INVENTARIO_JUNIO_2025 salen versiones 8 a 12 (49 a 65 módulos por lado).
- Cada módulo mide TAM_MODULO_PX píxeles: el PNG más grande queda en 650 × 650 px,
  unos 390 ppp al imprimirlo a ~4.2 cm. Suficiente para impresión nítida.
- Imagen en blanco y negro puro (1 bit): bordes exactos y archivos de ~1–2 KB.
- Si el enlace crece tanto que el módulo impreso quedaría por debajo de MODULO_MIN_MM,
  avisa con un warning (no detiene el programa). Útil cuando se capturen las fechas
  de último MPrev y los enlaces se alarguen.
- Crea la carpeta de salida si no existe.

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (293 QR, todos se leen de vuelta
con el enlace exacto).
"""

import os
import sys
import warnings
from pathlib import Path

if __name__ == "__main__":  # permite probarlo solo: python modulos/generador_qr.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q

import config


# Píxeles por módulo (cada "cuadrito" del QR). El PDF escala la imagen al tamaño final.
TAM_MODULO_PX = 10

# Lado del QR impreso (el mismo valor que usa pdf_etiquetas).
# Solo se usa para el aviso de tamaño mínimo; no cambia la imagen.
TAM_QR_CM = config.TAM_QR_CM

# Por debajo de este tamaño de módulo la lectura con el teléfono empieza a ser menos confiable.
MODULO_MIN_MM = 0.5

_NIVELES = {
    "L": ERROR_CORRECT_L,   # ~7 % de recuperación
    "M": ERROR_CORRECT_M,   # ~15 %
    "Q": ERROR_CORRECT_Q,   # ~25 %
    "H": ERROR_CORRECT_H,   # ~30 %
}


def _nivel_correccion():
    nivel = str(config.CORRECCION_QR).strip().upper()
    if nivel not in _NIVELES:
        raise ValueError(f"config.CORRECCION_QR debe ser L, M, Q o H (es {config.CORRECCION_QR!r})")
    return _NIVELES[nivel]


def _crear_qr(enlace):
    """Arma el objeto QR (sin dibujarlo) con la versión mínima que le cabe al enlace."""
    if not isinstance(enlace, str) or enlace.strip() == "":
        raise ValueError("El enlace está vacío; no se puede generar el QR.")
    qr = qrcode.QRCode(
        version=None,                      # la elige sola según el largo del enlace
        error_correction=_nivel_correccion(),
        box_size=TAM_MODULO_PX,
        border=0,                          # el margen lo pone el PDF
    )
    qr.add_data(enlace)
    qr.make(fit=True)
    return qr


def info_qr(enlace):
    """Devuelve versión, módulos por lado y tamaño del módulo impreso (mm) para un enlace."""
    qr = _crear_qr(enlace)
    modulos = qr.modules_count
    return {
        "version": qr.version,
        "modulos": modulos,
        "modulo_mm": round(TAM_QR_CM * 10 / modulos, 3),
        "pixeles": modulos * TAM_MODULO_PX,
    }


def generar_qr(enlace, ruta_salida):
    """Genera el QR de `enlace`, lo guarda como PNG en `ruta_salida` y devuelve la ruta."""
    qr = _crear_qr(enlace)

    modulo_mm = TAM_QR_CM * 10 / qr.modules_count
    if modulo_mm < MODULO_MIN_MM:
        warnings.warn(
            f"{os.path.basename(str(ruta_salida))}: el QR es versión {qr.version} "
            f"({qr.modules_count} módulos); impreso a {TAM_QR_CM} cm cada módulo mide "
            f"{modulo_mm:.2f} mm (< {MODULO_MIN_MM} mm). Podría costar leerlo con el teléfono.",
            stacklevel=2,
        )

    ruta_salida = os.fspath(ruta_salida)
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    imagen = qr.make_image(fill_color="black", back_color="white")  # 1 bit, blanco y negro
    imagen.save(ruta_salida, format="PNG")
    return ruta_salida


# ---------------------------------------------------------------------------
# Prueba independiente:
#   python modulos/generador_qr.py                      → genera un QR de prueba
#   python modulos/generador_qr.py --excel INVENTARIO_JUNIO_2025.xlsx
#       → además genera los QR de todo el Excel.
# Todo se guarda en una carpeta temporal (no deja archivos en el proyecto) y,
# si está instalado zxing-cpp (pip install zxing-cpp), cada QR se lee de vuelta.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import tempfile
    from collections import Counter

    parser = argparse.ArgumentParser(description="Prueba del generador de QR")
    parser.add_argument("--excel", help="Probar con todos los equipos de este Excel")
    args = parser.parse_args()

    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        zxingcpp = None

    def leer_qr(ruta):
        """Lee el PNG con zxing-cpp. El PNG no trae margen, así que se le agrega uno al leerlo."""
        img = Image.open(ruta).convert("L")
        margen = 4 * TAM_MODULO_PX
        lienzo = Image.new("L", (img.width + 2 * margen, img.height + 2 * margen), 255)
        lienzo.paste(img, (margen, margen))
        resultados = zxingcpp.read_barcodes(lienzo)
        return resultados[0].text if resultados else None

    with tempfile.TemporaryDirectory() as carpeta:
        # 1) Ejemplo de la plantilla
        enlace = "https://dieguinhodil.github.io/Inventario/#id=PRUEBA"
        ruta = generar_qr(enlace, os.path.join(carpeta, "prueba_qr.png"))
        print("QR de prueba:", info_qr(enlace))
        if zxingcpp:
            assert leer_qr(ruta) == enlace, "El QR de prueba no se lee igual"
            print("OK: el QR de prueba se lee de vuelta")
        else:
            print("(zxing-cpp no está instalado: no se comprobó la lectura)")

        # 2) Todos los equipos del Excel real, con los pasos 1–5 de main.py
        if not args.excel:
            sys.exit(0)
        from modulos import enlaces, filtros, ids, lector_excel, limpieza
        incluidos, _ = filtros.separar_por_estatus(limpieza.limpiar(lector_excel.leer_hoja(args.excel)))
        equipos = ids.asignar_ids(incluidos)

        versiones = Counter()
        for e in equipos:
            enlace = enlaces.construir_enlace(e)
            ruta = generar_qr(enlace, os.path.join(carpeta, e["id_final"].replace(" ", "_") + ".png"))
            versiones[info_qr(enlace)["version"]] += 1
            if zxingcpp:
                assert leer_qr(ruta) == enlace, f"fila {e['fila_excel']}: el QR no se lee igual"
        print(f"\nQR generados: {len(equipos)}")
    for v, n in sorted(versiones.items()):
        modulos = 17 + 4 * v
        print(f"  versión {v:>2}: {n:>3} QR · {modulos} módulos · "
              f"módulo de {TAM_QR_CM * 10 / modulos:.2f} mm a {TAM_QR_CM} cm")
    if zxingcpp:
        print("OK: todos los QR se leen de vuelta con su enlace exacto")
