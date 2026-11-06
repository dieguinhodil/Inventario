"""
pruebas_respaldo.py — Pruebas de respaldo.py y de las rutas del respaldo (chat 6).

Uso:  python3 -m unittest pruebas_respaldo -v

Cada prueba usa una base de datos y una clave secreta temporales: no toca instancia/.
"""

import io
import os
import sqlite3
import tempfile
import unittest
import zipfile
from datetime import datetime

# pruebas_app cambia las rutas de config a una carpeta temporal antes de importar app.py.
from pruebas_app import BaseApp

from openpyxl import load_workbook  # noqa: E402

import config  # noqa: E402
import db  # noqa: E402
import respaldo  # noqa: E402

HASH_PRUEBA = "pbkdf2:sha256:600000$hashdeprueba$no-debe-salir-en-el-excel"
TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def libro(datos):
    return load_workbook(io.BytesIO(datos))


def xml_del_excel(datos):
    """Todo el XML del .xlsx junto (para buscar texto o fórmulas en el archivo crudo)."""
    with zipfile.ZipFile(io.BytesIO(datos)) as archivo:
        return b"".join(archivo.read(nombre) for nombre in archivo.namelist())


def filas(hoja):
    """Filas de una hoja (sin el encabezado) como diccionarios {encabezado: valor}."""
    encabezados = [c.value for c in hoja[1]]
    return [dict(zip(encabezados, fila)) for fila in hoja.iter_rows(min_row=2, values_only=True)]


# --- respaldo.py con una base propia ---------------------------------------------------------------

class BaseDatos(unittest.TestCase):
    """Base temporal con un equipo padre, un componente, un equipo en Baja, mantenimientos,
    un usuario y un intento de entrada."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.conexion = db.conectar(os.path.join(self.carpeta.name, "prueba.db"))
        db.crear_tablas(self.conexion)
        c = self.conexion
        self.padre = db.insertar_equipo(c, {
            "tipo": "Monitor", "marca": "Mindray", "id_interno": "CRM GDL 01 02 03",
            "estatus": "Funcional", "area": "Urgencias",
            "notas": '=HYPERLINK("http://ejemplo.com","clic")\nsegunda línea\x01'}, "diego")
        self.hijo = db.insertar_equipo(c, {"tipo": "Sensor", "padre_num": self.padre,
                                           "estatus": "Funcional"}, "diego")
        self.baja = db.insertar_equipo(c, {"tipo": "Viejo", "estatus": "Baja"}, "jefatura")
        db.registrar_mantenimiento(c, self.padre, "2025-01-15", "preventivo", "=1+1",
                                   "Técnico externo", "diego")
        db.registrar_mantenimiento(c, self.padre, "2025-06-01", "preventivo", "Revisión", None,
                                   "diego")
        db.registrar_mantenimiento(c, self.padre, "2026-01-10", "correctivo", "Cable", None,
                                   "diego")
        db.crear_usuario(c, "diego", "Diego", HASH_PRUEBA)
        db.registrar_intento(c, "diego", "203.0.113.7", False)

    def tearDown(self):
        self.conexion.close()
        self.carpeta.cleanup()


class PruebasResumen(BaseDatos):

    def test_conteos(self):
        self.assertEqual(respaldo.resumen(self.conexion),
                         {"equipos": 3, "en_baja": 1, "mantenimientos": 3})


class PruebasExcel(BaseDatos):

    def setUp(self):
        super().setUp()
        self.datos = respaldo.excel(self.conexion, "diego")
        self.libro = libro(self.datos)

    def test_hojas(self):
        self.assertEqual(self.libro.sheetnames, ["Equipos", "Mantenimientos", "Información"])

    def test_equipos_incluye_baja_y_columnas(self):
        hoja = self.libro["Equipos"]
        self.assertEqual(tuple(c.value for c in hoja[1]), respaldo.ENCABEZADOS_EQUIPOS)
        equipos = filas(hoja)
        self.assertEqual([e["Núm."] for e in equipos], [self.padre, self.hijo, self.baja])
        self.assertEqual(equipos[2]["Estatus"], "Baja")

    def test_codigo_enlace_padre_y_preventivo(self):
        padre, hijo, _ = filas(self.libro["Equipos"])
        codigo = db.obtener_equipo_por_num(self.conexion, self.padre)["codigo"]
        self.assertEqual(padre["Código del QR"], codigo)
        self.assertEqual(padre["Enlace del QR"], f"{config.BASE_URL}{config.RUTA_FICHA}{codigo}")
        self.assertEqual(padre["Último preventivo"], "2025-06-01")     # el correctivo no cuenta
        self.assertIsNone(hijo["Último preventivo"])
        self.assertEqual(hijo["Núm. del padre"], self.padre)
        self.assertEqual(hijo["ID del padre"], "CRM GDL 01 02 03")

    def test_mantenimientos(self):
        mantenimientos = filas(self.libro["Mantenimientos"])
        self.assertEqual(len(mantenimientos), 3)
        self.assertEqual({m["ID interno del equipo"] for m in mantenimientos}, {"CRM GDL 01 02 03"})
        self.assertEqual(mantenimientos[0]["Fecha"], "2026-01-10")    # más reciente primero
        self.assertEqual(mantenimientos[2]["Realizado por"], "Técnico externo")

    def test_texto_nunca_es_formula(self):
        self.assertNotIn(b"<f>", xml_del_excel(self.datos))
        nota = self.libro["Equipos"].cell(row=2, column=15)
        self.assertEqual(nota.data_type, "s")
        self.assertTrue(nota.value.startswith('=HYPERLINK('))
        descripcion = self.libro["Mantenimientos"].cell(row=4, column=7)
        self.assertEqual((descripcion.value, descripcion.data_type), ("=1+1", "s"))

    def test_quita_caracteres_de_control_y_conserva_saltos(self):
        nota = self.libro["Equipos"].cell(row=2, column=15).value
        self.assertNotIn("\x01", nota)
        self.assertIn("\nsegunda línea", nota)

    def test_sin_usuarios_ni_intentos(self):
        xml = xml_del_excel(self.datos)
        self.assertNotIn(HASH_PRUEBA.encode(), xml)
        self.assertNotIn(b"203.0.113.7", xml)
        for nombre in self.libro.sheetnames:
            self.assertNotIn("usuario", nombre.lower())
            self.assertNotIn("intento", nombre.lower())

    def test_informacion(self):
        info = dict(self.libro["Información"].iter_rows(values_only=True))
        self.assertEqual(info["Descargado por"], "diego")
        self.assertEqual((info["Equipos"], info["En Baja"], info["Mantenimientos"]), (3, 1, 3))
        self.assertIn("No sirve para restaurar", info["Aviso"])
        self.assertRegex(info["Generado el"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-06:00$")

    def test_encabezado_fijo_y_filtros(self):
        for nombre in ("Equipos", "Mantenimientos"):
            hoja = self.libro[nombre]
            self.assertEqual(hoja.freeze_panes, "A2")
            self.assertTrue(hoja.auto_filter.ref.startswith("A1:"))

    def test_base_vacia(self):
        with tempfile.TemporaryDirectory() as carpeta:
            vacia = db.conectar(os.path.join(carpeta, "vacia.db"))
            db.crear_tablas(vacia)
            datos = libro(respaldo.excel(vacia, "diego"))
            vacia.close()
        self.assertEqual(datos["Equipos"].max_row, 1)                 # solo el encabezado


class PruebasCopiaDb(BaseDatos):

    def test_copia_completa(self):
        datos = respaldo.copia_db(self.conexion)
        self.assertTrue(datos.startswith(b"SQLite format 3\x00"))
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "copia.db")
            with open(ruta, "wb") as archivo:
                archivo.write(datos)
            copia = sqlite3.connect(ruta)
            conteos = [copia.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                       for t in ("equipos", "mantenimientos", "usuarios", "intentos_entrada")]
            copia.close()
        self.assertEqual(conteos, [3, 3, 1, 1])        # el .db sí lleva usuarios (para restaurar)

    def test_no_deja_archivos_temporales(self):
        antes = set(os.listdir(tempfile.gettempdir()))
        respaldo.copia_db(self.conexion)
        nuevos = set(os.listdir(tempfile.gettempdir())) - antes
        self.assertFalse([n for n in nuevos if n.startswith("respaldo_")])


class PruebasNombreArchivo(unittest.TestCase):

    def test_nombre(self):
        momento = datetime(2026, 11, 6, 10, 45, tzinfo=config.ZONA_HORARIA)
        self.assertEqual(respaldo.nombre_archivo("xlsx", momento),
                         "respaldo_inventario_2026-11-06_1045.xlsx")
        self.assertEqual(respaldo.nombre_archivo("db", momento),
                         "respaldo_inventario_2026-11-06_1045.db")

    def test_hora_de_ciudad_de_mexico(self):
        nombre = respaldo.nombre_archivo("db")
        esperado = datetime.now(config.ZONA_HORARIA).strftime("%Y-%m-%d")
        self.assertIn(esperado, nombre)

    def test_extension_no_permitida(self):
        for extension in ("csv", ".xlsx", "", "db/../x"):
            with self.subTest(extension=extension), self.assertRaises(ValueError):
                respaldo.nombre_archivo(extension)


# --- Rutas ---------------------------------------------------------------------------------------

RUTAS = ("/respaldo", "/respaldo.xlsx", "/respaldo.db")
NOMBRE = r'attachment; filename=respaldo_inventario_\d{4}-\d{2}-\d{2}_\d{4}\.%s'


class PruebasRutasSinSesion(BaseApp):

    def test_todo_pide_sesion(self):
        for url in RUTAS:
            with self.subTest(url=url):
                respuesta = self.cliente.get(url)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta.headers["Location"].startswith("/entrar"))


class PruebasRutasRespaldo(BaseApp):

    def setUp(self):
        super().setUp()
        self.num = db.insertar_equipo(self.conexion(), {"tipo": "Zzrespaldo monitor",
                                                        "estatus": "Funcional"}, "prueba")
        self.entrar()

    def test_enlace_en_la_cabecera(self):
        self.assertIn('href="/respaldo">Respaldo</a>', self.cliente.get("/").get_data(as_text=True))

    def test_pagina(self):
        respuesta = self.cliente.get("/respaldo")
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('href="/respaldo.xlsx"', html)
        self.assertIn('href="/respaldo.db"', html)
        total = self.conexion().execute("SELECT COUNT(*) FROM equipos").fetchone()[0]
        self.assertIn(f"<strong>{total}</strong>", html)
        self.assertIn("contraseñas cifradas", html)

    def test_excel(self):
        respuesta = self.cliente.get("/respaldo.xlsx")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, TIPO_EXCEL)
        self.assertRegex(respuesta.headers["Content-Disposition"], NOMBRE % "xlsx")
        self.assertIn("no-store", respuesta.headers["Cache-Control"])
        equipos = filas(libro(respuesta.data)["Equipos"])
        self.assertIn("Zzrespaldo monitor", [e["Tipo"] for e in equipos])

    def test_db(self):
        respuesta = self.cliente.get("/respaldo.db")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "application/octet-stream")
        self.assertRegex(respuesta.headers["Content-Disposition"], NOMBRE % "db")
        self.assertIn("no-store", respuesta.headers["Cache-Control"])
        self.assertTrue(respuesta.data.startswith(b"SQLite format 3\x00"))

    def test_cabeceras_de_seguridad(self):
        for url in RUTAS:
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).headers["X-Content-Type-Options"], "nosniff")

    def test_solo_get(self):
        for url in RUTAS:
            with self.subTest(url=url):
                self.assertEqual(self.cliente.post(url).status_code, 405)


if __name__ == "__main__":
    unittest.main()
