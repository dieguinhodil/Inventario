"""
ids.py — Paso 4 del diagrama de flujo: ¿ID válido y único? No → asignar TMP-NNN.

Contrato (arquitectura.md, sección 7):
    def asignar_ids(equipos: list[dict]) -> list[dict]

Agrega a cada equipo:
    id_original : el ID tal como viene después de limpieza (para trazabilidad)
    id_final    : el ID que va en el QR (el original o TMP-NNN)
    motivo_id   : ""                 → ID válido y único
                  "sin_id"           → vacío o "Sin información"      → TMP
                  "id_repetido"      → aparece 2+ veces (todas sus filas) → TMP
                  "formato_distinto" → no cumple config.FORMATO_ID   → conserva su ID

Reglas:
- La numeración TMP-001, TMP-002… sigue el orden de fila_excel.
- "id_repetido" tiene prioridad sobre "formato_distinto" (un ID con formato
  distinto que además se repite recibe TMP).
- No quita ni renombra claves; la lista se devuelve en el mismo orden de entrada.

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (16 TMP: 8 sin ID + 8 repetidos).
"""

import re
import sys
from pathlib import Path

if __name__ == "__main__":  # permite probarlo solo: python modulos/ids.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from modulos.limpieza import clave


MOTIVO_OK = ""
MOTIVO_SIN_ID = "sin_id"
MOTIVO_REPETIDO = "id_repetido"
MOTIVO_FORMATO = "formato_distinto"

_CLAVE_SIN_ID = clave(config.SIN_ID)
_PATRON_ID = re.compile(config.FORMATO_ID)


def es_sin_id(valor: str) -> bool:
    """True si el ID está vacío o es "Sin información" (con o sin acento/mayúsculas)."""
    return clave(valor) in ("", _CLAVE_SIN_ID)


def tiene_formato_valido(valor: str) -> bool:
    """True si el ID cumple el patrón CRM GDL AA BB CC."""
    return _PATRON_ID.fullmatch(valor) is not None


def asignar_ids(equipos: list[dict]) -> list[dict]:
    # 1) Contar cuántas veces aparece cada ID real (los "sin ID" no cuentan como repetidos)
    conteo = {}
    for equipo in equipos:
        id_texto = equipo.get("id", "")
        if not es_sin_id(id_texto):
            llave = clave(id_texto)
            conteo[llave] = conteo.get(llave, 0) + 1

    # 2) Decidir el motivo de cada equipo (copias, para no alterar la lista de entrada)
    resultado = []
    for equipo in equipos:
        nuevo = dict(equipo)
        id_texto = nuevo.get("id", "")
        nuevo["id_original"] = id_texto

        if es_sin_id(id_texto):
            nuevo["motivo_id"] = MOTIVO_SIN_ID
        elif conteo[clave(id_texto)] > 1:
            nuevo["motivo_id"] = MOTIVO_REPETIDO
        elif not tiene_formato_valido(id_texto):
            nuevo["motivo_id"] = MOTIVO_FORMATO
        else:
            nuevo["motivo_id"] = MOTIVO_OK

        nuevo["id_final"] = id_texto  # se reemplaza abajo si necesita TMP
        resultado.append(nuevo)

    # 3) Numerar los TMP en orden de fila_excel
    necesitan_tmp = [e for e in resultado if e["motivo_id"] in (MOTIVO_SIN_ID, MOTIVO_REPETIDO)]
    necesitan_tmp.sort(key=lambda e: e["fila_excel"])
    for numero, equipo in enumerate(necesitan_tmp, start=1):
        equipo["id_final"] = f"{config.PREFIJO_TMP}{numero:03d}"

    return resultado


def resumen(equipos: list[dict]) -> dict:
    """Cuenta cuántos equipos hay por motivo (útil para imprimir en main.py o en pruebas)."""
    cuentas = {MOTIVO_OK: 0, MOTIVO_SIN_ID: 0, MOTIVO_REPETIDO: 0, MOTIVO_FORMATO: 0}
    for equipo in equipos:
        cuentas[equipo["motivo_id"]] = cuentas.get(equipo["motivo_id"], 0) + 1
    return cuentas


if __name__ == "__main__":
    # Prueba independiente con datos de ejemplo (no necesita el Excel)
    ejemplo = [
        {"id": "CRM GDL 06 01 01", "fila_excel": 5},
        {"id": "Sin información", "fila_excel": 6},
        {"id": "CRM GDL 06 13 05", "fila_excel": 7},
        {"id": "CRMG 023 01", "fila_excel": 8},
        {"id": "", "fila_excel": 9},
        {"id": "CRM GDL 06 13 05", "fila_excel": 10},
        {"id": "sin informacion", "fila_excel": 4},  # fila menor: debe ser TMP-001
        {"id": "Sin​información", "fila_excel": 11},  # carácter invisible pegado de Excel
        {"id": "CRM GDL 01 01 01\n", "fila_excel": 12},    # salto de línea: no es formato válido
    ]
    salida = asignar_ids(ejemplo)
    for e in salida:
        print(f"fila {e['fila_excel']:>3} | {e['id_original']!r:<22} → {e['id_final']:<18} {e['motivo_id']}")

    esperado = {
        5: ("CRM GDL 06 01 01", ""),
        6: ("TMP-002", "sin_id"),
        7: ("TMP-003", "id_repetido"),
        8: ("CRMG 023 01", "formato_distinto"),
        9: ("TMP-004", "sin_id"),
        10: ("TMP-005", "id_repetido"),
        4: ("TMP-001", "sin_id"),
        11: ("TMP-006", "sin_id"),
        12: ("CRM GDL 01 01 01\n", "formato_distinto"),
    }
    for e in salida:
        assert (e["id_final"], e["motivo_id"]) == esperado[e["fila_excel"]], e
    assert [e["fila_excel"] for e in salida] == [e["fila_excel"] for e in ejemplo]  # mismo orden
    assert "id_final" not in ejemplo[0]  # no modifica la entrada
    print("\nResumen:", resumen(salida))
    print("OK: todas las pruebas pasaron")
