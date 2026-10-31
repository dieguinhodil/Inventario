"""
config.py — Constantes compartidas de la app de inventario (versión 2).

Cualquier cambio aquí se acuerda en el chat de arquitectura y se anota en arquitectura.md.
Aquí NO van secretos: la clave secreta y la base de datos viven en instancia/ (fuera de git).
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Rutas --------------------------------------------------------------------
# Todas las rutas se calculan a partir de la carpeta de este archivo, para que funcionen
# igual en la laptop (flask run) y en PythonAnywhere (donde la carpeta de trabajo es otra).
CARPETA_BASE = Path(__file__).resolve().parent
CARPETA_INSTANCIA = CARPETA_BASE / "instancia"              # NUNCA se sube a git
RUTA_DB = CARPETA_INSTANCIA / "inventario.db"
RUTA_CLAVE_SECRETA = CARPETA_INSTANCIA / "clave_secreta.txt"  # se genera una vez; nunca en el código

# --- Servidor -------------------------------------------------------------------
# Cuenta de PythonAnywhere de la Jefatura de Biomédica: usuario "Bi0medic4CRM" (con cero y cuatro).
# PythonAnywhere usa el subdominio en minúsculas. NO cambiar: los QR impresos llevan esta dirección.
BASE_URL = "https://bi0medic4crm.pythonanywhere.com"
RUTA_FICHA = "/e/"                     # dirección pública de la ficha: BASE_URL + RUTA_FICHA + codigo

# True solo en PythonAnywhere (se define la variable de entorno INVENTARIO_PRODUCCION=1 en su
# archivo WSGI). Activa la cookie de sesión "Secure", que en la laptop (sin HTTPS) impediría entrar.
ES_PRODUCCION = os.environ.get("INVENTARIO_PRODUCCION") == "1"

# --- Zona horaria ----------------------------------------------------------------
# PythonAnywhere trabaja en UTC: todas las fechas y horas se guardan y muestran en hora de
# Ciudad de México, con su desfase (ej. 2026-10-29T16:45:00-06:00). En Windows requiere `pip install tzdata`.
ZONA_HORARIA = ZoneInfo("America/Mexico_City")

# --- Código aleatorio del QR ---------------------------------------------------------
LARGO_CODIGO = 8
ALFABETO_CODIGO = "23456789abcdefghjkmnpqrstuvwxyz"   # sin 0, o, 1, l, i (se confunden al leerlos)

# --- Inicio de sesión ------------------------------------------------------------------
MAX_INTENTOS = 5          # intentos fallidos de un mismo USUARIO...
MAX_INTENTOS_IP = 20      # intentos fallidos desde una misma IP (más alto: en el hospital varios usuarios comparten IP)
MINUTOS_BLOQUEO = 15      # ...en esta ventana → bloqueo durante este tiempo

# --- Catálogos ---------------------------------------------------------------------------
ESTATUS = ["Funcional", "En Revisión", "En Mantenimiento", "Fuera de Servicio", "No Funcional", "Baja"]
ESTATUS_EXCLUIDOS = ["baja"]      # en minúsculas: sin TMP al importar, sin QR y ocultos en la búsqueda
TIPOS_MANTENIMIENTO = ["preventivo", "correctivo"]

# --- Texto fijo de la ficha ------------------------------------------------------------------
CUENTA_FIJA = "Cruz Roja Mexicana"
UBICACION_FIJA = "Delegación Guadalajara"

# --- Etiquetas y QR -------------------------------------------------------------------------
TAM_ETIQUETA_CM = 3       # antes 5
TAM_QR_CM = 2.1           # antes 3.7; el valor exacto se fija en el chat de etiquetas
CORRECCION_QR = "M"

# --- Importación del Excel (versión 1, la usa importar_excel.py) ---------------------------
RUTA_EXCEL = CARPETA_BASE / "INVENTARIO_JUNIO_2025.xlsx"   # se puede cambiar con --excel
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

SIN_ID = "Sin información"
FORMATO_ID = r"^CRM GDL \d{2} \d{2} \d{2}$"
PREFIJO_TMP = "TMP-"
DESCRIPCION_MPREV_IMPORTADO = "Importado del inventario de junio 2025"

# --- Normalización ----------------------------------------------------------------------------
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