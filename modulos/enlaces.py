"""
enlaces.py — Paso 5 del diagrama de flujo: construye el enlace del QR para cada equipo.

Contrato (arquitectura.md, sección 7):
    construir_enlace(equipo: dict, base_url=config.BASE_URL) -> str

- Claves completas en el orden de config.CAMPOS_QR:
  id, tipo, marca, modelo, serie, area, estatus, ultimo_mprev
- La clave "id" toma equipo["id_final"] (lo agrega ids.py).
- Cada valor se codifica con urllib.parse.quote(valor, safe="").
- Los campos vacíos se omiten.
- Los datos van después del "#", así nunca se envían al servidor.
- Debe coincidir con docs/visor.js (que usa decodeURIComponent).

Ejemplo:
    https://dieguinhodil.github.io/Inventario/#id=CRM%20GDL%2001%2002%2003&tipo=Monitor&...

Estado: LISTO — probado con INVENTARIO_JUNIO_2025 (293 enlaces, el más largo 279 caracteres).
"""

import sys
from pathlib import Path
from urllib.parse import quote, unquote

if __name__ == "__main__":  # permite probarlo solo: python modulos/enlaces.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


def construir_enlace(equipo: dict, base_url=config.BASE_URL) -> str:
    """Devuelve el enlace completo del visor con los datos del equipo en el hash."""
    if "id_final" not in equipo:
        raise KeyError(
            f"El equipo de la fila {equipo.get('fila_excel', '?')} no tiene 'id_final'. "
            "Ejecuta ids.asignar_ids() antes de construir los enlaces."
        )

    partes = []
    for campo in config.CAMPOS_QR:
        # La clave "id" del enlace sale de id_final, no del id original del Excel
        valor = equipo["id_final"] if campo == "id" else equipo.get(campo, "")
        valor = "" if valor is None else str(valor).strip()
        if valor == "":
            continue  # campo vacío → no va en el enlace
        partes.append(f"{campo}={quote(valor, safe='')}")

    return f"{base_url}#{'&'.join(partes)}"


def leer_enlace(enlace: str) -> dict:
    """Hace lo mismo que docs/visor.js: separa el hash y decodifica cada campo.
    Sirve para comprobar que lo que se codifica es lo que el visor va a mostrar."""
    _, _, hash_ = enlace.partition("#")
    return {clave: unquote(valor) for clave, valor in
            (parte.split("=", 1) for parte in hash_.split("&") if parte)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prueba del módulo de enlaces")
    parser.add_argument("--excel", default=config.RUTA_EXCEL)
    args = parser.parse_args()

    # 1) Ejemplo con caracteres difíciles (no necesita el Excel)
    ejemplo = {
        "id": "CRM GDL 01 02 03",
        "id_final": "CRM GDL 01 02 03",
        "cuenta": "Cruz Roja Mexicana",
        "tipo": "Máquina de anestesia",
        "marca": "Drägerwerk & Co",
        "modelo": "Fabius GS/Premium",
        "serie": "ASDF-1234",
        "ubicacion": "Cruz Roja Guadalajara",
        "area": "Quirófano",
        "estatus": "Fuera de Servicio",
        "ultimo_mprev": "",          # vacío → se omite
        "fila_excel": 5,
    }
    enlace = construir_enlace(ejemplo)
    print(enlace)
    assert enlace.startswith(config.BASE_URL + "#")
    assert "ultimo_mprev" not in enlace, "Los campos vacíos deben omitirse"
    assert "cuenta" not in enlace and "ubicacion" not in enlace, "Solo van los CAMPOS_QR"
    assert leer_enlace(enlace)["marca"] == "Drägerwerk & Co", "El '&' del valor no debe partir el enlace"
    print("OK: ejemplo\n")

    # 2) Todos los equipos del Excel real, con los pasos 1–4 de main.py
    if not Path(args.excel).exists():
        sys.exit(f"No encuentro el Excel ({args.excel}); se probó solo el ejemplo.")

    from modulos import filtros, ids, lector_excel, limpieza
    incluidos, _ = filtros.separar_por_estatus(limpieza.limpiar(lector_excel.leer_hoja(args.excel)))
    equipos = ids.asignar_ids(incluidos)
    enlaces = [construir_enlace(e) for e in equipos]

    for equipo, enlace in zip(equipos, enlaces):
        esperado = {campo: equipo["id_final"] if campo == "id" else equipo[campo]
                    for campo in config.CAMPOS_QR}
        esperado = {campo: valor for campo, valor in esperado.items() if valor}
        assert leer_enlace(enlace) == esperado, f"fila {equipo['fila_excel']}: el visor leería otra cosa"

    largos = sorted(len(e) for e in enlaces)
    mas_largo = max(zip(enlaces, equipos), key=lambda par: len(par[0]))
    sin_fecha = sum(1 for e in equipos if not e["ultimo_mprev"])
    print(f"Enlaces: {len(enlaces)}  |  únicos: {len(set(enlaces)) == len(enlaces)}")
    print(f"Longitud: mín {largos[0]}, mediana {largos[len(largos) // 2]}, máx {largos[-1]}")
    print(f"Más largo (fila {mas_largo[1]['fila_excel']}):\n  {mas_largo[0]}")
    print(f"Sin último MPrev (se omite del enlace): {sin_fecha} de {len(equipos)}")
    print("OK: el visor leería exactamente los datos de cada equipo")
