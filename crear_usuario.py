"""
crear_usuario.py — Da de alta a los usuarios de la app o les cambia la contraseña.

Se corre en la consola de la computadora donde está la base de datos que se quiere cambiar:
en la laptop para desarrollar, y en una consola Bash de PythonAnywhere para la app publicada
(cada una tiene su propia instancia/inventario.db).

Uso:
    python3 crear_usuario.py diego "Diego"            → crea el usuario (pide la contraseña)
    python3 crear_usuario.py jefatura "Jefatura de Biomédica"
    python3 crear_usuario.py --cambiar diego           → cambia la contraseña de un usuario

La contraseña se escribe dos veces y no se ve en pantalla. Debe tener al menos 12 caracteres
y no usarse en ningún otro lado. Al cambiarla se cierran las sesiones abiertas de ese usuario.
Si alguien olvida su contraseña, se usa --cambiar (la app no manda correos).
"""

import argparse
import getpass
import re
import sys
from contextlib import closing

import auth
import db

# Letras minúsculas sin acentos, números, punto, guion y guion bajo.
FORMATO_USUARIO = re.compile(rf"^[a-z0-9._-]{{3,{auth.LARGO_MAX_USUARIO}}}$")

# Nombres que ya se usan para otra cosa en la base de datos.
USUARIOS_RESERVADOS = {"importacion"}   # autor de los datos importados del Excel


def validar_usuario(usuario):
    """Revisa el nombre de usuario. Lanza db.ErrorDatos con el motivo si no sirve."""
    if not FORMATO_USUARIO.match(usuario):
        raise db.ErrorDatos(
            f"El usuario debe tener de 3 a {auth.LARGO_MAX_USUARIO} caracteres: letras minúsculas "
            "sin acentos, números, punto, guion o guion bajo (por ejemplo: diego)."
        )
    if usuario in USUARIOS_RESERVADOS:
        raise db.ErrorDatos(f"El nombre {usuario} está reservado; elige otro.")


def pedir_contrasena(usuario, pedir=getpass.getpass):
    """Pide la contraseña dos veces hasta que sea válida y devuelve su hash."""
    while True:
        contrasena = pedir(f"Contraseña nueva para {usuario} (no se ve al escribir): ")
        confirmacion = pedir("Escríbela otra vez: ")
        try:
            auth.validar_contrasena_nueva(contrasena, confirmacion, usuario)
        except db.ErrorDatos as error:
            print(f"✗ {error} Intenta de nuevo.\n")
            continue
        return auth.generar_hash(contrasena)


def crear(conexion, usuario, nombre, pedir=getpass.getpass):
    validar_usuario(usuario)
    if db.obtener_usuario(conexion, usuario) is not None:
        raise db.ErrorDatos(f"Ya existe el usuario {usuario}. Para cambiarle la contraseña "
                            f"usa: python3 crear_usuario.py --cambiar {usuario}")
    hash_contrasena = pedir_contrasena(usuario, pedir)
    db.crear_usuario(conexion, usuario, nombre, hash_contrasena)
    print(f"✓ Usuario {usuario} creado.")


def cambiar(conexion, usuario, pedir=getpass.getpass):
    if db.obtener_usuario(conexion, usuario) is None:
        raise db.ErrorDatos(f"No existe el usuario {usuario}.")
    hash_contrasena = pedir_contrasena(usuario, pedir)
    db.cambiar_contrasena(conexion, usuario, hash_contrasena)
    print(f"✓ Contraseña de {usuario} cambiada. Sus sesiones abiertas se cerraron.")


def main(argumentos=None, pedir=getpass.getpass, ruta_db=None):
    lector = argparse.ArgumentParser(
        description="Crea usuarios de la app de inventario o les cambia la contraseña.")
    lector.add_argument("usuario", help="nombre de usuario, por ejemplo: diego")
    lector.add_argument("nombre", nargs="?", help="nombre para mostrar (solo al crear)")
    lector.add_argument("--cambiar", action="store_true",
                        help="cambiar la contraseña de un usuario que ya existe")
    opciones = lector.parse_args(argumentos)
    usuario = opciones.usuario.strip().lower()

    try:
        with closing(db.conectar(ruta_db)) as conexion:
            db.crear_tablas(conexion)
            if opciones.cambiar:
                cambiar(conexion, usuario, pedir)
            else:
                nombre = (opciones.nombre or "").strip()
                if not nombre:
                    lector.error('falta el nombre, por ejemplo: python3 crear_usuario.py diego "Diego"')
                crear(conexion, usuario, nombre, pedir)
    except db.ErrorDatos as error:
        print(f"✗ {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado. No se guardó nada.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())