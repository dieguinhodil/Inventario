"""
app.py — Aplicación web Flask del inventario (versión 2).

Crea la app, abre una conexión a la base de datos por petición y registra las rutas.
Toda la lógica de datos vive en db.py; aquí solo se leen los datos y se muestran.

Arranque:
    Laptop:          flask --app app run        (desde la carpeta inventario/)
    PythonAnywhere:  en su archivo WSGI →  from app import app as application

Al importarse, este archivo:
    - crea instancia/clave_secreta.txt si no existe (la clave de las cookies de sesión);
    - crea las tablas de la base de datos si no existen (no borra ni cambia datos).

Partes de este chat (chat 3): búsqueda y ficha, solo lectura.
    PROVISIONAL hasta el chat 4: `requiere_sesion` no revisa nada y no hay inicio de sesión.
    Por eso la app se niega a arrancar en producción (ver crear_app).
"""

import os
import secrets
from contextlib import closing
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, abort, current_app, g, render_template, request
from flask_wtf.csrf import CSRFProtect

import config
import db

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")

# Valores que se muestran como "Sin dato" (se comparan sin acentos ni mayúsculas).
VALORES_SIN_DATO = {"s/d", "n/a", "na", "-", "--"}

# Color de cada estatus (llave sin acentos y en minúsculas). Cualquier otro → gris.
CLASES_ESTATUS = {
    "funcional": "verde",
    "en revision": "ambar",
    "en mantenimiento": "ambar",
    "fuera de servicio": "rojo",
    "no funcional": "rojo",
    "baja": "rojo",
}

LARGO_MAX_BUSQUEDA = 100     # caracteres; cada palabra agrega 5 comparaciones a la consulta

ESTATUS_BAJA = {db.normalizar_texto(e) for e in config.ESTATUS_EXCLUIDOS}

# Política de seguridad del navegador: solo se cargan archivos de este mismo sitio.
# Consecuencia para las plantillas: nada de <script> ni style="..." escritos dentro del HTML.
POLITICA_CONTENIDO = ("default-src 'self'; img-src 'self' data:; object-src 'none'; "
                      "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")

csrf = CSRFProtect()


# --- Sesión: PROVISIONAL hasta el chat 4 ------------------------------------------------------
# El chat 4 crea auth.py con el decorador real y reemplaza este bloque por un import.
# Mientras tanto la búsqueda queda abierta, pero SOLO en la laptop (crear_app lo impide en
# producción) y las plantillas se comportan como si hubiera sesión.

def requiere_sesion(vista):
    """PROVISIONAL: no revisa nada. El chat 4 lo reemplaza por el de auth.py, que manda a
    /entrar a quien no tenga sesión."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        return vista(*args, **kwargs)
    return envoltura


def hay_sesion():
    """PROVISIONAL: True mientras SESION_PROVISIONAL esté activo. El chat 4 lo cambia para
    que diga si de verdad hay un usuario con sesión."""
    return bool(current_app.config["SESION_PROVISIONAL"])


# --- Clave secreta --------------------------------------------------------------------------

def cargar_clave_secreta(ruta):
    """Lee la clave secreta de las cookies. Si el archivo no existe, la genera una sola vez.

    Se guarda en instancia/ (fuera de git) y nunca en el código. Si se borra el archivo, se
    genera otra y todas las sesiones abiertas se cierran (no se pierde ningún dato).
    """
    ruta = Path(ruta)
    try:
        clave = ruta.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        clave = secrets.token_hex(32)
        try:
            # O_EXCL: si otro proceso la acaba de crear, no se sobrescribe. 0o600: solo el dueño.
            descriptor = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return cargar_clave_secreta(ruta)
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            archivo.write(clave + "\n")
        return clave
    if len(clave) < 32:
        raise RuntimeError(f"La clave secreta de {ruta} está vacía o es muy corta. "
                           "Borra el archivo para que se genere una nueva.")
    return clave


# --- Conexión por petición --------------------------------------------------------------------

def obtener_conexion():
    """Conexión de esta petición (se abre la primera vez que se pide)."""
    if "conexion" not in g:
        g.conexion = db.conectar(current_app.config["RUTA_DB"])
    return g.conexion


def cerrar_conexion(_error=None):
    conexion = g.pop("conexion", None)
    if conexion is not None:
        conexion.close()


# --- Utilidades de presentación (filtros de Jinja) -----------------------------------------------

def sin_dato(valor):
    """Vacío, None, S/D, N/A, NA, -, -- → "Sin dato"."""
    texto = "" if valor is None else str(valor).strip()
    if not texto or db.normalizar_texto(texto) in VALORES_SIN_DATO:
        return "Sin dato"
    return texto


def fecha_larga(valor, vacio="Sin registro"):
    """"2025-01-15" → "15 de enero de 2025".
    "2026-10-29T16:45:00-06:00" → "29 de octubre de 2026, 16:45" (hora de Ciudad de México).
    Vacío → `vacio`. Texto que no es fecha → se muestra tal cual."""
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        return vacio
    try:
        if "T" in texto:
            momento = datetime.fromisoformat(texto)
            if momento.tzinfo is not None:
                momento = momento.astimezone(config.ZONA_HORARIA)
            return f"{_dia_mes_anio(momento.date())}, {momento:%H:%M}"
        return _dia_mes_anio(date.fromisoformat(texto))
    except ValueError:
        return texto


def _dia_mes_anio(dia):
    return f"{dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def clase_estatus(estatus):
    """Clase CSS del color del estatus: verde, ambar, rojo o gris."""
    return CLASES_ESTATUS.get(db.normalizar_texto(estatus), "gris")


def es_tmp(id_interno):
    """True si el ID es temporal (empieza con TMP-)."""
    return str(id_interno or "").upper().startswith(config.PREFIJO_TMP.upper())


def es_baja(estatus):
    """True si el estatus es uno de config.ESTATUS_EXCLUIDOS (Baja)."""
    return db.normalizar_texto(estatus) in ESTATUS_BAJA


def opciones_estatus(conexion):
    """Estatus para el filtro: los de config.ESTATUS en su orden y, después, cualquier otro
    que exista en la base (importar_excel.py guarda tal cual un estatus fuera del catálogo)."""
    opciones = list(config.ESTATUS)
    conocidos = {db.normalizar_texto(e) for e in opciones}
    for valor in db.valores_distintos(conexion, "estatus"):
        if db.normalizar_texto(valor) not in conocidos:
            opciones.append(valor)
            conocidos.add(db.normalizar_texto(valor))
    return opciones


# --- Rutas ----------------------------------------------------------------------------------

@requiere_sesion
def buscar():
    """GET / — búsqueda por texto + filtros de área y estatus. Oculta Baja salvo que se pida."""
    texto = request.args.get("q", "")[:LARGO_MAX_BUSQUEDA]
    area = request.args.get("area", "")
    estatus = request.args.get("estatus", "")
    incluir_baja = request.args.get("baja") == "1"

    conexion = obtener_conexion()
    equipos = db.buscar_equipos(conexion, texto, area, estatus, incluir_baja)
    return render_template(
        "buscar.html",
        equipos=equipos,
        texto=texto,
        largo_max_busqueda=LARGO_MAX_BUSQUEDA,
        area=area,
        estatus=estatus,
        incluir_baja=incluir_baja,
        areas=db.valores_distintos(conexion, "area"),
        lista_estatus=opciones_estatus(conexion),
    )


def ficha(codigo):
    """GET /e/<codigo> — ficha pública del equipo (lo que abre el QR)."""
    conexion = obtener_conexion()
    equipo = db.obtener_equipo_por_codigo(conexion, codigo)
    if equipo is None:
        abort(404)

    padre = None
    if equipo["padre_num"] is not None:
        padre = db.obtener_equipo_por_num(conexion, equipo["padre_num"])

    return render_template(
        "ficha.html",
        equipo=equipo,
        padre=padre,
        componentes=db.listar_componentes(conexion, equipo["num"]),
        mantenimientos=db.listar_mantenimientos(conexion, equipo["num"]),
        ultimo_preventivo=db.ultimo_preventivo(conexion, equipo["num"]),
    )


def pagina_no_encontrada(_error):
    return render_template(
        "error.html", titulo="No encontrado",
        mensaje="No existe esa página o ese equipo. Revisa que el código del QR esté completo.",
    ), 404


def error_interno(_error):
    return render_template(
        "error.html", titulo="Ocurrió un error",
        mensaje="Algo falló al mostrar esta página. Intenta de nuevo en unos minutos.",
    ), 500


def agregar_cabeceras(respuesta):
    """Cabeceras de seguridad del navegador en todas las respuestas."""
    respuesta.headers.setdefault("Content-Security-Policy", POLITICA_CONTENIDO)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "same-origin")
    return respuesta


def variables_plantillas():
    """Variables disponibles en todas las plantillas."""
    return {
        "hay_sesion": hay_sesion(),
        "sesion_provisional": bool(current_app.config["SESION_PROVISIONAL"]),
        "CUENTA_FIJA": config.CUENTA_FIJA,
        "UBICACION_FIJA": config.UBICACION_FIJA,
    }


# --- Creación de la app -----------------------------------------------------------------------

def crear_app(ajustes=None):
    """Crea y configura la app. `ajustes` sirve para las pruebas (otra base de datos, etc.)."""
    app = Flask(__name__)
    app.config.update(
        RUTA_DB=None,                                  # None = config.RUTA_DB (lo decide db.py)
        RUTA_CLAVE_SECRETA=config.RUTA_CLAVE_SECRETA,
        ES_PRODUCCION=config.ES_PRODUCCION,
        SESION_PROVISIONAL=True,                       # el chat 4 lo quita junto con el bloque provisional
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,                # 1 MB por petición (para los formularios del chat 4)
    )
    app.config.update(ajustes or {})
    # Cookie "Secure" solo en producción: en la laptop no hay HTTPS y no se podría entrar.
    # (No sirve setdefault: Flask ya trae SESSION_COOKIE_SECURE=False de fábrica.)
    app.config["SESSION_COOKIE_SECURE"] = bool(app.config["ES_PRODUCCION"])

    if app.config["ES_PRODUCCION"] and app.config["SESION_PROVISIONAL"]:
        raise RuntimeError("La app todavía no tiene inicio de sesión (auth.py, chat 4): "
                           "no se puede publicar porque la búsqueda quedaría abierta a todos.")

    app.secret_key = cargar_clave_secreta(app.config["RUTA_CLAVE_SECRETA"])
    csrf.init_app(app)

    with closing(db.conectar(app.config["RUTA_DB"])) as conexion:
        db.crear_tablas(conexion)
    app.teardown_appcontext(cerrar_conexion)

    app.add_template_filter(sin_dato)
    app.add_template_filter(fecha_larga)
    app.add_template_filter(clase_estatus)
    app.add_template_test(es_tmp, "tmp")
    app.add_template_test(es_baja, "baja")
    app.context_processor(variables_plantillas)
    app.after_request(agregar_cabeceras)

    app.add_url_rule("/", "buscar", buscar)
    app.add_url_rule(f"{config.RUTA_FICHA}<codigo>", "ficha", ficha)
    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(500, error_interno)
    return app


app = crear_app()