"""
importar_excel.py — Carga el inventario del Excel a la base de datos (versión 2).

Script de UNA SOLA VEZ. Se corre en la laptop, antes de imprimir etiquetas:

    python importar_excel.py
    python importar_excel.py --excel otra/ruta.xlsx --db pruebas.db

Qué hace:
    1. Lee la hoja config.HOJA con modulos/lector_excel.py (columnas B..K).
    2. Revisa las fechas de la columna K ANTES de escribir nada. Si alguna está mal o es
       posterior a hoy, muestra la lista de filas y se detiene sin tocar la base de datos.
    3. Limpia las filas con modulos/limpieza.py y escribe el estatus con la forma exacta
       de config.ESTATUS ("baja" → "Baja").
    4. Asigna los ID internos con modulos/ids.py, solo para los equipos que no están en Baja
       (igual que en la versión 1). Los equipos en Baja conservan su ID si es único;
       si no tienen ID o está repetido, quedan sin ID (NULL).
    5. Dentro de una sola transacción: da de alta los equipos (db.insertar_equipo genera
       el código del QR) y guarda la columna K como mantenimiento preventivo.
       Se guardan todos o ninguno.

No se importa si la base de datos ya tiene equipos (ver _revisar_base_vacia).
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import config
import db
from modulos import ids, lector_excel, limpieza

# Quién aparece como autor de los datos importados (actualizado_por / registrado_por).
USUARIO_IMPORTACION = "importacion"

# Columnas limpias que se guardan tal cual en la tabla `equipos`.
CAMPOS_TEXTO = ("tipo", "marca", "modelo", "serie", "area")

AYUDA_FECHAS = (
    "La columna K (Último MPrev.) debe tener una celda con formato de fecha de Excel, "
    "o texto en alguno de estos formatos: AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA "
    "o DD/MM/AA (por ejemplo 2025-01-15 o 15/01/2025). "
    "No se permiten fechas posteriores a hoy. Si no hay mantenimiento, deja la celda vacía."
)


class ErrorImportacion(Exception):
    """Problema en el Excel o en la base de datos que impide importar. Se muestra tal cual."""


# --- Fechas de la columna K -------------------------------------------------------------------

def revisar_fechas(crudos):
    """Revisa la columna K de todas las filas (sin limpiar). Si alguna no se reconoce como
    fecha o es posterior a hoy, lanza ErrorImportacion con TODAS las filas con problema.

    Se hace antes de limpieza.limpiar(), que deja vacía una fecha que no reconoce: aquí se
    prefiere detener la importación para que no se pierda ningún mantenimiento.
    """
    problemas = []
    for fila in crudos:
        try:
            texto = limpieza.limpiar_fecha(fila["ultimo_mprev"])
        except ValueError as error:
            problemas.append(f"  - Fila {fila['fila_excel']}: {error}")
            continue
        if texto and date.fromisoformat(texto) > db.hoy():
            problemas.append(f"  - Fila {fila['fila_excel']}: {texto} es posterior a hoy")
    if problemas:
        raise ErrorImportacion(
            "Hay fechas que no se pueden importar en la columna K:\n"
            + "\n".join(problemas) + "\n\n" + AYUDA_FECHAS
            + "\nCorrige el Excel y vuelve a correr el script. No se guardó nada."
        )


# --- Estatus e ID internos --------------------------------------------------------------------

_CATALOGO_ESTATUS = {limpieza.clave(e): e for e in config.ESTATUS}


def _estatus(texto):
    """Estatus con la forma exacta de config.ESTATUS. Si no está en el catálogo se conserva
    como venga (y se avisa en el resumen)."""
    return _CATALOGO_ESTATUS.get(limpieza.clave(texto), texto)


def _es_baja(estatus):
    return limpieza.clave(estatus) in config.ESTATUS_EXCLUIDOS


def asignar_id_interno(limpios):
    """Devuelve {fila_excel: (id_interno, motivo_id)} para todas las filas.

    - Equipos que no están en Baja: ids.asignar_ids(), igual que en la versión 1
      (los TMP salen con la misma numeración).
    - Equipos en Baja: sin ID o con ID repetido → None; si no, conservan su ID.
      Sus motivos salen de ids.asignar_ids() sobre TODAS las filas, para que los repetidos
      se cuenten contra todo el inventario y ningún ID quede dos veces.
    """
    activos = [e for e in limpios if not _es_baja(e["estatus"])]
    resultado = {e["fila_excel"]: (e["id_final"], e["motivo_id"])
                 for e in ids.asignar_ids(activos)}

    for equipo in ids.asignar_ids(limpios):
        if equipo["fila_excel"] not in resultado:   # solo los de Baja
            sin_id = equipo["motivo_id"] in (ids.MOTIVO_SIN_ID, ids.MOTIVO_REPETIDO)
            resultado[equipo["fila_excel"]] = (None if sin_id else equipo["id"], equipo["motivo_id"])
    return resultado


def preparar(limpios):
    """Filas limpias → lista de (datos para db.insertar_equipo, fecha del MPrev, motivo_id)."""
    asignados = asignar_id_interno(limpios)
    preparados = []
    for equipo in limpios:
        id_interno, motivo = asignados[equipo["fila_excel"]]
        datos = {campo: equipo[campo] for campo in CAMPOS_TEXTO}
        datos.update(
            id_interno=id_interno,
            id_original=equipo["id"],
            estatus=_estatus(equipo["estatus"]),
            fila_excel=equipo["fila_excel"],
        )
        # db.insertar_equipo convierte el texto vacío ("") en NULL.
        preparados.append((datos, equipo["ultimo_mprev"], motivo))
    return preparados


# --- Base de datos ----------------------------------------------------------------------------

def _revisar_base_vacia(conexion, ruta_db):
    """Se detiene si ya hay equipos: importar dos veces duplicaría el inventario y, una vez
    impresas las etiquetas, reimportar cambiaría todos los códigos de los QR."""
    cuantos = conexion.execute("SELECT COUNT(*) FROM equipos").fetchone()[0]
    if cuantos:
        raise ErrorImportacion(
            f"La base de datos ya tiene {cuantos} equipos, así que no se importó nada.\n"
            "Este script solo se corre una vez, con la base de datos vacía.\n"
            "Si de verdad quieres empezar de cero (y todavía NO se imprimieron etiquetas), "
            f"borra a mano el archivo {ruta_db} y vuelve a correr el script."
        )


def guardar(conexion, preparados):
    """Da de alta equipos y mantenimientos en una sola transacción. Devuelve cuántos
    mantenimientos se guardaron."""
    total_mant = 0
    with db.transaccion(conexion):
        for datos, fecha_mprev, _ in preparados:
            num = db.insertar_equipo(conexion, datos, USUARIO_IMPORTACION)
            if fecha_mprev:
                db.registrar_mantenimiento(
                    conexion, num, fecha_mprev, "preventivo",
                    config.DESCRIPCION_MPREV_IMPORTADO,
                    realizado_por=None, registrado_por=USUARIO_IMPORTACION,
                )
                total_mant += 1
    return total_mant


# --- Resumen ----------------------------------------------------------------------------------

def imprimir_resumen(preparados, total_mant):
    print(f"\n✔ Importación terminada: {len(preparados)} equipos y {total_mant} mantenimientos "
          "preventivos.\n")

    tmp = [(d, m) for d, _, m in preparados if (d["id_interno"] or "").startswith(config.PREFIJO_TMP)]
    print(f"ID temporales asignados ({len(tmp)}):")
    for datos, motivo in tmp:
        print(f"  Fila {datos['fila_excel']:>3}: {datos['id_interno']}  "
              f"(venía: {datos['id_original'] or 'vacío'}; {motivo})")

    baja_sin_id = [d for d, _, _ in preparados if d["id_interno"] is None]
    print(f"\nEquipos en Baja que quedaron sin ID ({len(baja_sin_id)}):")
    for datos in baja_sin_id:
        print(f"  Fila {datos['fila_excel']:>3}  (venía: {datos['id_original'] or 'vacío'})")

    formato = [d for d, _, m in preparados if m == ids.MOTIVO_FORMATO]
    print(f"\nID con formato distinto a «CRM GDL AA BB CC» (se conservaron) ({len(formato)}):")
    for datos in formato:
        print(f"  Fila {datos['fila_excel']:>3}: {datos['id_interno']}")

    raros = [d for d, _, _ in preparados if d["estatus"] and d["estatus"] not in config.ESTATUS]
    if raros:
        print(f"\n⚠ Estatus que no están en el catálogo (se guardaron tal cual) ({len(raros)}):")
        for datos in raros:
            print(f"  Fila {datos['fila_excel']:>3}: {datos['estatus']}")
    sin_estatus = [d["fila_excel"] for d, _, _ in preparados if not d["estatus"]]
    if sin_estatus:
        print(f"\n⚠ Equipos sin estatus ({len(sin_estatus)}): filas {sin_estatus}")


# --- Programa principal -----------------------------------------------------------------------

def importar(ruta_excel, ruta_db=None):
    """Importa el Excel a la base de datos. Devuelve (preparados, total_mant)."""
    ruta_excel = Path(ruta_excel)
    if not ruta_excel.exists():
        raise ErrorImportacion(f"No se encontró el Excel: {ruta_excel}")

    crudos = lector_excel.leer_hoja(ruta_excel)
    revisar_fechas(crudos)                  # antes de abrir la base de datos
    preparados = preparar(limpieza.limpiar(crudos))

    conexion = db.conectar(ruta_db)
    try:
        db.crear_tablas(conexion)
        _revisar_base_vacia(conexion, ruta_db or config.RUTA_DB)
        total_mant = guardar(conexion, preparados)
    finally:
        conexion.close()
    return preparados, total_mant


def main(argv=None):
    parser = argparse.ArgumentParser(description="Carga el inventario del Excel a la base de datos.")
    parser.add_argument("--excel", default=config.RUTA_EXCEL,
                        help=f"Ruta del Excel (por defecto {config.RUTA_EXCEL.name})")
    parser.add_argument("--db", default=None,
                        help=f"Ruta de la base de datos (por defecto instancia/{config.RUTA_DB.name})")
    args = parser.parse_args(argv)

    try:
        preparados, total_mant = importar(args.excel, args.db)
    except ErrorImportacion as error:
        print(f"\n✘ {error}", file=sys.stderr)
        return 1
    except db.ErrorDatos as error:
        print(f"\n✘ {error}\nSe deshizo la importación: no se guardó nada.", file=sys.stderr)
        return 1
    imprimir_resumen(preparados, total_mant)
    return 0


if __name__ == "__main__":  
    sys.exit(main())