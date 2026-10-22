"""
Paso 3 — ¿Estatus es Baja?

Contrato:
    separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS) -> (incluidos, excluidos)
    filtrar(equipos, area=None, estatus=None) -> list[dict]

- La comparación ignora mayúsculas y espacios.
- filtrar() es un filtro general reutilizable (ej. solo Urgencias). El área es un parámetro.

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (293 incluidos, 23 excluidos).
"""
import config
from modulos.limpieza import clave


def separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS):
    """Separa los equipos cuyo estatus está en `excluidos` (ej. Baja)."""
    claves_excluidas = {clave(e) for e in excluidos}
    incluidos, fuera = [], []
    for equipo in equipos:
        if clave(equipo["estatus"]) in claves_excluidas:
            fuera.append(equipo)
        else:
            incluidos.append(equipo)
    return incluidos, fuera


def filtrar(equipos, area=None, estatus=None):
    """Devuelve los equipos del área y/o estatus indicados. None = sin filtrar por ese campo."""
    resultado = []
    for equipo in equipos:
        if area is not None and clave(equipo["area"]) != clave(area):
            continue
        if estatus is not None and clave(equipo["estatus"]) != clave(estatus):
            continue
        resultado.append(equipo)
    return resultado


if __name__ == "__main__":
    ejemplo = [{"estatus": "Funcional", "area": "Urgencias"}, {"estatus": "Baja", "area": "Socorros"}]
    print(separar_por_estatus(ejemplo))
    print(filtrar(ejemplo, area="Urgencias"))
