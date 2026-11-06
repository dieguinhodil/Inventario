"""
respaldo.py — Respaldo del inventario (versión 2, chat 6).

Genera los dos archivos de la página "Respaldo". No depende de Flask (igual que db.py):
las rutas las registra app.py.

    - Excel (para CONSULTAR): equipos (también los de Baja), mantenimientos e información
      del respaldo. NO incluye las tablas `usuarios` ni `intentos_entrada`. No sirve para
      restaurar la app. No tiene contraseñas, pero sí datos internos (notas, nombres de
      usuario, "Realizado por"): compartirlo solo con personal autorizado.
    - Copia de la base de datos .db (para RESTAURAR), hecha con sqlite3 backup().
      Contiene los hashes de las contraseñas y las IPs de los intentos de entrada:
      guardarla con cuidado.

Uso:
    datos = respaldo.excel(conexion, "diego")
    nombre = respaldo.nombre_archivo("xlsx")    # respaldo_inventario_2026-11-06_1045.xlsx
"""

import io
import re
import tempfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

import config
import db

EXTENSIONES = ("xlsx", "db")

# Caracteres de control que openpyxl no acepta (se detiene con un error al guardar).
# Se conservan el tabulador y los saltos de línea (\t, \n, \r).
CARACTERES_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

ANCHO_MAX_COLUMNA = 50    # caracteres; las notas largas no hacen la columna enorme

ENCABEZADOS_EQUIPOS = (
    "Núm.", "Código del QR", "Enlace del QR", "ID interno", "ID original", "Tipo", "Marca",
    "Modelo", "No. de serie", "Área", "Estatus", "Núm. del padre", "ID del padre",
    "Último preventivo", "Notas", "Fila del Excel", "Creado en", "Actualizado en",
    "Actualizado por",
)
ENCABEZADOS_MANTENIMIENTOS = (
    "ID", "Núm. del equipo", "ID interno del equipo", "Código del QR del equipo", "Fecha",
    "Tipo", "Descripción", "Realizado por", "Registrado por", "Registrado en",
)

AVISO_EXCEL = ("Este Excel es para consultar. No sirve para restaurar la app: para eso se usa "
               "el archivo .db del respaldo. No contiene contraseñas, pero sí datos internos "
               "(notas y nombres de usuario): compártelo solo con personal autorizado.")


# --- Utilidades -----------------------------------------------------------------------------

def _enlace(codigo):
    """Dirección que lleva el QR del equipo (la misma fórmula que qr.enlace_equipo)."""
    return f"{config.BASE_URL}{config.RUTA_FICHA}{codigo}"


def _valor_celda(valor):
    """Texto sin caracteres de control; números y None se quedan igual."""
    if isinstance(valor, str):
        return CARACTERES_CONTROL.sub("", valor)
    return valor


def _escribir_fila(hoja, valores):
    """Agrega una fila. Todo texto se guarda COMO TEXTO, nunca como fórmula: openpyxl trataría
    una nota que empieza con "=" como fórmula y Excel la ejecutaría al abrir el archivo."""
    hoja.append([_valor_celda(v) for v in valores])
    for celda in hoja[hoja.max_row]:
        if isinstance(celda.value, str):
            celda.data_type = "s"


def _hoja_tabla(libro, titulo, encabezados, filas, primera=False):
    """Hoja con encabezado en negritas, fijo al desplazarse y con filtros."""
    hoja = libro.active if primera else libro.create_sheet()
    hoja.title = titulo
    _escribir_fila(hoja, encabezados)
    for fila in filas:
        _escribir_fila(hoja, fila)

    for celda in hoja[1]:
        celda.font = Font(bold=True)
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = f"A1:{get_column_letter(len(encabezados))}{hoja.max_row}"
    _ajustar_anchos(hoja)


def _ajustar_anchos(hoja):
    for columna in hoja.columns:
        largo = max(len(str(c.value)) if c.value is not None else 0 for c in columna)
        hoja.column_dimensions[columna[0].column_letter].width = min(largo + 2,
                                                                      ANCHO_MAX_COLUMNA)


# --- Funciones públicas -----------------------------------------------------------------------

def resumen(conexion):
    """Conteos para la página de respaldo:
    {"equipos": total, "en_baja": cuántos en Baja, "mantenimientos": total}."""
    equipos = db.buscar_equipos(conexion, incluir_baja=True)
    return {
        "equipos": len(equipos),
        "en_baja": sum(1 for e in equipos if db.es_baja(e["estatus"])),
        "mantenimientos": len(db.listar_mantenimientos(conexion)),
    }


def excel(conexion, usuario):
    """Excel del respaldo en memoria (bytes). `usuario` es quien lo descarga."""
    equipos = db.buscar_equipos(conexion, incluir_baja=True)           # todos, por num
    mantenimientos = db.listar_mantenimientos(conexion)
    por_num = {e["num"]: e for e in equipos}

    # Último preventivo de cada equipo, calculado del historial (fechas AAAA-MM-DD: el mayor
    # como texto es el más reciente). Igual que db.ultimo_preventivo, sin una consulta por equipo.
    ultimo = {}
    for m in mantenimientos:
        if m["tipo"] == "preventivo" and m["fecha"] > ultimo.get(m["equipo_num"], ""):
            ultimo[m["equipo_num"]] = m["fecha"]

    filas_equipos = []
    for e in equipos:
        padre = por_num.get(e["padre_num"]) if e["padre_num"] is not None else None
        filas_equipos.append((
            e["num"], e["codigo"], _enlace(e["codigo"]), e["id_interno"], e["id_original"],
            e["tipo"], e["marca"], e["modelo"], e["serie"], e["area"], e["estatus"],
            e["padre_num"], padre["id_interno"] if padre else None, ultimo.get(e["num"]),
            e["notas"], e["fila_excel"], e["creado_en"], e["actualizado_en"],
            e["actualizado_por"],
        ))

    filas_mantenimientos = []
    for m in mantenimientos:
        equipo = por_num.get(m["equipo_num"])
        filas_mantenimientos.append((
            m["id"], m["equipo_num"], equipo["id_interno"] if equipo else None,
            equipo["codigo"] if equipo else None, m["fecha"], m["tipo"], m["descripcion"],
            m["realizado_por"], m["registrado_por"], m["creado_en"],
        ))

    libro = Workbook()
    libro.properties.creator = "Inventario Cruz Roja Guadalajara"
    _hoja_tabla(libro, "Equipos", ENCABEZADOS_EQUIPOS, filas_equipos, primera=True)
    _hoja_tabla(libro, "Mantenimientos", ENCABEZADOS_MANTENIMIENTOS, filas_mantenimientos)

    en_baja = sum(1 for e in equipos if db.es_baja(e["estatus"]))
    info = libro.create_sheet("Información")
    for fila in (
        ("Respaldo del inventario de equipo biomédico", ""),
        ("Generado el", db.ahora()),
        ("Zona horaria", "Ciudad de México"),
        ("Descargado por", usuario),
        ("Equipos", len(equipos)),
        ("En Baja", en_baja),
        ("Activos (no en Baja)", len(equipos) - en_baja),
        ("Mantenimientos", len(mantenimientos)),
        ("Aviso", AVISO_EXCEL),
    ):
        _escribir_fila(info, fila)
    for celda in info["A"]:
        celda.font = Font(bold=True)
    info["A1"].font = Font(bold=True, size=13)
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 80
    info.cell(row=info.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")  # el aviso

    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def copia_db(conexion):
    """Copia completa de la base de datos (bytes), hecha con db.respaldar_db (sqlite3
    backup()) en un archivo temporal que se lee y se borra."""
    with tempfile.TemporaryDirectory(prefix="respaldo_") as carpeta:
        ruta = Path(carpeta) / "inventario.db"
        db.respaldar_db(conexion, ruta)
        return ruta.read_bytes()


def nombre_archivo(extension, momento=None):
    """"respaldo_inventario_2026-11-06_1045.xlsx" con la hora de Ciudad de México.
    `momento` sirve para las pruebas."""
    if extension not in EXTENSIONES:
        raise ValueError(f"Extensión no permitida: {extension}")
    momento = momento or datetime.now(config.ZONA_HORARIA)
    return f"respaldo_inventario_{momento:%Y-%m-%d_%H%M}.{extension}"
