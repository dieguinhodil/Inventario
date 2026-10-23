#!/usr/bin/env python3
"""
Programa principal. Sigue el diagrama de flujo de arquitectura.md:

  1. Leer hoja            -> modulos.lector_excel.leer_hoja
  2. Limpiar datos        -> modulos.limpieza.limpiar
  3. ¿Estatus es Baja?    -> modulos.filtros.separar_por_estatus
  4. ¿ID válido y único?  -> modulos.ids.asignar_ids
  5. Construir enlace     -> modulos.enlaces.construir_enlace
  6. Generar QR           -> modulos.generador_qr.generar_qr
  7. Armar PDF            -> modulos.pdf_etiquetas.armar_pdf

Uso:
  python main.py --excel ruta/al/inventario.xlsx            # solo prepara datos (pasos 1-5)
  python main.py --excel ruta/al/inventario.xlsx --qr       # también genera QR y PDF (pasos 6-7)

Si un módulo todavía no está programado, el programa se detiene en ese paso
y avisa cuál falta, sin romper los pasos anteriores.
"""
import argparse
import csv
import os
import sys

import config
from modulos import lector_excel, limpieza, filtros, ids, enlaces, generador_qr, pdf_etiquetas


class PasoPendiente(Exception):
    pass


def ejecutar(numero, nombre, funcion, *args, **kwargs):
    print(f"[{numero}/7] {nombre}...", end=" ")
    try:
        resultado = funcion(*args, **kwargs)
    except NotImplementedError:
        print("PENDIENTE")
        raise PasoPendiente(f"El paso {numero} ({nombre}) aún no está programado.")
    print("ok")
    return resultado


def guardar_csv(ruta, filas):
    if not filas:
        return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    claves = list(filas[0].keys())
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        escritor = csv.DictWriter(fh, fieldnames=claves, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)


def main():
    parser = argparse.ArgumentParser(description="Genera QR del inventario de equipo médico.")
    parser.add_argument("--excel", default=config.RUTA_EXCEL, help="Ruta al Excel del inventario")
    parser.add_argument("--qr", action="store_true", help="Generar imágenes QR y PDF (pasos 6 y 7)")
    args = parser.parse_args()

    if not os.path.exists(args.excel):
        sys.exit(f"No encuentro el Excel: {args.excel}")

    try:
        # 1. Leer
        equipos = ejecutar(1, "Leer hoja " + config.HOJA, lector_excel.leer_hoja, args.excel)
        print(f"      {len(equipos)} filas leídas")

        # 2. Limpiar
        equipos = ejecutar(2, "Limpiar datos", limpieza.limpiar, equipos)

        # 3. ¿Estatus es Baja?
        incluidos, excluidos = ejecutar(3, "Separar por estatus", filtros.separar_por_estatus, equipos)
        print(f"      {len(incluidos)} incluidos, {len(excluidos)} excluidos")
        guardar_csv(config.CSV_EXCLUIDOS, excluidos)

        # 4. ¿ID válido y único?
        incluidos = ejecutar(4, "Asignar IDs", ids.asignar_ids, incluidos)
        tmp = sum(1 for e in incluidos if e["id_final"].startswith(config.PREFIJO_TMP))
        print(f"      {tmp} IDs temporales")

        # 5. Construir enlace
        def construir_todos(lista):
            for e in lista:
                e["enlace"] = enlaces.construir_enlace(e)
            return lista
        incluidos = ejecutar(5, "Construir enlaces", construir_todos, incluidos)
        guardar_csv(config.CSV_REVISION, incluidos)
        print(f"      Revisión guardada en {config.CSV_REVISION}")

        if not args.qr:
            print("\nListo (sin QR). Revisa el CSV y vuelve a correr con --qr.")
            return

        # 6. Generar QR
        def generar_todos(lista):
            os.makedirs(config.CARPETA_QR, exist_ok=True)
            for e in lista:
                nombre = e["id_final"].replace(" ", "_") + ".png"
                e["ruta_qr"] = generador_qr.generar_qr(e["enlace"], os.path.join(config.CARPETA_QR, nombre))
            return lista
        incluidos = ejecutar(6, "Generar QR", generar_todos, incluidos)

        # 7. Armar PDF
        ruta = ejecutar(7, "Armar PDF", pdf_etiquetas.armar_pdf, incluidos, config.PDF_ETIQUETAS)
        print(f"\nListo. PDF en {ruta}")

    except PasoPendiente as aviso:
        print(f"\n{aviso}")
        print("Prográmalo en su chat siguiendo arquitectura.md y vuelve a correr main.py.")


if __name__ == "__main__":
    main()
