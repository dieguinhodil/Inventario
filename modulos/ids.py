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

Estado: PENDIENTE — se programa en su propio chat siguiendo arquitectura.md.
"""
import config


def asignar_ids(equipos):
    raise NotImplementedError


if __name__ == "__main__":
    ejemplo = [{"fila_excel": 5, "id": "Sin información"},
               {"fila_excel": 6, "id": "CRM GDL 06 01 11"},
               {"fila_excel": 7, "id": "CRM GDL 06 01 11"},
               {"fila_excel": 8, "id": "CRM GDL 02 01 01"}]
    for e in asignar_ids(ejemplo):
        print(e)
