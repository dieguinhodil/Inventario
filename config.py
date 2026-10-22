"""
Constantes compartidas por todos los módulos.
Cualquier cambio aquí se acuerda en el chat de arquitectura y se anota en arquitectura.md.
"""

# --- Origen de datos -------------------------------------------------------
RUTA_EXCEL = "INVENTARIO_JUNIO_2025.xlsx"   # se puede cambiar con --excel
HOJA = "GUADALAJARA"
PRIMERA_FILA = 5          # encabezados en la fila 4
COL_INI, COL_FIN = 2, 11  # columnas B..K

# Nombre de cada columna (B..K) en el diccionario "equipo"
COLUMNAS = [
    "id",            # B  ID Interno
    "cuenta",        # C  Cuenta
    "tipo",          # D  Tipo Activo
    "marca",         # E  Marca
    "modelo",        # F  Modelo
    "serie",         # G  No. Serie
    "ubicacion",     # H  Ubicación
    "area",          # I  Área
    "estatus",       # J  Estatus
    "ultimo_mprev",  # K  Último Mantenimiento Preventivo
]

# --- Reglas -----------------------------------------------------------------
SIN_ID = "Sin información"
ESTATUS_EXCLUIDOS = ["baja"]                  # en minúsculas
FORMATO_ID = r"^CRM GDL \d{2} \d{2} \d{2}$"
PREFIJO_TMP = "TMP-"

# --- Enlace del QR ----------------------------------------------------------
BASE_URL = "https://dieguinhodil.github.io/Inventario/"
# Orden y nombre de las claves después del '#'. Debe coincidir con docs/visor.js
CAMPOS_QR = ["id", "tipo", "marca", "modelo", "serie", "area", "estatus", "ultimo_mprev"]

# --- Etiquetas --------------------------------------------------------------
TAM_ETIQUETA_CM = 5
CORRECCION_QR = "M"

# --- Normalización (la llena el chat de limpieza) ---------------------------
# variante -> forma oficial. La comparación ignora mayúsculas, acentos y espacios extra.
NORMALIZAR_MARCAS = {
    "Hergom Medical": "HERGOM",
    "Devilbiss": "Devilbiss Healthcare",
    "Precision Medical": "Precision Medical Equipment",
    "Saps": "SAPS",
    "Torino": "Torino (Oken)",
    "Puritan Bennett": "Puritan Bennett (Medtronic)",
    "Nellcor Puritan Bennett": "Puritan Bennett (Medtronic)",
}
NORMALIZAR_TIPOS = {
    "Maquina de anestesia": "Máquina de Anestesia",
}

# --- Salidas ----------------------------------------------------------------
CARPETA_SALIDA = "salida"
CARPETA_QR = "salida/qr"
CSV_REVISION = "salida/revision_qr.csv"
CSV_EXCLUIDOS = "salida/excluidos.csv"
PDF_ETIQUETAS = "salida/etiquetas.pdf"
