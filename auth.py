"""
auth.py — Inicio de sesión de la app de inventario (versión 2).

Contiene la lógica de sesión; las rutas (/entrar, /salir, /contrasena) las registra app.py.
Así auth.py no necesita importar app.py (la conexión por petición vive allá).

Cómo funciona:
    - La sesión es la cookie firmada de Flask. Guarda el nombre de usuario y una "huella" de
      su contraseña (no la contraseña ni su hash). Si la contraseña cambia, la huella deja de
      coincidir y todas las sesiones abiertas de ese usuario se cierran solas.
    - En cada petición, app.py llama a cargar_usuario() y deja el usuario en flask.g.usuario.
      requiere_sesion() y hay_sesion() solo miran g.usuario.
    - Límite de intentos (arquitectura, sección 4): mientras haya bloqueo NO se revisa la
      contraseña ni se registra el intento (si se registrara, el bloqueo se alargaría).
    - IP del usuario: en PythonAnywhere llega en la cabecera X-Real-IP; request.remote_addr es
      la del balanceador de carga (igual para todos). En la laptop se usa remote_addr.

Usa db.py (sin Flask) para los datos y werkzeug.security para los hashes.
"""

import hashlib
import hmac
from functools import wraps
from urllib.parse import urlsplit

from flask import current_app, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db

LARGO_MIN_CONTRASENA = 12     # arquitectura, sección 2
LARGO_MAX_CONTRASENA = 128    # evita que una contraseña enorme haga lento el cálculo del hash
LARGO_MAX_USUARIO = 30
LARGO_MAX_IP = 45             # lo más largo que mide una IPv6 escrita

MENSAJE_INCORRECTO = "Usuario o contraseña incorrectos."

_hash_falso = None            # ver _comparar_con_hash_falso()


# --- Contraseñas ------------------------------------------------------------------------------

def generar_hash(contrasena):
    """Hash de la contraseña con werkzeug (lo usan crear_usuario.py y /contrasena)."""
    return generate_password_hash(contrasena)


def validar_contrasena_nueva(contrasena, confirmacion, usuario):
    """Revisa una contraseña nueva. Lanza db.ErrorDatos con el motivo si no sirve."""
    if contrasena != confirmacion:
        raise db.ErrorDatos("Las dos contraseñas no coinciden.")
    if len(contrasena) < LARGO_MIN_CONTRASENA:
        raise db.ErrorDatos(f"La contraseña debe tener al menos {LARGO_MIN_CONTRASENA} caracteres.")
    if len(contrasena) > LARGO_MAX_CONTRASENA:
        raise db.ErrorDatos(f"La contraseña puede tener como máximo {LARGO_MAX_CONTRASENA} caracteres.")
    if contrasena.strip() != contrasena:
        raise db.ErrorDatos("La contraseña no debe empezar ni terminar con espacios.")
    if usuario and db.normalizar_texto(usuario) in db.normalizar_texto(contrasena):
        raise db.ErrorDatos("La contraseña no debe contener el nombre de usuario.")


def _comparar_con_hash_falso(contrasena):
    """Cuando el usuario no existe, se calcula un hash de todos modos para que la respuesta
    tarde lo mismo y no revele qué usuarios existen."""
    global _hash_falso
    if _hash_falso is None:
        _hash_falso = generate_password_hash("contrasena-que-nadie-usa")
    check_password_hash(_hash_falso, contrasena)


def huella(hash_contrasena):
    """Resumen del hash de la contraseña, firmado con la clave secreta, para guardar en la
    cookie. No permite reconstruir el hash, pero cambia cuando cambia la contraseña."""
    clave = current_app.secret_key.encode("utf-8")
    return hmac.new(clave, hash_contrasena.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


# --- IP del usuario ---------------------------------------------------------------------------

def ip_cliente():
    """IP real del usuario: X-Real-IP en producción (PythonAnywhere), remote_addr en la laptop.

    X-Real-IP solo se usa en producción porque en la laptop cualquiera podría inventarla.
    """
    ip = None
    if current_app.config["ES_PRODUCCION"]:
        ip = request.headers.get("X-Real-IP")
    ip = (ip or request.remote_addr or "").strip()
    return ip[:LARGO_MAX_IP] or None


# --- Entrar y salir ---------------------------------------------------------------------------

def intentar_entrar(conexion, usuario, contrasena, ip):
    """Revisa usuario y contraseña respetando el límite de intentos.

    Devuelve (fila_del_usuario, None) si entra, o (None, mensaje_de_error) si no.
    """
    usuario = (usuario or "").strip()
    if not usuario or not contrasena:
        return None, "Escribe tu usuario y tu contraseña."
    if len(usuario) > LARGO_MAX_USUARIO:
        # Ningún usuario puede ser tan largo (crear_usuario.py no lo permite): no se registra
        # para no llenar la tabla de intentos con textos enormes.
        return None, MENSAJE_INCORRECTO

    minutos = db.minutos_bloqueado(conexion, usuario, ip)
    if minutos:
        return None, _mensaje_bloqueo(minutos)

    fila = db.obtener_usuario(conexion, usuario)
    if len(contrasena) > LARGO_MAX_CONTRASENA:
        correcta = False                 # imposible: no se aceptan contraseñas tan largas
    elif fila is None:
        _comparar_con_hash_falso(contrasena)
        correcta = False
    else:
        correcta = check_password_hash(fila["hash_contrasena"], contrasena)

    db.registrar_intento(conexion, usuario, ip, correcta)
    if correcta:
        return fila, None

    minutos = db.minutos_bloqueado(conexion, usuario, ip)
    if minutos:
        return None, f"{MENSAJE_INCORRECTO} {_mensaje_bloqueo(minutos)}"
    return None, MENSAJE_INCORRECTO


def verificar_contrasena_actual(conexion, fila, contrasena, ip):
    """Para cambiar la contraseña con sesión abierta: revisa la actual con el mismo límite de
    intentos que /entrar (así una sesión robada no sirve para adivinarla).

    Devuelve None si es correcta, o el mensaje de error.
    """
    minutos = db.minutos_bloqueado(conexion, fila["usuario"], ip)
    if minutos:
        return _mensaje_bloqueo(minutos)
    if (contrasena and len(contrasena) <= LARGO_MAX_CONTRASENA
            and check_password_hash(fila["hash_contrasena"], contrasena)):
        return None
    db.registrar_intento(conexion, fila["usuario"], ip, False)
    return "La contraseña actual no es correcta."


def _mensaje_bloqueo(minutos):
    unidad = "minuto" if minutos == 1 else "minutos"
    return (f"Demasiados intentos fallidos. Espera {minutos} {unidad} antes de volver a "
            "intentar.")


def iniciar_sesion(fila):
    """Abre la sesión del usuario (también se usa tras cambiar la contraseña)."""
    session.clear()                      # cookie nueva: nada de la sesión anterior se conserva
    session["usuario"] = fila["usuario"]
    session["huella"] = huella(fila["hash_contrasena"])
    session.permanent = True             # dura PERMANENT_SESSION_LIFETIME (lo fija app.py)


def cerrar_sesion():
    session.clear()


def cargar_usuario(obtener_conexion):
    """Usuario con sesión de esta petición, o None. app.py lo llama en cada petición.

    obtener_conexion: función que da la conexión de la petición; solo se llama si la cookie
    trae un usuario (las visitas a la ficha pública no abren la base por esto).
    """
    usuario = session.get("usuario")
    if not usuario:
        return None
    fila = db.obtener_usuario(obtener_conexion(), usuario)
    if fila is None or not hmac.compare_digest(str(session.get("huella", "")),
                                               huella(fila["hash_contrasena"])):
        session.clear()                  # usuario borrado o contraseña cambiada
        return None
    return fila


# --- Decorador y ayudas para las plantillas ---------------------------------------------------

def usuario_actual():
    """Fila del usuario con sesión, o None."""
    return g.get("usuario")


def hay_sesion():
    """True si hay un usuario con sesión. Lo usan las plantillas como `hay_sesion`."""
    return usuario_actual() is not None


def requiere_sesion(vista):
    """Manda a /entrar a quien no tenga sesión. Si era una página (GET), vuelve a ella después
    de entrar; si era un formulario (POST), avisa que no se guardó."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if hay_sesion():
            return vista(*args, **kwargs)
        if request.method == "GET":
            destino = request.full_path.rstrip("?")
            siguiente = destino if destino != url_for("buscar") else None
            return redirect(url_for("entrar", siguiente=siguiente))
        flash("Tu sesión terminó. Vuelve a entrar; lo que estabas capturando no se guardó.",
              "error")
        return redirect(url_for("entrar"))
    return envoltura


def destino_seguro(destino):
    """True si `destino` es una dirección de este mismo sitio (evita que un enlace
    /entrar?siguiente=https://otro-sitio mande al usuario a otra página después de entrar)."""
    if not destino or len(destino) > 500 or not destino.startswith("/"):
        return False
    if destino.startswith("//") or "\\" in destino:
        return False
    if any(ord(c) < 32 for c in destino):
        return False
    partes = urlsplit(destino)
    return not partes.scheme and not partes.netloc