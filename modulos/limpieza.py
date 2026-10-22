"""
Paso 2 — Limpiar los datos.

Contrato:
    limpiar(equipos: list[dict]) -> list[dict]

- Quita espacios al inicio/fin y espacios dobles; None -> "".
- Números de serie numéricos -> texto sin ".0".
- Fechas (ultimo_mprev) -> "AAAA-MM-DD".
- Unifica marcas y tipos con config.NORMALIZAR_MARCAS y config.NORMALIZAR_TIPOS.
- No elimina filas ni cambia "fila_excel".

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (316 filas).
"""
import datetime
import unicodedata

import config


def _clave(texto):
    """Forma para comparar: minúsculas, sin acentos y sin espacios extra."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(sin_acentos.casefold().split())


def _preparar(tabla):
    """Convierte {variante: oficial} en {clave(variante): oficial}."""
    return {_clave(variante): oficial for variante, oficial in tabla.items()}


def _a_texto(valor):
    """Convierte cualquier valor de Excel en texto limpio."""
    if valor is None:
        return ""
    if isinstance(valor, (datetime.datetime, datetime.date)):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return " ".join(str(valor).split())


def limpiar(equipos):
    """Devuelve copias de los equipos con todos los valores como texto limpio."""
    marcas = _preparar(config.NORMALIZAR_MARCAS)
    tipos = _preparar(config.NORMALIZAR_TIPOS)

    limpios = []
    for equipo in equipos:
        nuevo = dict(equipo)
        for columna in config.COLUMNAS:
            nuevo[columna] = _a_texto(equipo.get(columna))
        nuevo["marca"] = marcas.get(_clave(nuevo["marca"]), nuevo["marca"])
        nuevo["tipo"] = tipos.get(_clave(nuevo["tipo"]), nuevo["tipo"])
        limpios.append(nuevo)
    return limpios


if __name__ == "__main__":
    ejemplo = [{"fila_excel": 5, "id": " CRM GDL 02 01 01 ", "marca": "Hergom Medical",
                "serie": 120601062, "ultimo_mprev": None}]
    print(limpiar(ejemplo))
