"""
app.py — Aplicación web Flask del inventario (versión 2).

Crea la app, abre una conexión a la base de datos por petición y registra las rutas.
Toda la lógica de datos vive en db.py y la de sesión en auth.py; aquí se leen los formularios
y se muestran las pantallas.

Arranque:
    Laptop:          flask --app app run        (desde la carpeta inventario/)
    PythonAnywhere:  en su archivo WSGI, ANTES del import:
                         os.environ["INVENTARIO_PRODUCCION"] = "1"
                         from app import app as application

Al importarse, este archivo:
    - crea instancia/clave_secreta.txt si no existe (la clave de las cookies de sesión);
    - crea las tablas de la base de datos si no existen (no borra ni cambia datos).

Partes: chat 3 (búsqueda y ficha), chat 4 (sesión, edición, alta de equipos y componentes,
registro de mantenimientos y cambio de contraseña), chat 5 (QR y etiquetas) y chat 6 (respaldo).
"""

import hashlib
import io
import math
import os
import re
import secrets
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (Flask, abort, current_app, flash, g, redirect, render_template, request,
                   send_file, session, url_for)
from flask_wtf.csrf import CSRFProtect

import auth
import config
import db
import etiquetas
import qr
import respaldo
from auth import requiere_sesion

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

# Formulario de equipo (alta y edición). padre_num se lee aparte (ver leer_formulario_equipo).
CAMPOS_FORMULARIO = ("id_interno", "tipo", "marca", "modelo", "serie", "area", "estatus", "notas")
CAMPOS_MANTENIMIENTO = ("fecha", "tipo", "descripcion", "realizado_por")

NOMBRES_CAMPOS = {
    "id_interno": "ID interno", "tipo": "Tipo", "marca": "Marca", "modelo": "Modelo",
    "serie": "No. de serie", "area": "Área", "estatus": "Estatus", "notas": "Notas",
    "padre_num": "Componente de", "fecha": "Fecha", "descripcion": "Descripción",
    "realizado_por": "Realizado por",
}
LARGO_MAX_CAMPO = 200        # caracteres de un campo de una línea
LARGOS_MAXIMOS = {"notas": 2000, "descripcion": 1000}

# Política de seguridad del navegador: solo se cargan archivos de este mismo sitio.
# Consecuencia para las plantillas: nada de <script> ni style="..." escritos dentro del HTML.
POLITICA_CONTENIDO = ("default-src 'self'; img-src 'self' data:; object-src 'none'; "
                      "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")

csrf = CSRFProtect()


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


# --- Conexión y sesión por petición -------------------------------------------------------------

def obtener_conexion():
    """Conexión de esta petición (se abre la primera vez que se pide)."""
    if "conexion" not in g:
        g.conexion = db.conectar(current_app.config["RUTA_DB"])
    return g.conexion


def cerrar_conexion(_error=None):
    conexion = g.pop("conexion", None)
    if conexion is not None:
        conexion.close()


def _equipo_o_404(num):
    equipo = db.obtener_equipo_por_num(obtener_conexion(), num)
    if equipo is None:
        abort(404)
    return equipo


def cargar_sesion():
    """Antes de cada petición: deja en g.usuario al usuario con sesión (o None)."""
    if request.endpoint == "static":
        g.usuario = None             # los archivos estáticos no necesitan abrir la base
        return
    g.usuario = auth.cargar_usuario(obtener_conexion)


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


def _texto(valor):
    """Valor de la base como texto de formulario (None → "")."""
    return "" if valor is None else str(valor)


def version_equipo(equipo):
    """Huella del contenido de un equipo para el formulario de edición. Si cambia entre que se
    abre el formulario y se guarda, otra persona lo modificó. (No se usa actualizado_en porque
    solo tiene segundos: dos guardados en el mismo segundo tendrían la misma hora.)"""
    contenido = "\x1f".join(_texto(equipo[campo]) for campo in db.CAMPOS_EDITABLES)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]


def _nombre_corto(equipo):
    """"Monitor Mindray PM-7000" (como la macro nombre_equipo, para mensajes)."""
    partes = [equipo["tipo"] or "Sin tipo", equipo["marca"], equipo["modelo"]]
    return " ".join(p for p in partes if p)


# --- Formularios ----------------------------------------------------------------------------

def leer_formulario(campos):
    """Valores del formulario sin espacios en los extremos y con saltos de línea \\n
    (el navegador manda \\r\\n en los cuadros de texto grandes)."""
    return {campo: request.form.get(campo, "").replace("\r\n", "\n").strip() for campo in campos}


def revisar_largos(valores):
    for campo, valor in valores.items():
        maximo = LARGOS_MAXIMOS.get(campo, LARGO_MAX_CAMPO)
        if len(valor) > maximo:
            raise db.ErrorDatos(f"{NOMBRES_CAMPOS[campo]}: máximo {maximo} caracteres.")


def leer_formulario_equipo():
    """Valores del formulario de alta o edición. padre_num solo se incluye si el formulario
    lo trae (no lo trae cuando el equipo tiene componentes y no puede tener padre)."""
    campos = CAMPOS_FORMULARIO + (("padre_num",) if "padre_num" in request.form else ())
    return leer_formulario(campos)


def revisar_equipo(valores, estatus_actual=None):
    """Validaciones del formulario de equipo que db.py no hace. Lanza db.ErrorDatos.

    Deja el estatus con la forma exacta de config.ESTATUS ("Baja", no "baja") para que el
    filtro de la búsqueda no muestre dos opciones; acepta además el estatus actual del equipo
    aunque esté fuera del catálogo (para no obligar a cambiarlo al editar otra cosa).
    """
    revisar_largos(valores)
    if not valores["tipo"]:
        raise db.ErrorDatos("El tipo de equipo es obligatorio.")
    estatus = valores["estatus"]
    if estatus:
        permitidos = list(config.ESTATUS) + ([estatus_actual] if estatus_actual else [])
        for opcion in permitidos:
            if db.normalizar_texto(opcion) == db.normalizar_texto(estatus):
                valores["estatus"] = opcion
                break
        else:
            raise db.ErrorDatos("Elige un estatus de la lista.")


def candidatos_padre(conexion, num=None, padre_actual=None):
    """Equipos que se pueden elegir como padre: los que no son componentes, no están en Baja
    y no son el mismo equipo. Siempre incluye al padre actual (aunque esté en Baja)."""
    candidatos = [e for e in db.buscar_equipos(conexion)
                  if e["padre_num"] is None and e["num"] != num]
    if padre_actual is not None and all(e["num"] != padre_actual for e in candidatos):
        padre = db.obtener_equipo_por_num(conexion, padre_actual)
        if padre is not None:
            candidatos.append(padre)
    return sorted(candidatos, key=lambda e: (db.normalizar_texto(_nombre_corto(e)), e["num"]))


def pagina_formulario(conexion, valores, equipo=None, error=None, diferencias=None,
                      estado=200):
    """Pantalla de alta (equipo=None) o edición de un equipo."""
    num = equipo["num"] if equipo else None
    componentes = db.listar_componentes(conexion, num) if equipo else []
    padre_actual = equipo["padre_num"] if equipo else None
    if valores.get("padre_num", "").isdigit():
        padre_actual = int(valores["padre_num"])

    lista_estatus = list(config.ESTATUS)
    if equipo and equipo["estatus"] and equipo["estatus"] not in lista_estatus:
        lista_estatus.append(equipo["estatus"])

    return render_template(
        "editar.html",
        es_nuevo=equipo is None,
        equipo=equipo,
        valores=valores,
        error=error,
        diferencias=diferencias or {},
        version=version_equipo(equipo) if equipo else None,
        num_componentes=len(componentes),
        candidatos=[] if componentes else candidatos_padre(conexion, num, padre_actual),
        lista_estatus=lista_estatus,
        tipos=db.valores_distintos(conexion, "tipo"),
        marcas=db.valores_distintos(conexion, "marca"),
        areas=db.valores_distintos(conexion, "area"),
        largo_max_campo=LARGO_MAX_CAMPO,
        largos=LARGOS_MAXIMOS,
    ), estado


# --- Rutas: búsqueda y ficha ------------------------------------------------------------------

def filtros_busqueda():
    """Texto y filtros de la búsqueda (?q=, ?area=, ?estatus=). Los usan la búsqueda y las
    etiquetas de varios equipos."""
    return (request.args.get("q", "")[:LARGO_MAX_BUSQUEDA], request.args.get("area", ""),
            request.args.get("estatus", ""))


@requiere_sesion
def buscar():
    """GET / — búsqueda por texto + filtros de área y estatus. Oculta Baja salvo que se pida."""
    texto, area, estatus = filtros_busqueda()
    incluir_baja = request.args.get("baja") == "1"

    # Se recuerda en la sesión para el enlace "Volver a la búsqueda" (ver variables_plantillas).
    filtros = {"q": texto, "area": area, "estatus": estatus, "baja": "1" if incluir_baja else ""}
    session["ultima_busqueda"] = {clave: valor[:LARGO_MAX_BUSQUEDA]
                                  for clave, valor in filtros.items() if valor}

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


def pagina_ficha(conexion, equipo, form_mto=None, error_mantenimiento=None, estado=200):
    """Ficha del equipo. `form_mto` y `error_mantenimiento` son el formulario de mantenimiento
    (solo se muestra con sesión) cuando hay que volver a mostrarlo con un error."""
    padre = None
    if equipo["padre_num"] is not None:
        padre = db.obtener_equipo_por_num(conexion, equipo["padre_num"])
    hoy = db.hoy().isoformat()

    return render_template(
        "ficha.html",
        equipo=equipo,
        padre=padre,
        componentes=db.listar_componentes(conexion, equipo["num"]),
        mantenimientos=db.listar_mantenimientos(conexion, equipo["num"]),
        ultimo_preventivo=db.ultimo_preventivo(conexion, equipo["num"]),
        form_mto=form_mto or {"fecha": hoy, "tipo": config.TIPOS_MANTENIMIENTO[0],
                    "descripcion": "", "realizado_por": ""},
        error_mantenimiento=error_mantenimiento,
        hoy=hoy,
        tipos_mantenimiento=config.TIPOS_MANTENIMIENTO,
        largo_max_campo=LARGO_MAX_CAMPO,
        largos=LARGOS_MAXIMOS,
    ), estado


def ficha(codigo):
    """GET /e/<codigo> — ficha pública del equipo (lo que abre el QR)."""
    # Antes de consultar la base: 8 caracteres del alfabeto del QR (sin distinguir mayúsculas).
    codigo = codigo.lower()
    if len(codigo) != config.LARGO_CODIGO or any(c not in config.ALFABETO_CODIGO for c in codigo):
        abort(404)
    conexion = obtener_conexion()
    equipo = db.obtener_equipo_por_codigo(conexion, codigo)
    if equipo is None:
        abort(404)
    return pagina_ficha(conexion, equipo)


# --- Rutas: sesión ----------------------------------------------------------------------------

def entrar():
    """GET/POST /entrar — inicio de sesión."""
    siguiente = request.values.get("siguiente", "")
    if not auth.destino_seguro(siguiente):
        siguiente = ""
    if auth.hay_sesion():
        return redirect(siguiente or url_for("buscar"))

    usuario = ""
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        fila, error = auth.intentar_entrar(obtener_conexion(), usuario,
                                           request.form.get("contrasena", ""), auth.ip_cliente())
        if fila is not None:
            auth.iniciar_sesion(fila)
            return redirect(siguiente or url_for("buscar"))
    return render_template("entrar.html", usuario=usuario.strip()[:auth.LARGO_MAX_USUARIO],
                           siguiente=siguiente, error=error)


def salir():
    """POST /salir — cierra la sesión (POST con token CSRF: un enlace no puede cerrarla)."""
    auth.cerrar_sesion()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("entrar"))


@requiere_sesion
def cambiar_contrasena():
    """GET/POST /contrasena — el usuario con sesión cambia su propia contraseña."""
    usuario = auth.usuario_actual()
    error = None
    if request.method == "POST":
        conexion = obtener_conexion()
        actual = request.form.get("actual", "")
        nueva = request.form.get("nueva", "")
        error = auth.verificar_contrasena_actual(conexion, usuario, actual, auth.ip_cliente())
        if error is None:
            try:
                auth.validar_contrasena_nueva(nueva, request.form.get("confirmacion", ""),
                                              usuario["usuario"])
                if nueva == actual:
                    raise db.ErrorDatos("La contraseña nueva debe ser distinta de la actual.")
                db.cambiar_contrasena(conexion, usuario["usuario"], auth.generar_hash(nueva))
            except db.ErrorDatos as problema:
                error = str(problema)
            else:
                # Sesión nueva con la huella nueva: esta sigue abierta, las demás se cierran.
                auth.iniciar_sesion(db.obtener_usuario(conexion, usuario["usuario"]))
                flash("Contraseña cambiada. Las sesiones abiertas en otros dispositivos se "
                      "cerraron.", "exito")
                return redirect(url_for("cambiar_contrasena"))
    return render_template("contrasena.html", error=error,
                           largo_min=auth.LARGO_MIN_CONTRASENA,
                           largo_max=auth.LARGO_MAX_CONTRASENA), 400 if error else 200


# --- Rutas: alta y edición de equipos ------------------------------------------------------------

@requiere_sesion
def nuevo_equipo():
    """GET/POST /equipo/nuevo — alta de equipo, o de componente con ?padre=<num>."""
    conexion = obtener_conexion()
    if request.method == "GET":
        valores = {campo: "" for campo in CAMPOS_FORMULARIO}
        valores.update(estatus=config.ESTATUS[0], padre_num="")
        padre_texto = request.args.get("padre", "")
        padre = db.obtener_equipo_por_num(conexion, int(padre_texto)) if padre_texto.isdigit() else None
        if padre is not None and padre["padre_num"] is None:
            valores["padre_num"] = str(padre["num"])
            valores["area"] = _texto(padre["area"])     # un componente suele estar donde su padre
        return pagina_formulario(conexion, valores)

    valores = leer_formulario_equipo()
    try:
        revisar_equipo(valores)
        num = db.insertar_equipo(conexion, valores, auth.usuario_actual()["usuario"])
    except db.ErrorDatos as error:
        return pagina_formulario(conexion, valores, error=str(error), estado=400)
    equipo = db.obtener_equipo_por_num(conexion, num)
    flash("Equipo dado de alta.", "exito")
    return redirect(url_for("ficha", codigo=equipo["codigo"]))


@requiere_sesion
def editar_equipo(num):
    """GET/POST /equipo/<num>/editar — editar los datos de un equipo (incluye ligarlo a un
    padre o desligarlo)."""
    conexion = obtener_conexion()
    equipo = _equipo_o_404(num)
    actuales = {campo: _texto(equipo[campo]) for campo in CAMPOS_FORMULARIO + ("padre_num",)}
    if request.method == "GET":
        return pagina_formulario(conexion, actuales, equipo)

    valores = leer_formulario_equipo()

    # Si alguien guardó este equipo mientras se editaba, no se sobrescribe sin avisar:
    # se muestran los datos capturados y, junto a cada campo distinto, lo que hay guardado.
    # (Si lo capturado ya es igual a lo guardado, no hay nada que avisar.)
    if request.form.get("version") != version_equipo(equipo):
        diferencias = {}
        for campo, valor in valores.items():
            if valor != actuales[campo]:
                guardado = actuales[campo]
                if campo == "padre_num" and guardado:
                    guardado = _nombre_corto(db.obtener_equipo_por_num(conexion, int(guardado)))
                diferencias[campo] = guardado or ("Ninguno" if campo == "padre_num" else "")
        if diferencias:
            error = ("Otra persona guardó cambios en este equipo mientras lo editabas. Revisa los "
                     "campos marcados y vuelve a guardar si tus datos siguen siendo correctos.")
            return pagina_formulario(conexion, valores, equipo, error=error,
                                     diferencias=diferencias, estado=409)

    try:
        revisar_equipo(valores, estatus_actual=equipo["estatus"])
        cambios = {campo: valor for campo, valor in valores.items() if valor != actuales[campo]}
        if not cambios:
            flash("No había cambios que guardar.", "info")
            return redirect(url_for("ficha", codigo=equipo["codigo"]))
        db.actualizar_equipo(conexion, num, cambios, auth.usuario_actual()["usuario"])
    except db.ErrorDatos as error:
        return pagina_formulario(conexion, valores, equipo, error=str(error), estado=400)
    flash("Cambios guardados.", "exito")
    return redirect(url_for("ficha", codigo=equipo["codigo"]))


@requiere_sesion
def registrar_mantenimiento(num):
    """POST /equipo/<num>/mantenimiento — agrega un mantenimiento al historial."""
    conexion = obtener_conexion()
    equipo = _equipo_o_404(num)
    valores = leer_formulario(CAMPOS_MANTENIMIENTO)
    try:
        revisar_largos(valores)
        db.registrar_mantenimiento(conexion, num, valores["fecha"], valores["tipo"],
                                   valores["descripcion"], valores["realizado_por"],
                                   auth.usuario_actual()["usuario"])
    except db.ErrorDatos as error:
        return pagina_ficha(conexion, equipo, form_mto=valores, error_mantenimiento=str(error),
                            estado=400)
    flash("Mantenimiento registrado.", "exito")
    return redirect(url_for("ficha", codigo=equipo["codigo"], _anchor="historial"))


# --- Rutas: QR y etiquetas (chat 5) --------------------------------------------------------------

def _sin_etiqueta(motivo):
    """Página de aviso cuando se pide el QR o el PDF de un equipo que no lleva etiqueta."""
    return render_template("error.html", titulo="No se puede generar la etiqueta",
                           mensaje=motivo), 409


def _nombre_archivo(texto):
    """"CRM GDL 06 01 10" → "CRM_GDL_06_01_10" (solo letras, números y guiones)."""
    return re.sub(r"[^A-Za-z0-9-]+", "_", texto).strip("_") or "equipo"


def _archivo(datos, tipo, nombre, adjunto=False):
    """Respuesta con un archivo generado en memoria. Por defecto se abre en el navegador (en el
    iPhone, desde ahí se imprime o se comparte); con adjunto=True se descarga (respaldos).
    No se guarda en caché: todos estos archivos piden sesión."""
    respuesta = send_file(io.BytesIO(datos), mimetype=tipo, download_name=nombre,
                          as_attachment=adjunto)
    respuesta.headers["Cache-Control"] = "private, no-store"
    return respuesta


@requiere_sesion
def etiqueta(num):
    """GET /equipo/<num>/etiqueta — vista previa del QR de un equipo y botones para descargar
    su etiqueta. Si el equipo no lleva etiqueta (Baja o sin ID), explica por qué."""
    equipo = _equipo_o_404(num)
    return render_template(
        "etiqueta.html",
        equipo=equipo,
        motivo=etiquetas.motivo_sin_etiqueta(equipo),
        enlace=qr.enlace_equipo(equipo["codigo"]),
        tam_etiqueta=config.TAM_ETIQUETA_CM,
    )


@requiere_sesion
def qr_png(num):
    """GET /equipo/<num>/qr.png — imagen del QR (con su zona blanca) para la pantalla."""
    equipo = _equipo_o_404(num)
    motivo = etiquetas.motivo_sin_etiqueta(equipo)
    if motivo:
        return _sin_etiqueta(motivo)
    datos = qr.png(qr.enlace_equipo(equipo["codigo"]))
    return _archivo(datos, "image/png", f"qr_{_nombre_archivo(equipo['id_interno'])}.png")


@requiere_sesion
def etiqueta_pdf(num):
    """GET /equipo/<num>/etiqueta.pdf — PDF de una etiqueta. Por defecto, una página del tamaño
    exacto de la etiqueta (impresora de etiquetas); con ?hoja=carta, en una hoja carta con
    líneas de corte."""
    equipo = _equipo_o_404(num)
    motivo = etiquetas.motivo_sin_etiqueta(equipo)
    if motivo:
        return _sin_etiqueta(motivo)
    nombre = f"etiqueta_{_nombre_archivo(equipo['id_interno'])}"
    if request.args.get("hoja") == "carta":
        return _archivo(etiquetas.pdf_hoja([equipo]), "application/pdf", f"{nombre}_carta.pdf")
    return _archivo(etiquetas.pdf_una(equipo), "application/pdf", f"{nombre}.pdf")


def _equipos_para_etiquetas():
    """Equipos de la búsqueda actual separados en (imprimibles en orden de impresión, excluidos).
    Los equipos en Baja nunca se imprimen: la búsqueda ya los oculta y, si se filtró por
    estatus "Baja", quedan en `excluidos` con su motivo."""
    equipos = db.buscar_equipos(obtener_conexion(), *filtros_busqueda())
    imprimibles, excluidos = etiquetas.separar(equipos)
    return etiquetas.ordenar_para_imprimir(imprimibles), excluidos


@requiere_sesion
def lote_etiquetas():
    """GET /etiquetas — resumen antes de imprimir las etiquetas de una búsqueda: cuántas salen,
    en cuántas hojas y qué equipos se quedan fuera (y por qué)."""
    texto, area, estatus = filtros_busqueda()
    imprimibles, excluidos = _equipos_para_etiquetas()
    por_hoja = etiquetas.etiquetas_por_hoja()
    return render_template(
        "etiquetas.html",
        texto=texto, area=area, estatus=estatus,
        imprimibles=imprimibles,
        excluidos=excluidos,
        hojas=math.ceil(len(imprimibles) / por_hoja),
        por_hoja=por_hoja,
        tam_etiqueta=config.TAM_ETIQUETA_CM,
    )


@requiere_sesion
def lote_etiquetas_pdf():
    """GET /etiquetas.pdf — PDF en hojas carta con las etiquetas de la búsqueda (mismos filtros
    que /etiquetas), para la impresión inicial."""
    imprimibles, _ = _equipos_para_etiquetas()
    if not imprimibles:
        return _sin_etiqueta("Ningún equipo de esta búsqueda puede llevar etiqueta.")
    nombre = f"etiquetas_{db.hoy().isoformat()}.pdf"
    return _archivo(etiquetas.pdf_hoja(imprimibles), "application/pdf", nombre)


# --- Rutas: respaldo (chat 6) -------------------------------------------------------------------

TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@requiere_sesion
def pagina_respaldo():
    """GET /respaldo — conteos, aviso sobre el .db y los dos botones de descarga."""
    return render_template("respaldo.html", resumen=respaldo.resumen(obtener_conexion()))


@requiere_sesion
def respaldo_excel():
    """GET /respaldo.xlsx — Excel para consultar (sin usuarios ni intentos de entrada)."""
    datos = respaldo.excel(obtener_conexion(), auth.usuario_actual()["usuario"])
    return _archivo(datos, TIPO_EXCEL, respaldo.nombre_archivo("xlsx"), adjunto=True)


@requiere_sesion
def respaldo_db():
    """GET /respaldo.db — copia de la base de datos para restaurar (incluye los hashes de las
    contraseñas)."""
    datos = respaldo.copia_db(obtener_conexion())
    return _archivo(datos, "application/octet-stream", respaldo.nombre_archivo("db"),
                    adjunto=True)


# --- Errores y cabeceras ----------------------------------------------------------------------

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


MENSAJES_ERROR = {
    400: ("No se pudo completar",
          "La página caducó o el formulario llegó incompleto. Regresa, recarga la página e "
          "intenta de nuevo."),
    405: ("Acción no permitida", "Esa acción no se puede hacer desde esta dirección."),
    413: ("Formulario demasiado grande", "Lo que enviaste es demasiado grande. Acórtalo e "
          "intenta de nuevo."),
}


def error_formulario(error):
    """400 (incluye el token CSRF vencido o faltante), 405 y 413, sin detalles técnicos."""
    titulo, mensaje = MENSAJES_ERROR[error.code]
    return render_template("error.html", titulo=titulo, mensaje=mensaje), error.code


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
        "hay_sesion": auth.hay_sesion(),
        "usuario_actual": auth.usuario_actual(),
        "volver_busqueda": url_for("buscar", **session.get("ultima_busqueda", {})),
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
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=config.HORAS_SESION),
        # El token CSRF dura lo que la sesión (no 1 hora): un formulario que se dejó abierto
        # un rato no pierde lo capturado. Sigue ligado a la cookie de sesión.
        WTF_CSRF_TIME_LIMIT=None,
        MAX_CONTENT_LENGTH=1024 * 1024,                # 1 MB por petición
    )
    app.config.update(ajustes or {})
    # Cookie "Secure" solo en producción: en la laptop no hay HTTPS y no se podría entrar.
    # (No sirve setdefault: Flask ya trae SESSION_COOKIE_SECURE=False de fábrica.)
    app.config["SESSION_COOKIE_SECURE"] = bool(app.config["ES_PRODUCCION"])

    app.secret_key = cargar_clave_secreta(app.config["RUTA_CLAVE_SECRETA"])
    csrf.init_app(app)

    with closing(db.conectar(app.config["RUTA_DB"])) as conexion:
        db.crear_tablas(conexion)
    app.before_request(cargar_sesion)
    app.teardown_appcontext(cerrar_conexion)

    app.add_template_filter(sin_dato)
    app.add_template_filter(fecha_larga)
    app.add_template_filter(clase_estatus)
    app.add_template_test(es_tmp, "tmp")
    app.add_template_test(db.es_baja, "baja")
    app.context_processor(variables_plantillas)
    app.after_request(agregar_cabeceras)

    app.add_url_rule("/", "buscar", buscar)
    app.add_url_rule(f"{config.RUTA_FICHA}<codigo>", "ficha", ficha)
    app.add_url_rule("/entrar", "entrar", entrar, methods=["GET", "POST"])
    app.add_url_rule("/salir", "salir", salir, methods=["POST"])
    app.add_url_rule("/contrasena", "cambiar_contrasena", cambiar_contrasena,
                     methods=["GET", "POST"])
    app.add_url_rule("/equipo/nuevo", "nuevo_equipo", nuevo_equipo, methods=["GET", "POST"])
    app.add_url_rule("/equipo/<int:num>/editar", "editar_equipo", editar_equipo,
                     methods=["GET", "POST"])
    app.add_url_rule("/equipo/<int:num>/mantenimiento", "registrar_mantenimiento",
                     registrar_mantenimiento, methods=["POST"])
    app.add_url_rule("/equipo/<int:num>/etiqueta", "etiqueta", etiqueta)
    app.add_url_rule("/equipo/<int:num>/qr.png", "qr_png", qr_png)
    app.add_url_rule("/equipo/<int:num>/etiqueta.pdf", "etiqueta_pdf", etiqueta_pdf)
    app.add_url_rule("/etiquetas", "etiquetas", lote_etiquetas)
    app.add_url_rule("/etiquetas.pdf", "etiquetas_pdf", lote_etiquetas_pdf)
    app.add_url_rule("/respaldo", "respaldo", pagina_respaldo)
    app.add_url_rule("/respaldo.xlsx", "respaldo_excel", respaldo_excel)
    app.add_url_rule("/respaldo.db", "respaldo_db", respaldo_db)

    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(500, error_interno)
    for codigo in MENSAJES_ERROR:
        app.register_error_handler(codigo, error_formulario)
    return app


app = crear_app()