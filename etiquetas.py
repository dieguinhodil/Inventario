"""
etiquetas.py — PDF de etiquetas QR de 3 × 3 cm (versión 2).

Base: pdf_etiquetas.py de la versión 1 (zona blanca de al menos 4 módulos, QR a lado fijo,
ID en texto debajo, impresión a tamaño real). Diferencias:
    - No lee ni escribe archivos: devuelve el PDF en memoria (bytes) para mandarlo como descarga.
    - El QR se dibuja como figuras vectoriales (no como imagen): sale nítido en cualquier
      impresora y el PDF pesa menos.
    - Dos formatos (arquitectura, decisión del chat 5):
        pdf_una(equipo)     → una página de exactamente 3 × 3 cm (impresora de etiquetas en rollo)
        pdf_hoja(equipos)   → hojas carta con cuadrícula de 6 × 8 = 48 etiquetas y líneas de corte
    - Solo llevan etiqueta los equipos que NO están en Baja y que SÍ tienen ID interno
      (decisión del chat 5). motivo_sin_etiqueta() dice por qué un equipo no puede llevarla.

Medidas de la etiqueta de 30 mm (config.TAM_ETIQUETA_CM = 3, config.TAM_QR_CM = 2.1).
El enlace siempre mide 50 caracteres → QR versión 4 (33 módulos): módulo de 21 / 33 = 0.636 mm.

    ┌──────────── 30 mm ────────────┐
    │   2.55 mm (4 módulos)         │
    │   4.5 ┌─────────────┐ 4.5     │
    │       │  QR 21 mm   │         │
    │       └─────────────┘         │
    │   2.55 mm (4 módulos)         │
    │       CRM GDL 06 01 10        │  Helvetica Bold 7 pt (mayúsculas de 1.8 mm, 21.8 mm de ancho)
    │   ~2.1 mm                     │
    └───────────────────────────────┘

- La zona blanca de 4 módulos queda DENTRO de la etiqueta por los cuatro lados (también entre
  el QR y el texto): la superficie del equipo alrededor de la etiqueta puede no ser blanca.
- Si el ID no cabe a 7 pt se reduce hasta 5 pt; si ni así cabe, el equipo no puede llevar
  etiqueta hasta que se acorte su ID.
- Si se cambia TAM_QR_CM o TAM_ETIQUETA_CM y ya no cabe todo (o el módulo queda por debajo
  de 0.5 mm), se detiene con un error claro en lugar de generar etiquetas que no se lean bien.

No depende de Flask (sí de db.py, solo para normalizar el estatus).
"""

import io
import math
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

import config
import db
import qr

# --- Medidas (en mm) ---------------------------------------------------------------------------
MODULOS_ZONA_BLANCA = 4        # el estándar del QR pide al menos 4 módulos blancos alrededor
MODULO_MIN_MM = 0.5            # por debajo de esto la lectura con el teléfono es menos confiable
MARGEN_TEXTO_MM = 2.0          # margen a los lados del ID
MARGEN_INFERIOR_MIN_MM = 1.0   # espacio mínimo bajo el ID (tolerancia al recortar)
MARGEN_PAGINA_MIN_MM = 6       # zona de la hoja que muchas impresoras no imprimen
PIE_MIN_MM = 10                # el pie de la hoja solo se dibuja si el margen inferior lo permite

# --- Texto del ID ------------------------------------------------------------------------------
FUENTE = "Helvetica-Bold"
FUENTE_PT = 7
FUENTE_MIN_PT = 5
ALTURA_MAYUSCULAS = 0.718      # CapHeight de Helvetica-Bold (AFM de Adobe), fracción del tamaño

# --- Líneas de corte y pie de la hoja ------------------------------------------------------------
GRIS_CORTE = 0.78              # 0 = negro, 1 = blanco
GROSOR_CORTE_PT = 0.3
GRIS_PIE = 0.45
PIE_PT = 7

TAMANO_HOJA = letter           # carta: 215.9 × 279.4 mm
TITULO = "Inventario de equipo biomédico"

MENSAJE_BAJA = "Los equipos en Baja no llevan etiqueta."
MENSAJE_SIN_ID = ("Este equipo no tiene ID interno. Asígnale uno con «Editar» para poder "
                  "imprimir su etiqueta.")
MENSAJE_ID_LARGO = ("El ID interno es demasiado largo para la etiqueta de "
                    f"{config.TAM_ETIQUETA_CM} cm. Acórtalo con «Editar» para poder imprimirla.")
MENSAJE_ID_CARACTERES = ("El ID interno tiene caracteres que no se pueden imprimir en la "
                         "etiqueta. Corrígelo con «Editar».")


class ErrorEtiqueta(ValueError):
    """El equipo no puede llevar etiqueta. El mensaje se puede mostrar tal cual al usuario."""


# --- Qué equipos llevan etiqueta -------------------------------------------------------------

def _altura_mayusculas_mm(tam_pt):
    return ALTURA_MAYUSCULAS * tam_pt * 25.4 / 72


def _ancho_texto_mm():
    return config.TAM_ETIQUETA_CM * 10 - 2 * MARGEN_TEXTO_MM


def tamano_fuente(texto):
    """Tamaño de letra (pt) para que el ID quepa a lo ancho, o None si no cabe ni a FUENTE_MIN_PT."""
    tam_pt = FUENTE_PT
    while tam_pt >= FUENTE_MIN_PT:
        if stringWidth(texto, FUENTE, tam_pt) / mm <= _ancho_texto_mm():
            return tam_pt
        tam_pt -= 0.5
    return None


def texto_etiqueta(equipo):
    """Texto que va debajo del QR: el ID interno tal como está guardado."""
    return (equipo["id_interno"] or "").strip()


def motivo_sin_etiqueta(equipo):
    """Por qué este equipo no puede llevar etiqueta, o None si sí puede."""
    if db.es_baja(equipo["estatus"]):
        return MENSAJE_BAJA
    texto = texto_etiqueta(equipo)
    if not texto:
        return MENSAJE_SIN_ID
    try:
        texto.encode("cp1252")         # lo que puede escribir la fuente Helvetica del PDF
    except UnicodeEncodeError:
        return MENSAJE_ID_CARACTERES
    if tamano_fuente(texto) is None:
        return MENSAJE_ID_LARGO
    return None


def separar(equipos):
    """Divide una lista de equipos en (imprimibles, excluidos). `excluidos` es una lista de
    (equipo, motivo)."""
    imprimibles, excluidos = [], []
    for equipo in equipos:
        motivo = motivo_sin_etiqueta(equipo)
        if motivo is None:
            imprimibles.append(equipo)
        else:
            excluidos.append((equipo, motivo))
    return imprimibles, excluidos


def ordenar_para_imprimir(equipos):
    """Orden de las etiquetas en las hojas: por área (las de una misma área quedan juntas, para
    repartirlas más fácil; sin área al final) y después por ID."""
    def llave(equipo):
        area = db.normalizar_texto(equipo["area"])
        return (area == "", area, db.normalizar_texto(equipo["id_interno"]), equipo["num"])
    return sorted(equipos, key=llave)


# --- Medidas ---------------------------------------------------------------------------------

def calcular_medidas(modulos):
    """Medidas (mm) de la etiqueta para un QR de `modulos` por lado. Revisa que todo quepa."""
    tam = float(config.TAM_ETIQUETA_CM) * 10
    lado_qr = float(config.TAM_QR_CM) * 10
    modulo = lado_qr / modulos
    zona = MODULOS_ZONA_BLANCA * modulo

    if modulo < MODULO_MIN_MM - 1e-9:
        raise ValueError(
            f"Con config.TAM_QR_CM = {config.TAM_QR_CM} cm y {modulos} módulos, cada módulo mide "
            f"{modulo:.2f} mm (mínimo {MODULO_MIN_MM} mm): el QR costaría leerlo con el teléfono.")
    if lado_qr + 2 * zona > tam + 1e-9:
        raise ValueError(
            f"Un QR de {config.TAM_QR_CM} cm con su zona blanca de {MODULOS_ZONA_BLANCA} módulos "
            f"no cabe a lo ancho en una etiqueta de {config.TAM_ETIQUETA_CM} cm.")
    alto_minimo = (zona + lado_qr + zona + _altura_mayusculas_mm(FUENTE_PT)
                   + MARGEN_INFERIOR_MIN_MM)
    if alto_minimo > tam + 1e-9:
        raise ValueError(
            f"El QR de {config.TAM_QR_CM} cm, su zona blanca y el ID no caben a lo alto en una "
            f"etiqueta de {config.TAM_ETIQUETA_CM} cm (hacen falta {alto_minimo:.1f} mm).")
    return {"tam_mm": tam, "qr_mm": lado_qr, "modulo_mm": modulo, "zona_mm": zona}


def calcular_hoja(tam_mm):
    """Cuadrícula de etiquetas en la hoja carta, centrada."""
    ancho = TAMANO_HOJA[0] / mm
    alto = TAMANO_HOJA[1] / mm
    columnas = int((ancho - 2 * MARGEN_PAGINA_MIN_MM + 1e-6) // tam_mm)
    filas = int((alto - 2 * MARGEN_PAGINA_MIN_MM + 1e-6) // tam_mm)
    return {
        "ancho_mm": ancho, "alto_mm": alto, "columnas": columnas, "filas": filas,
        "por_hoja": columnas * filas,
        "margen_x_mm": (ancho - columnas * tam_mm) / 2,
        "margen_y_mm": (alto - filas * tam_mm) / 2,
    }


def etiquetas_por_hoja():
    """Cuántas etiquetas caben en una hoja carta (6 × 8 = 48 con etiquetas de 3 cm)."""
    return calcular_hoja(float(config.TAM_ETIQUETA_CM) * 10)["por_hoja"]


def posicion_en_hoja(hoja, tam_mm, indice):
    """Esquina inferior izquierda (mm, origen abajo a la izquierda) de la etiqueta `indice` de
    la hoja: de izquierda a derecha y de arriba hacia abajo."""
    columna = indice % hoja["columnas"]
    fila = indice // hoja["columnas"]
    x = hoja["margen_x_mm"] + columna * tam_mm
    y = hoja["alto_mm"] - hoja["margen_y_mm"] - (fila + 1) * tam_mm
    return x, y


# --- Dibujo ----------------------------------------------------------------------------------

def _preparar(equipo):
    """Cuadrícula del QR y texto del ID, o ErrorEtiqueta si el equipo no lleva etiqueta."""
    motivo = motivo_sin_etiqueta(equipo)
    if motivo is not None:
        raise ErrorEtiqueta(motivo)
    return qr.matriz(qr.enlace_equipo(equipo["codigo"])), texto_etiqueta(equipo)


def _dibujar_etiqueta(c, x, y, cuadricula, texto):
    """Dibuja una etiqueta con su esquina inferior izquierda en (x, y) mm."""
    m = calcular_medidas(len(cuadricula))
    tam, lado, modulo, zona = m["tam_mm"], m["qr_mm"], m["modulo_mm"], m["zona_mm"]

    # QR centrado a lo ancho, con su zona blanca arriba. Cada tramo de módulos negros seguidos
    # de una fila es un rectángulo; todos van en un solo trazo (sin rayitas entre filas).
    qr_x = x + (tam - lado) / 2
    qr_arriba = y + tam - zona
    trazo = c.beginPath()
    for fila, valores in enumerate(cuadricula):
        fila_y = qr_arriba - (fila + 1) * modulo
        columna = 0
        while columna < len(valores):
            if valores[columna]:
                inicio = columna
                while columna < len(valores) and valores[columna]:
                    columna += 1
                trazo.rect((qr_x + inicio * modulo) * mm, fila_y * mm,
                           (columna - inicio) * modulo * mm, modulo * mm)
            else:
                columna += 1
    c.setFillGray(0)
    c.drawPath(trazo, stroke=0, fill=1)

    # ID centrado debajo; la parte alta de las letras queda a 4 módulos del QR.
    tam_pt = tamano_fuente(texto)
    base = qr_arriba - lado - zona - _altura_mayusculas_mm(tam_pt)
    c.setFont(FUENTE, tam_pt)
    c.drawCentredString((x + tam / 2) * mm, base * mm, texto)


def _nuevo_pdf(salida, tamano, titulo, asunto):
    c = canvas.Canvas(salida, pagesize=tamano, pageCompression=1)
    c.setTitle(titulo)
    c.setAuthor(TITULO)
    c.setSubject(asunto)
    c.setCreator("Inventario · etiquetas.py")
    c.setViewerPreference("PrintScaling", "None")   # pedir impresión a tamaño real
    return c


def pdf_una(equipo):
    """PDF de una sola etiqueta en una página de exactamente TAM_ETIQUETA_CM × TAM_ETIQUETA_CM
    (para impresora de etiquetas en rollo). Lanza ErrorEtiqueta si el equipo no lleva etiqueta."""
    cuadricula, texto = _preparar(equipo)
    tam = calcular_medidas(len(cuadricula))["tam_mm"]
    salida = io.BytesIO()
    c = _nuevo_pdf(salida, (tam * mm, tam * mm), f"Etiqueta QR — {texto}",
                   f"Etiqueta de {config.TAM_ETIQUETA_CM} × {config.TAM_ETIQUETA_CM} cm")
    _dibujar_etiqueta(c, 0, 0, cuadricula, texto)
    c.save()
    return salida.getvalue()


def _dibujar_pie(c, hoja, numero, total_hojas, primera, ultima, total, momento):
    if hoja["margen_y_mm"] < PIE_MIN_MM:
        return
    texto = (f"{TITULO} · hoja {numero} de {total_hojas} · etiquetas {primera}–{ultima} de "
             f"{total} · {momento:%Y-%m-%d %H:%M} · imprimir a tamaño real (100 %), "
             f"sin ajustar a la página")
    c.setFont("Helvetica", PIE_PT)
    c.setFillGray(GRIS_PIE)
    c.drawCentredString(hoja["ancho_mm"] / 2 * mm, hoja["margen_y_mm"] / 2 * mm, texto)


def pdf_hoja(equipos):
    """PDF de una o varias etiquetas en hojas carta, con líneas de corte tenues alrededor de
    cada etiqueta usada y un pie con el número de hoja. Las etiquetas salen en el orden de la
    lista. Lanza ErrorEtiqueta si la lista está vacía o algún equipo no lleva etiqueta (se revisa
    todo antes de dibujar)."""
    if not equipos:
        raise ErrorEtiqueta("No hay equipos con etiqueta para imprimir.")
    preparados = []
    for equipo in equipos:
        try:
            preparados.append(_preparar(equipo))
        except ErrorEtiqueta as error:
            nombre = texto_etiqueta(equipo) or f"número {equipo['num']}"
            raise ErrorEtiqueta(f"Equipo {nombre}: {error}") from error

    tam = calcular_medidas(len(preparados[0][0]))["tam_mm"]
    hoja = calcular_hoja(tam)
    total = len(preparados)
    total_hojas = math.ceil(total / hoja["por_hoja"])
    momento = datetime.now(config.ZONA_HORARIA)

    salida = io.BytesIO()
    c = _nuevo_pdf(salida, TAMANO_HOJA, f"Etiquetas QR — {TITULO}",
                   f"{total} etiquetas de {config.TAM_ETIQUETA_CM} × {config.TAM_ETIQUETA_CM} cm")
    for indice, (cuadricula, texto) in enumerate(preparados):
        en_hoja = indice % hoja["por_hoja"]
        if en_hoja == 0:
            if indice > 0:
                c.showPage()
            _dibujar_pie(c, hoja, indice // hoja["por_hoja"] + 1, total_hojas, indice + 1,
                         min(indice + hoja["por_hoja"], total), total, momento)
            c.setStrokeGray(GRIS_CORTE)      # hay que repetirlo en cada hoja: showPage() lo borra
            c.setLineWidth(GROSOR_CORTE_PT)
        x, y = posicion_en_hoja(hoja, tam, en_hoja)
        c.rect(x * mm, y * mm, tam * mm, tam * mm, stroke=1, fill=0)    # línea de corte
        _dibujar_etiqueta(c, x, y, cuadricula, texto)
    c.save()
    return salida.getvalue()