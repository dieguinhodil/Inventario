"""
Paso 3 — ¿Estatus es Baja?

Contrato:
    separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS) -> (incluidos, excluidos)
    filtrar(equipos, area=None, estatus=None) -> list[dict]

- La comparación ignora mayúsculas y espacios.
- filtrar() es un filtro general reutilizable (ej. solo Urgencias). El área es un parámetro.

Estado: PENDIENTE — se programa en su propio chat siguiendo arquitectura.md.
"""
import config


def separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS):
    raise NotImplementedError


def filtrar(equipos, area=None, estatus=None):
    raise NotImplementedError


if __name__ == "__main__":
    ejemplo = [{"estatus": "Funcional", "area": "Urgencias"}, {"estatus": "Baja", "area": "Socorros"}]
    print(separar_por_estatus(ejemplo))
    print(filtrar(ejemplo, area="Urgencias"))
