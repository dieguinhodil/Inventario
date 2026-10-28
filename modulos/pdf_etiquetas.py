"""
pdf_etiquetas.py — Paso 7 del diagrama de flujo: arma el PDF imprimible de etiquetas.

Contrato (arquitectura.md, sección 7):
    armar_pdf(equipos: list[dict], ruta_pdf: str, tam_cm=config.TAM_ETIQUETA_CM) -> str

- Cada equipo trae "ruta_qr" (PNG de generador_qr) e "id_final".
- Etiqueta de tam_cm × tam_cm: QR + id_final en texto debajo.
- Hoja carta, rejilla automática (4 × 5 = 20 etiquetas con 5 × 5 cm), líneas de corte tenues.
- Librería reportlab. Devuelve la ruta del PDF.

Medidas de la etiqueta de 5 × 5 cm (de arriba hacia abajo):

    ┌──────────── 50 mm ────────────┐
    │          3.5 mm margen        │
    │   6.5 ┌───────────────┐ 6.5   │
    │       │   QR 37 mm    │       │
    │       └───────────────┘       │
    │       3.5 mm separación       │
    │       CRM GDL 06 01 10        │  texto ~2.3 mm (Helvetica Bold 9 pt)
    │         ~3.7 mm margen        │
    └───────────────────────────────┘

- Decisión del pendiente de espacio vertical (arquitectura.md, sección 3): el QR mide 37 mm
  (3.5 + 37 + 3.5 + 2.5 + 3.5 = 50 mm). Se eligió 3.5 mm de margen en lugar de 3 mm para que
  la zona blanca mida al menos 4 módulos en TODAS las versiones de QR:
  versión 8 (49 módulos) → módulo de 0.76 mm → 4 módulos = 3.02 mm ≤ 3.5 mm.
  El módulo más pequeño (versión 12, 65 módulos) queda en 37/65 = 0.57 mm (> 0.5 mm).
- El lado del QR es config.TAM_QR_CM (3.7 cm), el mismo que usa generador_qr para avisar si
  el módulo impreso queda por debajo de 0.5 mm (por eso este módulo no repite ese aviso).
  Si no cabe en la etiqueta con estos márgenes, se detiene con un error claro.
- Los PNG no traen margen y miden de 490 a 650 px: se dibujan SIEMPRE al lado fijo del QR
  (drawImage con width/height), nunca a su tamaño natural.
- El QR se pasa a reportlab en escala de grises (8 bits): el PDF queda ~35 % más ligero que
  si se le da el PNG de 1 bit (que reportlab guarda como color). Se ve idéntico.
- Las líneas de corte rodean solo las etiquetas usadas (la última hoja no lleva cuadros vacíos).
- Pie de página fuera de las etiquetas: hoja N de M, rango de etiquetas, fecha y aviso de
  imprimir a tamaño real. El PDF además pide al visor imprimir sin escalar (PrintScaling=None).
- Las etiquetas salen en el mismo orden de la lista (fila_excel), de izquierda a derecha
  y de arriba hacia abajo.

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (293 etiquetas, 15 hojas; los 293 QR se leen
de vuelta del PDF con su enlace exacto).
"""

import math
import os
import sys
import warnings
from datetime import date
from pathlib import Path

if __name__ == "__main__":  # permite probarlo solo: python modulos/pdf_etiquetas.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

import config


# --- Medidas (en mm) ---------------------------------------------------------
MARGEN_MM = 3.5            # zona blanca alrededor del QR (arriba, lados y entre QR y texto)
TEXTO_MM = 2.5             # franja reservada para el texto del ID
MARGEN_PAGINA_MIN_MM = 6   # margen mínimo de la hoja (zona que muchas impresoras no imprimen)
PIE_MIN_MM = 10            # solo se dibuja el pie si el margen inferior mide al menos esto

# --- Texto del ID -----------------------------------------------------------
FUENTE = "Helvetica-Bold"
FUENTE_PT = 9
FUENTE_MIN_PT = 6          # si el ID no cabe a 9 pt se reduce hasta este tamaño
ALTURA_MAYUSCULAS = 0.718  # CapHeight de Helvetica-Bold (archivo AFM de Adobe), en fracción del tamaño

# --- Líneas de corte y pie -----------------------------------------------------
GRIS_CORTE = 0.78          # 0 = negro, 1 = blanco
GROSOR_CORTE_PT = 0.3
GRIS_PIE = 0.45
PIE_PT = 7

TAMANO_HOJA = letter       # carta: 215.9 × 279.4 mm


def _altura_mayusculas_mm(tam_pt):
    """Altura de una mayúscula/dígito de FUENTE a tam_pt, en mm."""
    return ALTURA_MAYUSCULAS * tam_pt * 25.4 / 72


def calcular_geometria(tam_cm=config.TAM_ETIQUETA_CM):
    """Devuelve todas las medidas (mm) de la etiqueta y de la rejilla en la hoja.
    La usa armar_pdf() y la prueba de abajo (para recortar cada etiqueta al leerla)."""
    tam = float(tam_cm) * 10
    qr = float(config.TAM_QR_CM) * 10

    # Lo que queda tras margen arriba, separación, texto y margen abajo
    qr_max = tam - 3 * MARGEN_MM - TEXTO_MM
    if not 0 < qr <= qr_max + 1e-6:
        raise ValueError(
            f"config.TAM_QR_CM = {config.TAM_QR_CM} cm no cabe en una etiqueta de {tam_cm} cm "
            f"con márgenes de {MARGEN_MM} mm (máximo {qr_max / 10:.2f} cm)."
        )

    ancho_hoja = TAMANO_HOJA[0] / mm
    alto_hoja = TAMANO_HOJA[1] / mm
    columnas = int((ancho_hoja - 2 * MARGEN_PAGINA_MIN_MM + 1e-6) // tam)
    filas = int((alto_hoja - 2 * MARGEN_PAGINA_MIN_MM + 1e-6) // tam)
    if columnas < 1 or filas < 1:
        raise ValueError(f"Una etiqueta de {tam_cm} cm no cabe en la hoja carta.")

    return {
        "tam_mm": tam,
        "qr_mm": qr,
        "ancho_hoja_mm": ancho_hoja,
        "alto_hoja_mm": alto_hoja,
        "columnas": columnas,
        "filas": filas,
        "por_hoja": columnas * filas,
        "margen_x_mm": (ancho_hoja - columnas * tam) / 2,   # rejilla centrada
        "margen_y_mm": (alto_hoja - filas * tam) / 2,
    }


def posicion_etiqueta(g, indice_en_hoja):
    """Esquina inferior izquierda (mm, origen abajo-izquierda como en el PDF) de la etiqueta."""
    columna = indice_en_hoja % g["columnas"]
    fila = indice_en_hoja // g["columnas"]          # fila 0 = arriba
    x = g["margen_x_mm"] + columna * g["tam_mm"]
    y = g["alto_hoja_mm"] - g["margen_y_mm"] - (fila + 1) * g["tam_mm"]
    return x, y


def _tamano_fuente(texto, ancho_disponible_mm):
    """Tamaño de letra para que el ID quepa a lo ancho (de FUENTE_PT hacia abajo)."""
    tam_pt = FUENTE_PT
    while stringWidth(texto, FUENTE, tam_pt) / mm > ancho_disponible_mm and tam_pt > FUENTE_MIN_PT:
        tam_pt -= 0.5
    return tam_pt


def _validar(equipos, g):
    """Revisa todo ANTES de escribir el PDF, para no dejar un archivo a medias."""
    if not equipos:
        raise ValueError("No hay equipos para armar el PDF de etiquetas.")

    for equipo in equipos:
        fila = equipo.get("fila_excel", "?")
        for campo in ("ruta_qr", "id_final"):
            if not str(equipo.get(campo) or "").strip():
                raise KeyError(
                    f"El equipo de la fila {fila} no tiene '{campo}'. "
                    "Corre ids.asignar_ids() y generador_qr.generar_qr() antes de armar el PDF."
                )
        ruta = os.fspath(equipo["ruta_qr"])
        if not os.path.isfile(ruta):
            raise FileNotFoundError(f"Fila {fila}: no existe la imagen QR {ruta}")

        with Image.open(ruta) as imagen:
            ancho, alto = imagen.size
        if ancho != alto:
            raise ValueError(f"Fila {fila}: el QR {ruta} no es cuadrado ({ancho} × {alto} px).")

        ancho_texto = g["tam_mm"] - 2 * MARGEN_MM
        id_texto = str(equipo["id_final"])
        if stringWidth(id_texto, FUENTE, FUENTE_MIN_PT) / mm > ancho_texto:
            warnings.warn(
                f"Fila {fila}: el ID {id_texto!r} no cabe completo en la etiqueta "
                f"ni a {FUENTE_MIN_PT} pt; se imprime igual y puede salirse del margen.",
                stacklevel=3,
            )


def _dibujar_etiqueta(c, g, x, y, ruta_qr, id_texto):
    tam, qr = g["tam_mm"], g["qr_mm"]

    # Línea de corte (borde de la etiqueta)
    c.rect(x * mm, y * mm, tam * mm, tam * mm, stroke=1, fill=0)

    # QR centrado, a MARGEN_MM del borde superior, siempre a lado fijo
    qr_x = x + (tam - qr) / 2
    qr_y = y + tam - MARGEN_MM - qr
    # En escala de grises: reportlab guardaría el PNG de 1 bit como color (≈35 % más pesado)
    with Image.open(ruta_qr) as imagen:
        imagen_gris = ImageReader(imagen.convert("L"))
    c.drawImage(imagen_gris, qr_x * mm, qr_y * mm, width=qr * mm, height=qr * mm)

    # ID centrado debajo; la parte alta de las letras queda a MARGEN_MM del QR
    tam_pt = _tamano_fuente(id_texto, tam - 2 * MARGEN_MM)
    base = qr_y - MARGEN_MM - _altura_mayusculas_mm(tam_pt)
    c.setFont(FUENTE, tam_pt)
    c.setFillGray(0)
    c.drawCentredString((x + tam / 2) * mm, base * mm, id_texto)


def _dibujar_pie(c, g, hoja, total_hojas, primera, ultima, total):
    if g["margen_y_mm"] < PIE_MIN_MM:
        return  # no hay espacio: se omite el pie
    texto = (f"Etiquetas QR · Inventario {config.HOJA} · hoja {hoja} de {total_hojas} · "
             f"etiquetas {primera}–{ultima} de {total} · generado {date.today().isoformat()} · "
             f"imprimir a tamaño real (100 %)")
    c.setFont("Helvetica", PIE_PT)
    c.setFillGray(GRIS_PIE)
    c.drawCentredString(g["ancho_hoja_mm"] / 2 * mm, g["margen_y_mm"] / 2 * mm, texto)


def armar_pdf(equipos, ruta_pdf, tam_cm=config.TAM_ETIQUETA_CM):
    """Arma el PDF de etiquetas (QR + id_final) en hoja carta y devuelve su ruta."""
    g = calcular_geometria(tam_cm)
    _validar(equipos, g)

    ruta_pdf = os.fspath(ruta_pdf)
    carpeta = os.path.dirname(ruta_pdf)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    total = len(equipos)
    total_hojas = math.ceil(total / g["por_hoja"])

    c = canvas.Canvas(ruta_pdf, pagesize=TAMANO_HOJA, pageCompression=1)
    c.setTitle(f"Etiquetas QR — Inventario {config.HOJA}")
    c.setAuthor("Inventario de equipo biomédico")
    c.setSubject(f"{total} etiquetas de {tam_cm} × {tam_cm} cm")
    c.setCreator("Inventario · modulos/pdf_etiquetas.py")
    c.setViewerPreference("PrintScaling", "None")  # pedir impresión a tamaño real

    for indice, equipo in enumerate(equipos):
        en_hoja = indice % g["por_hoja"]
        if en_hoja == 0:
            if indice > 0:
                c.showPage()
            hoja = indice // g["por_hoja"] + 1
            ultima = min(indice + g["por_hoja"], total)
            _dibujar_pie(c, g, hoja, total_hojas, indice + 1, ultima, total)
            c.setStrokeGray(GRIS_CORTE)
            c.setLineWidth(GROSOR_CORTE_PT)

        x, y = posicion_etiqueta(g, en_hoja)
        _dibujar_etiqueta(c, g, x, y, os.fspath(equipo["ruta_qr"]), str(equipo["id_final"]))

    c.save()  # cierra también la última hoja
    return ruta_pdf


# ---------------------------------------------------------------------------
# Prueba independiente:
#   python modulos/pdf_etiquetas.py
#       → 3 QR de ejemplo → salida/prueba_etiquetas.pdf
#   python modulos/pdf_etiquetas.py --excel INVENTARIO_JUNIO_2025.xlsx
#       → todos los equipos del Excel (pasos 1–6) → salida/prueba_etiquetas.pdf
# Si están instalados pypdfium2 y zxing-cpp (pip install pypdfium2 zxing-cpp), además
# convierte cada hoja en imagen, lee cada QR y cada ID de vuelta y los compara.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import tempfile

    from modulos import enlaces, generador_qr

    parser = argparse.ArgumentParser(description="Prueba del PDF de etiquetas")
    parser.add_argument("--excel", help="Probar con todos los equipos de este Excel")
    parser.add_argument("--salida", default=os.path.join(config.CARPETA_SALIDA, "prueba_etiquetas.pdf"))
    parser.add_argument("--ppp", type=int, default=200, help="Resolución al leer de vuelta (puntos por pulgada)")
    args = parser.parse_args()

    try:
        import pypdfium2
        import zxingcpp
    except ImportError:
        pypdfium2 = zxingcpp = None

    g = calcular_geometria()
    print(f"Etiqueta {g['tam_mm']:.0f} mm · QR {g['qr_mm']:.1f} mm · margen {MARGEN_MM} mm · "
          f"rejilla {g['columnas']} × {g['filas']} = {g['por_hoja']} por hoja · "
          f"márgenes de hoja {g['margen_x_mm']:.1f} × {g['margen_y_mm']:.1f} mm")

    with tempfile.TemporaryDirectory() as carpeta:
        if args.excel:
            from modulos import filtros, ids, lector_excel, limpieza
            incluidos, _ = filtros.separar_por_estatus(limpieza.limpiar(lector_excel.leer_hoja(args.excel)))
            equipos = ids.asignar_ids(incluidos)
        else:
            base = {"tipo": "Monitor", "marca": "Mindray", "modelo": "uMEC10", "area": "Urgencias",
                    "estatus": "Funcional", "ultimo_mprev": "2025-01-15"}
            equipos = [
                dict(base, id_final="CRM GDL 06 01 10", serie="ABC123", fila_excel=5),
                dict(base, id_final="TMP-001", serie="S/D", fila_excel=6),
                dict(base, id_final="CRM GDL 06 13 05", fila_excel=7,
                     tipo="Máquina de Anestesia", marca="Puritan Bennett (Medtronic)",
                     modelo="Fabius GS Premium con vaporizador", serie="X" * 60,
                     area="Quirófano", estatus="Fuera de Servicio"),   # enlace largo → QR grande
            ]

        for e in equipos:
            e["enlace"] = enlaces.construir_enlace(e)
            e["ruta_qr"] = generador_qr.generar_qr(
                e["enlace"], os.path.join(carpeta, e["id_final"].replace(" ", "_") + ".png"))

        ruta = armar_pdf(equipos, args.salida)
        hojas = math.ceil(len(equipos) / g["por_hoja"])
        print(f"PDF: {ruta} · {len(equipos)} etiquetas · {hojas} hoja(s)")

    if not pypdfium2:
        print("(pypdfium2 o zxing-cpp no están instalados: no se comprobó la lectura)")
        sys.exit(0)

    # Leer de vuelta: cada etiqueta se recorta por separado y se lee su QR y su texto
    pdf = pypdfium2.PdfDocument(ruta)
    assert len(pdf) == hojas, f"se esperaban {hojas} hojas y hay {len(pdf)}"
    escala = args.ppp / 72
    a_px = lambda v: round(v * mm * escala)
    hoja_actual = None
    for indice, e in enumerate(equipos):
        numero_hoja, en_hoja = divmod(indice, g["por_hoja"])
        pagina = pdf[numero_hoja]
        if numero_hoja != hoja_actual:  # cada hoja se convierte en imagen una sola vez
            imagen = pagina.render(scale=escala, grayscale=True).to_pil()
            hoja_actual = numero_hoja
        # QR
        x, y = posicion_etiqueta(g, en_hoja)
        recorte = imagen.crop((a_px(x), imagen.height - a_px(y + g["tam_mm"]),
                               a_px(x + g["tam_mm"]), imagen.height - a_px(y)))
        # Solo formato QR: a baja resolución zxing a veces "ve" un código de barras lineal
        # falso dentro del propio QR
        leidos = zxingcpp.read_barcodes(recorte, formats=zxingcpp.BarcodeFormat.QRCode)
        assert len(leidos) == 1, f"fila {e['fila_excel']}: se leyeron {len(leidos)} QR en la etiqueta"
        assert leidos[0].text == e["enlace"], f"fila {e['fila_excel']}: el QR no se lee igual"
        # Texto del ID
        texto = pagina.get_textpage().get_text_bounded(
            left=x * mm, bottom=y * mm, right=(x + g["tam_mm"]) * mm, top=(y + g["tam_mm"]) * mm).strip()
        assert texto == e["id_final"], f"fila {e['fila_excel']}: texto {texto!r} ≠ {e['id_final']!r}"
    print(f"OK: los {len(equipos)} QR se leen a {args.ppp} ppp con su enlace exacto "
          f"y cada etiqueta muestra su id_final")