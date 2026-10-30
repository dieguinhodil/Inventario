"""
db.py — Base de datos SQLite de la app de inventario (versión 2).

Contiene la conexión, la creación de tablas y todas las consultas. No depende de Flask:
lo usan app.py, importar_excel.py y crear_usuario.py.

Uso típico:
    conexion = db.conectar()
    db.crear_tablas(conexion)
    equipo = db.obtener_equipo_por_codigo(conexion, "k7q2xpm4")
    conexion.close()

Transacciones:
    - Cada función que escribe confirma (commit) sus propios cambios.
    - Para agrupar muchas escrituras en una sola transacción (por ejemplo, la importación
      del Excel), se usa `with db.transaccion(conexion):`. Dentro de ese bloque las funciones
      no confirman por su cuenta; se confirma todo al final o se deshace todo si hay un error.

Errores:
    - Los datos inválidos (padre inexistente, ID repetido, fecha mal escrita, etc.) lanzan
      `ErrorDatos` con un mensaje en español listo para mostrarse al usuario.

Fechas y horas:
    - `creado_en`, `actualizado_en` y `fecha_hora` se guardan en hora de Ciudad de México
      (config.ZONA_HORARIA) con su desfase, por ejemplo "2026-10-29T16:45:00-06:00".
      PythonAnywhere trabaja en UTC, así que no se usa la hora del servidor tal cual.
    - Se comparan como texto (más viejo < más nuevo). Funciona porque Ciudad de México ya no
      cambia de horario: el desfase siempre es -06:00.
"""

import math
import re
import secrets
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import config

# Campos de `equipos` que se pueden escribir al dar de alta o al editar.
# `num`, `codigo`, `creado_en`, `actualizado_en` y `actualizado_por` los pone este módulo.
CAMPOS_EDITABLES = ("id_interno", "tipo", "marca", "modelo", "serie", "area", "estatus",
                    "padre_num", "notas")
# Solo al dar de alta (los usa importar_excel.py); después ya no se editan.
CAMPOS_SOLO_ALTA = ("id_original", "fila_excel")

# Campos donde busca el cuadro de texto de la búsqueda.
CAMPOS_BUSQUEDA = ("serie", "id_interno", "tipo", "marca", "modelo")

# Campos de los que se pueden pedir valores distintos (para listas desplegables).
CAMPOS_CON_VALORES = ("area", "estatus", "tipo", "marca")

DIAS_GUARDAR_INTENTOS = 30   # los intentos de inicio de sesión más viejos se borran

FORMATO_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ErrorDatos(ValueError):
    """Dato inválido. El mensaje se puede mostrar tal cual al usuario."""


# --- Utilidades -----------------------------------------------------------------------------

def ahora():
    """Fecha y hora actual de Ciudad de México en formato ISO, con desfase."""
    return datetime.now(config.ZONA_HORARIA).isoformat(timespec="seconds")


def hoy():
    """Fecha de hoy en Ciudad de México."""
    return datetime.now(config.ZONA_HORARIA).date()


def normalizar_texto(texto):
    """Quita acentos, pasa a minúsculas y junta espacios. None → "".

    Se registra en SQLite como la función `sin_acentos(...)` para que la búsqueda
    encuentre "Electrocardiógrafo" escribiendo "electrocardiografo".
    """
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_marcas = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return " ".join(sin_marcas.casefold().split())


def _limpiar(valor):
    """Quita espacios de los extremos; el texto vacío se guarda como NULL."""
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _limpiar_equipo(datos):
    """_limpiar() a cada campo y `padre_num` a entero (de un formulario llega como texto)."""
    limpios = {campo: _limpiar(valor) for campo, valor in datos.items()}
    if limpios.get("padre_num") is not None:
        try:
            limpios["padre_num"] = int(limpios["padre_num"])
        except (TypeError, ValueError):
            raise ErrorDatos(f"El equipo padre debe ser un número (llegó {limpios['padre_num']!r}).")
    return limpios


def _escapar_like(texto):
    """Escapa los comodines de LIKE para buscar el texto literal."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --- Conexión y transacciones -----------------------------------------------------------------

def conectar(ruta=None):
    """Abre la base de datos (por defecto config.RUTA_DB) y la deja lista para usarse.

    - Las filas se pueden leer por nombre: fila["serie"].
    - Las llaves foráneas quedan activadas (SQLite las trae apagadas).
    - Queda registrada la función SQL sin_acentos().
    """
    if ruta is None:
        config.CARPETA_INSTANCIA.mkdir(exist_ok=True)
        ruta = config.RUTA_DB
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.create_function("sin_acentos", 1, normalizar_texto, deterministic=True)
    return conexion


@contextmanager
def transaccion(conexion):
    """Agrupa varias escrituras: se confirman todas al final o no se guarda ninguna."""
    conexion.execute("BEGIN")
    with conexion:      # commit al final, rollback si hay cualquier error
        yield conexion


@contextmanager
def _escritura(conexion):
    """Confirma al terminar, salvo que ya haya una transacción abierta con transaccion()."""
    if conexion.in_transaction:
        yield
    else:
        with conexion:      # commit si todo sale bien, rollback si hay error
            yield


# --- Creación de tablas ---------------------------------------------------------------------

def crear_tablas(conexion):
    """Crea las tablas e índices si no existen. Se puede llamar las veces que sea."""
    conexion.executescript("""
        CREATE TABLE IF NOT EXISTS equipos (
            num             INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo          TEXT NOT NULL UNIQUE,
            id_interno      TEXT UNIQUE COLLATE NOCASE,
            id_original     TEXT,
            tipo            TEXT,
            marca           TEXT,
            modelo          TEXT,
            serie           TEXT,
            area            TEXT,
            estatus         TEXT,
            padre_num       INTEGER REFERENCES equipos(num),
            notas           TEXT,
            fila_excel      INTEGER,
            creado_en       TEXT NOT NULL,
            actualizado_en  TEXT NOT NULL,
            actualizado_por TEXT,
            CHECK (padre_num IS NULL OR padre_num <> num)
        );

        CREATE TABLE IF NOT EXISTS mantenimientos (
            id             INTEGER PRIMARY KEY,
            equipo_num     INTEGER NOT NULL REFERENCES equipos(num),
            fecha          TEXT NOT NULL,
            tipo           TEXT NOT NULL,
            descripcion    TEXT,
            realizado_por  TEXT,
            registrado_por TEXT,
            creado_en      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id              INTEGER PRIMARY KEY,
            usuario         TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nombre          TEXT NOT NULL,
            hash_contrasena TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS intentos_entrada (
            id         INTEGER PRIMARY KEY,
            usuario    TEXT COLLATE NOCASE,
            ip         TEXT,
            fecha_hora TEXT NOT NULL,
            exitoso    INTEGER NOT NULL CHECK (exitoso IN (0, 1))
        );

        CREATE INDEX IF NOT EXISTS idx_equipos_padre ON equipos(padre_num);
        CREATE INDEX IF NOT EXISTS idx_mant_equipo_fecha ON mantenimientos(equipo_num, fecha);
        CREATE INDEX IF NOT EXISTS idx_intentos_fecha ON intentos_entrada(fecha_hora);
    """)


# --- Equipos: lectura -----------------------------------------------------------------------

def obtener_equipo_por_codigo(conexion, codigo):
    """Equipo del código del QR, o None si no existe (la ruta pública muestra 404)."""
    return conexion.execute(
        "SELECT * FROM equipos WHERE codigo = ?", (codigo.strip().lower(),)
    ).fetchone()


def obtener_equipo_por_num(conexion, num):
    """Equipo por su número interno, o None si no existe."""
    return conexion.execute("SELECT * FROM equipos WHERE num = ?", (num,)).fetchone()


def listar_componentes(conexion, num_padre):
    """Componentes (hijos) de un equipo, en orden de alta."""
    return conexion.execute(
        "SELECT * FROM equipos WHERE padre_num = ? ORDER BY num", (num_padre,)
    ).fetchall()


def buscar_equipos(conexion, texto="", area=None, estatus=None, incluir_baja=False):
    """Busca equipos.

    - texto: cada palabra debe aparecer en alguno de CAMPOS_BUSQUEDA (sin importar
      acentos ni mayúsculas). "monitor mindray" encuentra monitores de esa marca.
    - area, estatus: filtros exactos (vienen de una lista desplegable). Vacío = sin filtro.
    - incluir_baja: si no se filtra por estatus, los equipos en ESTATUS_EXCLUIDOS se ocultan
      salvo que esto sea True. Si se filtra por estatus "Baja", sí se muestran.
    Sin texto ni filtros y con incluir_baja=True devuelve todo el inventario.
    """
    condiciones = []
    parametros = []

    for palabra in normalizar_texto(texto).split():
        patron = f"%{_escapar_like(palabra)}%"
        partes = [f"sin_acentos({campo}) LIKE ? ESCAPE '\\'" for campo in CAMPOS_BUSQUEDA]
        condiciones.append("(" + " OR ".join(partes) + ")")
        parametros.extend([patron] * len(CAMPOS_BUSQUEDA))

    area = _limpiar(area)
    if area:
        condiciones.append("area = ?")
        parametros.append(area)

    estatus = _limpiar(estatus)
    if estatus:
        condiciones.append("sin_acentos(estatus) = ?")
        parametros.append(normalizar_texto(estatus))
    elif not incluir_baja:
        marcas = ", ".join("?" * len(config.ESTATUS_EXCLUIDOS))
        condiciones.append(f"sin_acentos(estatus) NOT IN ({marcas})")
        parametros.extend(normalizar_texto(e) for e in config.ESTATUS_EXCLUIDOS)

    consulta = "SELECT * FROM equipos"
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)
    consulta += " ORDER BY num"
    return conexion.execute(consulta, parametros).fetchall()


def valores_distintos(conexion, campo):
    """Valores distintos (sin vacíos) de un campo, en orden alfabético. Para filtros y listas."""
    if campo not in CAMPOS_CON_VALORES:
        raise ValueError(f"Campo no permitido: {campo}")
    # El nombre del campo sale de la lista fija de arriba, nunca de lo que escribe el usuario.
    filas = conexion.execute(
        f"SELECT DISTINCT {campo} AS valor FROM equipos WHERE {campo} IS NOT NULL"
    ).fetchall()
    return sorted((fila["valor"] for fila in filas), key=normalizar_texto)


# --- Equipos: escritura ---------------------------------------------------------------------

def _generar_codigo(conexion):
    """Código aleatorio del QR que no esté usado todavía."""
    for _ in range(20):
        codigo = "".join(secrets.choice(config.ALFABETO_CODIGO)
                         for _ in range(config.LARGO_CODIGO))
        if not conexion.execute("SELECT 1 FROM equipos WHERE codigo = ?", (codigo,)).fetchone():
            return codigo
    raise RuntimeError("No se pudo generar un código único para el QR.")


def _validar_padre(conexion, padre_num, num=None):
    """Revisa que padre_num pueda ser el padre del equipo `num` (None si es alta)."""
    if num is not None and padre_num == num:
        raise ErrorDatos("Un equipo no puede ser componente de sí mismo.")
    padre = obtener_equipo_por_num(conexion, padre_num)
    if padre is None:
        raise ErrorDatos(f"No existe el equipo padre número {padre_num}.")
    if padre["padre_num"] is not None:
        raise ErrorDatos("El equipo elegido como padre ya es componente de otro equipo "
                         "(solo se permite un nivel).")
    if num is not None and listar_componentes(conexion, num):
        raise ErrorDatos("Este equipo tiene componentes, así que no puede ser componente "
                         "de otro equipo (solo se permite un nivel).")


def _error_por_unicidad(error, datos):
    """Convierte un IntegrityError de SQLite en un mensaje entendible."""
    if "equipos.id_interno" in str(error):
        return ErrorDatos(f"Ya existe un equipo con el ID interno {datos.get('id_interno')}.")
    return error


def insertar_equipo(conexion, datos, usuario):
    """Da de alta un equipo o componente y devuelve su `num`.

    datos: diccionario con cualquiera de CAMPOS_EDITABLES y CAMPOS_SOLO_ALTA.
    El `codigo` del QR se genera aquí y nunca cambia.
    """
    permitidos = CAMPOS_EDITABLES + CAMPOS_SOLO_ALTA
    desconocidos = set(datos) - set(permitidos)
    if desconocidos:
        raise ValueError(f"Campos no permitidos: {sorted(desconocidos)}")
    limpios = _limpiar_equipo(datos)

    with _escritura(conexion):
        if limpios.get("padre_num") is not None:
            _validar_padre(conexion, limpios["padre_num"])
        momento = ahora()
        limpios.update(codigo=_generar_codigo(conexion), creado_en=momento,
                       actualizado_en=momento, actualizado_por=usuario)
        columnas = ", ".join(limpios)
        marcas = ", ".join("?" * len(limpios))
        try:
            cursor = conexion.execute(
                f"INSERT INTO equipos ({columnas}) VALUES ({marcas})", list(limpios.values())
            )
        except sqlite3.IntegrityError as error:
            raise _error_por_unicidad(error, limpios) from error
    return cursor.lastrowid


def actualizar_equipo(conexion, num, cambios, usuario):
    """Edita un equipo. `cambios` solo puede traer CAMPOS_EDITABLES.

    Para desligar un componente de su padre: cambios={"padre_num": None}.
    Los equipos nunca se borran: para darlos de baja se cambia el estatus.
    """
    desconocidos = set(cambios) - set(CAMPOS_EDITABLES)
    if desconocidos:
        raise ValueError(f"Campos no editables: {sorted(desconocidos)}")
    limpios = _limpiar_equipo(cambios)

    with _escritura(conexion):
        if obtener_equipo_por_num(conexion, num) is None:
            raise ErrorDatos(f"No existe el equipo número {num}.")
        if limpios.get("padre_num") is not None:
            _validar_padre(conexion, limpios["padre_num"], num)
        limpios.update(actualizado_en=ahora(), actualizado_por=usuario)
        asignaciones = ", ".join(f"{campo} = ?" for campo in limpios)
        try:
            conexion.execute(f"UPDATE equipos SET {asignaciones} WHERE num = ?",
                             [*limpios.values(), num])
        except sqlite3.IntegrityError as error:
            raise _error_por_unicidad(error, limpios) from error


# --- Mantenimientos -------------------------------------------------------------------------

def registrar_mantenimiento(conexion, equipo_num, fecha, tipo, descripcion, realizado_por,
                            registrado_por):
    """Agrega un mantenimiento al historial y devuelve su `id`.

    fecha: texto "AAAA-MM-DD" (no puede ser posterior a hoy).
    tipo: uno de config.TIPOS_MANTENIMIENTO.
    """
    fecha = (fecha or "").strip()
    if not FORMATO_FECHA.match(fecha):
        raise ErrorDatos("La fecha debe tener el formato AAAA-MM-DD.")
    try:
        dia = date.fromisoformat(fecha)
    except ValueError as error:
        raise ErrorDatos(f"La fecha {fecha} no existe.") from error
    if dia > hoy():
        raise ErrorDatos("La fecha del mantenimiento no puede ser posterior a hoy.")

    tipo = normalizar_texto(tipo)
    if tipo not in config.TIPOS_MANTENIMIENTO:
        raise ErrorDatos(f"Tipo de mantenimiento no válido: debe ser "
                         f"{' o '.join(config.TIPOS_MANTENIMIENTO)}.")

    with _escritura(conexion):
        if obtener_equipo_por_num(conexion, equipo_num) is None:
            raise ErrorDatos(f"No existe el equipo número {equipo_num}.")
        cursor = conexion.execute(
            """INSERT INTO mantenimientos
               (equipo_num, fecha, tipo, descripcion, realizado_por, registrado_por, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (equipo_num, fecha, tipo, _limpiar(descripcion), _limpiar(realizado_por),
             registrado_por, ahora()),
        )
    return cursor.lastrowid


def listar_mantenimientos(conexion, equipo_num=None):
    """Historial de un equipo (del más reciente al más viejo). Sin equipo_num: todos (respaldo)."""
    if equipo_num is None:
        return conexion.execute(
            "SELECT * FROM mantenimientos ORDER BY equipo_num, fecha DESC, id DESC"
        ).fetchall()
    return conexion.execute(
        "SELECT * FROM mantenimientos WHERE equipo_num = ? ORDER BY fecha DESC, id DESC",
        (equipo_num,),
    ).fetchall()


def ultimo_preventivo(conexion, equipo_num):
    """Fecha ("AAAA-MM-DD") del mantenimiento preventivo más reciente, o None."""
    fila = conexion.execute(
        "SELECT MAX(fecha) AS fecha FROM mantenimientos "
        "WHERE equipo_num = ? AND tipo = 'preventivo'",
        (equipo_num,),
    ).fetchone()
    return fila["fecha"]


# --- Usuarios -------------------------------------------------------------------------------

def crear_usuario(conexion, usuario, nombre, hash_contrasena):
    """Da de alta un usuario y devuelve su `id`. El hash lo genera quien llama
    (werkzeug.security.generate_password_hash); aquí nunca llega la contraseña."""
    usuario = _limpiar(usuario)
    nombre = _limpiar(nombre)
    if not usuario or not nombre or not hash_contrasena:
        raise ErrorDatos("Usuario, nombre y contraseña son obligatorios.")
    with _escritura(conexion):
        try:
            cursor = conexion.execute(
                "INSERT INTO usuarios (usuario, nombre, hash_contrasena) VALUES (?, ?, ?)",
                (usuario, nombre, hash_contrasena),
            )
        except sqlite3.IntegrityError as error:
            raise ErrorDatos(f"Ya existe el usuario {usuario}.") from error
    return cursor.lastrowid


def obtener_usuario(conexion, usuario):
    """Usuario por nombre de usuario (sin distinguir mayúsculas), o None."""
    return conexion.execute(
        "SELECT * FROM usuarios WHERE usuario = ?", (_limpiar(usuario),)
    ).fetchone()


# --- Intentos de inicio de sesión -------------------------------------------------------------

def registrar_intento(conexion, usuario, ip, exitoso):
    """Guarda un intento de inicio de sesión y borra los de más de DIAS_GUARDAR_INTENTOS días."""
    momento = datetime.now(config.ZONA_HORARIA)
    limite = (momento - timedelta(days=DIAS_GUARDAR_INTENTOS)).isoformat(timespec="seconds")
    with _escritura(conexion):
        conexion.execute("DELETE FROM intentos_entrada WHERE fecha_hora < ?", (limite,))
        conexion.execute(
            "INSERT INTO intentos_entrada (usuario, ip, fecha_hora, exitoso) VALUES (?, ?, ?, ?)",
            (_limpiar(usuario), ip, momento.isoformat(timespec="seconds"), int(bool(exitoso))),
        )


def _fallos_recientes(conexion, columna, valor, desde):
    """Horas de los intentos fallidos de un usuario o IP desde `desde`, sin contar los
    anteriores al último inicio de sesión exitoso de ese mismo usuario o IP."""
    # `columna` solo puede ser "usuario" o "ip" (lo decide minutos_bloqueado, no el usuario).
    filas = conexion.execute(
        f"""SELECT fecha_hora FROM intentos_entrada
            WHERE {columna} = ? AND exitoso = 0 AND fecha_hora >= ?
              AND fecha_hora > COALESCE(
                  (SELECT MAX(fecha_hora) FROM intentos_entrada
                   WHERE {columna} = ? AND exitoso = 1), '')
            ORDER BY fecha_hora""",
        (valor, desde, valor),
    ).fetchall()
    return [datetime.fromisoformat(fila["fecha_hora"]) for fila in filas]


def minutos_bloqueado(conexion, usuario, ip):
    """Minutos que faltan para poder volver a intentar (0 = no está bloqueado).

    Regla (arquitectura, sección 4): si un usuario o una IP junta MAX_INTENTOS fallos dentro
    de MINUTOS_BLOQUEO minutos, queda bloqueado MINUTOS_BLOQUEO minutos desde el fallo con el
    que llegó al límite. Un inicio de sesión exitoso reinicia la cuenta de ese usuario o IP.
    """
    momento = datetime.now(config.ZONA_HORARIA)
    ventana = timedelta(minutes=config.MINUTOS_BLOQUEO)
    # Para saber si alguien llegó al límite en los últimos N minutos hay que mirar 2N minutos.
    desde = (momento - 2 * ventana).isoformat(timespec="seconds")

    restante = timedelta(0)
    for columna, valor in (("usuario", _limpiar(usuario)), ("ip", ip)):
        if not valor:
            continue
        fallos = _fallos_recientes(conexion, columna, valor, desde)
        for i in range(config.MAX_INTENTOS - 1, len(fallos)):
            # El fallo i completa MAX_INTENTOS fallos si el primero de ese grupo está en la ventana.
            if fallos[i] - fallos[i - config.MAX_INTENTOS + 1] <= ventana:
                restante = max(restante, fallos[i] + ventana - momento)
    return math.ceil(restante.total_seconds() / 60)   # redondeo hacia arriba; 0 = libre


# --- Respaldo -------------------------------------------------------------------------------

def respaldar_db(conexion, ruta_destino):
    """Copia completa y consistente de la base de datos con sqlite3 backup()
    (no se copia el archivo, que podría estar a medio escribir)."""
    destino = sqlite3.connect(ruta_destino)
    try:
        conexion.backup(destino)
    finally:
        destino.close()