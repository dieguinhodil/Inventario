"""
Paso 4 — ¿ID válido y único?

Contrato:
    asignar_ids(equipos: list[dict]) -> list[dict]

Agrega a cada equipo:
    id_original  -> el ID tal cual venía
    id_final     -> el ID que va en el QR
    motivo_id    -> "", "sin_id", "id_repetido" o "formato_distinto"

- "sin_id" (config.SIN_ID o vacío) e "id_repetido" (2+ veces) reciben TMP-001, TMP-002...
  en orden de fila_excel. Si un ID está repetido, TODAS sus filas reciben TMP.
- "formato_distinto" (no cumple config.FORMATO_ID) conserva su ID; solo se marca.

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (16 TMP: 8 sin ID + 8 repetidos).
"""
import collections
import re

import config
from modulos.limpieza import clave


def _motivo(id_equipo, conteo):
    """Decide el motivo_id de un ID según las reglas del contrato."""
    if clave(id_equipo) in ("", clave(config.SIN_ID)):
        return "sin_id"
    if conteo[clave(id_equipo)] > 1:
        return "id_repetido"
    if not re.fullmatch(config.FORMATO_ID, id_equipo):
        return "formato_distinto"
    return ""


def asignar_ids(equipos):
    """Devuelve copias de los equipos con id_original, id_final y motivo_id."""
    conteo = collections.Counter(clave(e["id"]) for e in equipos)

    resultado = []
    for equipo in equipos:
        nuevo = dict(equipo)
        nuevo["id_original"] = equipo["id"]
        nuevo["id_final"] = equipo["id"]
        nuevo["motivo_id"] = _motivo(equipo["id"], conteo)
        resultado.append(nuevo)

    # TMP numerados en orden de fila del Excel, aunque la lista venga en otro orden
    necesitan_tmp = [e for e in resultado if e["motivo_id"] in ("sin_id", "id_repetido")]
    for numero, equipo in enumerate(sorted(necesitan_tmp, key=lambda e: e["fila_excel"]), start=1):
        equipo["id_final"] = f"{config.PREFIJO_TMP}{numero:03d}"
    return resultado


if __name__ == "__main__":
    ejemplo = [{"fila_excel": 5, "id": "Sin información"},
               {"fila_excel": 6, "id": "CRM GDL 06 01 11"},
               {"fila_excel": 7, "id": "CRM GDL 06 01 11"},
               {"fila_excel": 8, "id": "CRM GDL 02 01 01"}]
    for e in asignar_ids(ejemplo):
        print(e)
