"""
limpieza.py — Paso 2 del diagrama de flujo.

Contrato (arquitectura.md, sección 7):
    def limpiar(equipos: list[dict]) -> list[dict]

- Quita espacios al inicio/fin y espacios dobles; None -> "".
- Números (no. de serie, modelo) -> texto sin ".0" (ej. 120601062).
- Fechas (ultimo_mprev) -> "AAAA-MM-DD".
- Unifica variantes de marca y tipo con config.NORMALIZAR_MARCAS y config.NORMALIZAR_TIPOS.
- No elimina filas ni cambia fila_excel.

Después de limpiar, todos los valores de config.COLUMNAS son str ("" si no hay dato).
Las demás claves (fila_excel, etc.) se copian sin tocar.
"""

import re
import sys
import unicodedata
import warnings
from datetime import date, datetime, timedelta
from pathlib import Path

if __name__ == "__main__":  # permite probarlo solo: python modulos/limpieza.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


# Cualquier espacio "raro" (tab, salto de línea, espacio duro de Excel, ancho cero) cuenta como espacio.
_ESPACIOS = re.compile(r"[\s ​‌‍﻿]+")

# Formatos de fecha que se aceptan si la fecha llega como texto
# (por si alguien captura la columna K a mano en lugar de usar formato de fecha).
_FORMATOS_FECHA = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"]

# Excel cuenta los días desde el 30/12/1899 (fecha "serial").
_ORIGEN_EXCEL = datetime(1899, 12, 30)


def limpiar_texto(valor) -> str:
    """Convierte cualquier valor de celda en texto limpio. None -> ""."""
    if valor is None:
        return ""
    if isinstance(valor, bool):          # bool es subclase de int: se trata aparte
        return str(valor)
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)               # 120601062.0 -> 120601062
    if isinstance(valor, (datetime, date)):
        return limpiar_fecha(valor)
    texto = str(valor)
    return _ESPACIOS.sub(" ", texto).strip()


def limpiar_fecha(valor) -> str:
    """Devuelve la fecha como 'AAAA-MM-DD', o "" si no hay fecha o no se reconoce."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        # Número serial de Excel (ej. 45678). Rango razonable: 1990–2100.
        if 32874 <= valor <= 73051:
            return (_ORIGEN_EXCEL + timedelta(days=int(valor))).date().isoformat()
        raise ValueError(f"número que no parece fecha: {valor!r}")
    texto = limpiar_texto(valor)
    if texto == "":
        return ""
    for formato in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"texto que no parece fecha: {texto!r}")


def clave(texto: str) -> str:
    """Forma de comparar variantes: sin mayúsculas, acentos ni espacios sobrantes.
    La usan también filtros.py e ids.py."""
    texto = unicodedata.normalize("NFKD", limpiar_texto(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def _preparar_tabla(normalizar: dict) -> dict:
    """Convierte {'Hergom Medical': 'HERGOM'} en {'hergom medical': 'HERGOM'}."""
    return {clave(variante): unificado for variante, unificado in normalizar.items()}


def normalizar(texto: str, tabla: dict) -> str:
    """Si el texto es una variante conocida, devuelve el nombre unificado."""
    return tabla.get(clave(texto), texto)


def limpiar(equipos: list[dict]) -> list[dict]:
    """Limpia la lista de equipos. Devuelve una lista nueva (no modifica la original)."""
    tabla_marcas = _preparar_tabla(config.NORMALIZAR_MARCAS)
    tabla_tipos = _preparar_tabla(config.NORMALIZAR_TIPOS)

    limpios = []
    for equipo in equipos:
        nuevo = dict(equipo)  # copia: conserva fila_excel y cualquier otra clave

        for columna in config.COLUMNAS:
            valor = equipo.get(columna)
            if columna == "ultimo_mprev":
                try:
                    nuevo[columna] = limpiar_fecha(valor)
                except ValueError as error:
                    # No se inventa una fecha: se deja vacía y se avisa con la fila.
                    warnings.warn(
                        f"Fila {equipo.get('fila_excel', '?')}: último MPrev no reconocido "
                        f"({error}); se deja vacío.",
                        stacklevel=2,
                    )
                    nuevo[columna] = ""
            else:
                nuevo[columna] = limpiar_texto(valor)

        nuevo["marca"] = normalizar(nuevo["marca"], tabla_marcas)
        nuevo["tipo"] = normalizar(nuevo["tipo"], tabla_tipos)
        limpios.append(nuevo)

    return limpios


# ---------------------------------------------------------------------------
# Prueba independiente: python modulos/limpieza.py --excel INVENTARIO_JUNIO_2025.xlsx
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    from collections import Counter

    parser = argparse.ArgumentParser(description="Prueba del módulo de limpieza")
    parser.add_argument("--excel", default=config.RUTA_EXCEL)
    args = parser.parse_args()

    from modulos import lector_excel
    crudos = lector_excel.leer_hoja(args.excel)
    limpios = limpiar(crudos)

    print(f"Filas leídas: {len(crudos)}  |  Filas después de limpiar: {len(limpios)}")
    assert len(crudos) == len(limpios), "limpiar() no debe eliminar filas"
    assert all(a["fila_excel"] == b["fila_excel"] for a, b in zip(crudos, limpios))
    assert all(isinstance(e[c], str) for e in limpios for c in config.COLUMNAS)

    cambios = Counter()
    for antes, despues in zip(crudos, limpios):
        for columna in config.COLUMNAS:
            if antes.get(columna) != despues[columna]:
                cambios[columna] += 1
    print("\nCeldas modificadas por columna:")
    for columna in config.COLUMNAS:
        print(f"  {columna:13} {cambios[columna]}")

    print("\nMarcas unificadas:")
    for antes, despues in zip(crudos, limpios):
        if limpiar_texto(antes["marca"]) != despues["marca"]:
            print(f"  fila {despues['fila_excel']}: {antes['marca']!r} -> {despues['marca']!r}")
    print("\nTipos unificados:")
    for antes, despues in zip(crudos, limpios):
        if limpiar_texto(antes["tipo"]) != despues["tipo"]:
            print(f"  fila {despues['fila_excel']}: {antes['tipo']!r} -> {despues['tipo']!r}")

    con_fecha = sum(1 for e in limpios if e["ultimo_mprev"])
    print(f"\nEquipos con último MPrev: {con_fecha} de {len(limpios)}")
    print(f"Marcas distintas: {len({e['marca'] for e in limpios})}  |  "
          f"Tipos distintos: {len({e['tipo'] for e in limpios})}")