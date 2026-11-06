"""
pruebas_app.py — Pruebas de app.py: búsqueda, ficha y configuración.

Uso:  python3 -m unittest pruebas_app -v
Todas las pruebas de la app:  python3 -m unittest pruebas_app pruebas_sesion pruebas_edicion

Cada prueba usa una base de datos y una clave secreta temporales: no toca instancia/.
BaseApp también la usan pruebas_sesion.py y pruebas_edicion.py.
"""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import config

# Importar app.py crea la clave secreta y las tablas: que sea en una carpeta temporal, no en instancia/.
_INSTANCIA = tempfile.TemporaryDirectory()
config.CARPETA_INSTANCIA = Path(_INSTANCIA.name)
config.RUTA_DB = config.CARPETA_INSTANCIA / "inventario.db"
config.RUTA_CLAVE_SECRETA = config.CARPETA_INSTANCIA / "clave_secreta.txt"

import app as aplicacion  # noqa: E402  (después de cambiar las rutas de config)
import db  # noqa: E402

CONTRASENA = "contrasena-de-prueba-123"


def hash_rapido(contrasena):
    """Hash con pocas vueltas: las pruebas no necesitan uno lento."""
    return generate_password_hash(contrasena, method="pbkdf2:sha256:1000")


def crear_usuarios(conexion):
    db.crear_usuario(conexion, "diego", "Diego", hash_rapido(CONTRASENA))
    db.crear_usuario(conexion, "jefatura", "Jefatura de Biomédica", hash_rapido(CONTRASENA))


class BaseApp(unittest.TestCase):
    """Crea una base temporal con equipos y usuarios de ejemplo y una app que la usa.

    El token CSRF se apaga para poder mandar formularios desde las pruebas; las pruebas que
    revisan el CSRF lo prenden con `csrf = True`.
    """

    csrf = False

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        carpeta = Path(self.carpeta.name)
        self.ruta_db = carpeta / "prueba.db"
        conexion = db.conectar(self.ruta_db)
        db.crear_tablas(conexion)
        crear_usuarios(conexion)
        self.cargar_datos(conexion)
        conexion.close()

        self.app = aplicacion.crear_app({
            "RUTA_DB": self.ruta_db,
            "RUTA_CLAVE_SECRETA": carpeta / "clave.txt",
            "ES_PRODUCCION": False,
            "TESTING": True,
            "WTF_CSRF_ENABLED": self.csrf,
        })
        self.cliente = self.app.test_client()

    def entrar(self, usuario="diego", contrasena=CONTRASENA):
        return self.cliente.post("/entrar", data={"usuario": usuario, "contrasena": contrasena})

    def conexion(self):
        """Conexión a la base de la prueba (para revisar qué quedó guardado)."""
        conexion = db.conectar(self.ruta_db)
        self.addCleanup(conexion.close)
        return conexion

    def tearDown(self):
        self.carpeta.cleanup()

    def cargar_datos(self, conexion):
        nuevo = lambda **datos: db.insertar_equipo(conexion, datos, "prueba")
        self.num_ecg = nuevo(tipo="Electrocardiógrafo", marca="Edan", modelo="SE-3",
                             serie="ECG123", area="Urgencias", estatus="Funcional",
                             id_interno="CRM GDL 01 02 03")
        self.num_monitor = nuevo(tipo="Monitor de signos vitales", marca="Mindray",
                                 modelo="PM-7000", serie="S/D", area="Terapia",
                                 estatus="En Revisión", id_interno="TMP-001")
        self.num_otro_monitor = nuevo(tipo="Monitor de signos vitales", marca="Edan",
                                      modelo="M3", serie="MON555", area="Urgencias",
                                      estatus="Funcional")
        self.num_baja = nuevo(tipo="Desfibrilador", marca="Zoll", modelo="M Series",
                              serie="BAJA01", area="Urgencias", estatus="Baja")
        self.num_raro = nuevo(tipo="Aspirador", estatus="Prestado", area="Quirófano")
        self.num_cable = nuevo(tipo="Cable de paciente", marca="Mindray", serie="CAB9",
                               estatus="Funcional", padre_num=self.num_monitor,
                               notas="<script>alert(1)</script>\nSegunda línea")
        db.registrar_mantenimiento(conexion, self.num_ecg, "2025-01-15", "preventivo",
                                   "Calibración", "Proveedor Edan", "diego")
        db.registrar_mantenimiento(conexion, self.num_ecg, "2025-06-02", "correctivo",
                                   "Cambio de cable", "Técnico interno", "jefatura")
        self.codigos = {num: db.obtener_equipo_por_num(conexion, num)["codigo"]
                        for num in (self.num_ecg, self.num_monitor, self.num_otro_monitor,
                                    self.num_baja, self.num_raro, self.num_cable)}

    def html(self, url):
        respuesta = self.cliente.get(url)
        return respuesta, respuesta.get_data(as_text=True)


class PruebasFicha(BaseApp):

    def test_ficha_muestra_datos(self):
        respuesta, html = self.html(f"/e/{self.codigos[self.num_ecg]}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Electrocardiógrafo", html)
        self.assertIn("estatus-verde", html)
        self.assertIn("CRM GDL 01 02 03", html)
        self.assertIn("Delegación Guadalajara", html)
        self.assertIn("Cruz Roja Mexicana", html)

    def test_ultimo_preventivo_y_historial(self):
        _, html = self.html(f"/e/{self.codigos[self.num_ecg]}")
        self.assertIn("15 de enero de 2025", html)     # último preventivo
        self.assertIn("2 de junio de 2025", html)      # correctivo en el historial
        self.assertLess(html.index("2 de junio de 2025"), html.index("Calibración"))

    def test_sin_mantenimientos(self):
        _, html = self.html(f"/e/{self.codigos[self.num_monitor]}")
        self.assertIn("Sin registro", html)

    def test_codigo_en_mayusculas(self):
        respuesta = self.cliente.get(f"/e/{self.codigos[self.num_ecg].upper()}")
        self.assertEqual(respuesta.status_code, 200)

    def test_codigo_inexistente_o_invalido_da_404(self):
        for codigo in ("zzzzzzzz", "abc", "k7q2xpm0", "k7q2xpm4x", "%3Cscript%3E"):
            with self.subTest(codigo=codigo):
                respuesta, html = self.html(f"/e/{codigo}")
                self.assertEqual(respuesta.status_code, 404)
                self.assertIn("No encontrado", html)

    def test_aviso_id_temporal(self):
        _, html = self.html(f"/e/{self.codigos[self.num_monitor]}")
        self.assertIn("ID temporal", html)
        self.assertIn("estatus-ambar", html)
        _, html = self.html(f"/e/{self.codigos[self.num_ecg]}")
        self.assertNotIn("ID temporal", html)

    def test_sin_dato(self):
        _, html = self.html(f"/e/{self.codigos[self.num_monitor]}")
        self.assertNotIn("S/D", html)
        self.assertIn("Sin dato", html)

    def test_equipo_en_baja(self):
        respuesta, html = self.html(f"/e/{self.codigos[self.num_baja]}")
        self.assertEqual(respuesta.status_code, 200)        # la ficha de una Baja sí se abre
        self.assertIn("dado de baja", html)
        self.assertIn("estatus-rojo", html)

    def test_estatus_fuera_de_catalogo_es_gris(self):
        _, html = self.html(f"/e/{self.codigos[self.num_raro]}")
        self.assertIn("estatus-gris", html)

    def test_padre_y_componentes(self):
        _, html = self.html(f"/e/{self.codigos[self.num_monitor]}")
        self.assertIn("Componentes (1)", html)
        self.assertIn(f"/e/{self.codigos[self.num_cable]}", html)
        _, html = self.html(f"/e/{self.codigos[self.num_cable]}")
        self.assertIn("Componente de", html)
        self.assertIn(f"/e/{self.codigos[self.num_monitor]}", html)

    def test_notas_se_escapan(self):
        self.entrar()                             # las notas solo se ven con sesión
        _, html = self.html(f"/e/{self.codigos[self.num_cable]}")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_con_sesion_muestra_datos_internos(self):
        self.entrar()
        _, html = self.html(f"/e/{self.codigos[self.num_ecg]}")
        self.assertIn("Datos internos", html)
        self.assertIn("Realizado por: Proveedor Edan", html)
        self.assertIn("Registrado por: diego", html)
        self.assertIn(f"/equipo/{self.num_ecg}/editar", html)
        self.assertIn("Registrar mantenimiento", html)
        self.assertIn("Agregar componente", html)
        _, html = self.html(f"/e/{self.codigos[self.num_cable]}")
        self.assertIn("Segunda línea", html)       # notas
        self.assertNotIn("Agregar componente", html)   # un componente no tiene componentes
        _, html = self.html(f"/e/{self.codigos[self.num_baja]}")
        self.assertNotIn("Agregar componente", html)   # ni un equipo en Baja

    def test_sin_sesion_oculta_datos_internos(self):
        respuesta, html = self.html(f"/e/{self.codigos[self.num_ecg]}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("Datos internos", html)
        self.assertNotIn("diego", html)          # nombres de usuario de la app
        self.assertNotIn("jefatura", html)
        self.assertNotIn("Registrado por", html)
        self.assertNotIn("Realizado por", html)
        self.assertNotIn("Proveedor Edan", html)
        self.assertNotIn('href="/"', html)       # sin enlace a la búsqueda
        self.assertNotIn("/equipo/", html)       # sin botones de edición (ni el num)
        self.assertNotIn("Registrar mantenimiento", html)
        self.assertNotIn("Salir", html)
        self.assertIn("Calibración", html)       # el historial sí es público

    def test_sin_sesion_oculta_notas(self):
        _, html = self.html(f"/e/{self.codigos[self.num_cable]}")
        self.assertNotIn("Notas", html)
        self.assertNotIn("Segunda línea", html)
        self.assertNotIn("alert(1)", html)


class PruebasBusqueda(BaseApp):

    def setUp(self):
        super().setUp()
        self.entrar()

    def codigos_en(self, html):
        return {num for num, codigo in self.codigos.items() if f"/e/{codigo}" in html}

    def test_volver_regresa_a_la_ultima_busqueda(self):
        self.html("/?q=monitor&area=Terapia&baja=1")
        enlace = '<a href="/?area=Terapia&amp;baja=1&amp;q=monitor">← Volver a la búsqueda</a>'
        ficha = f"/e/{self.codigos[self.num_monitor]}"
        self.assertIn(enlace, self.html(ficha)[1])
        # Se conserva después de registrar un mantenimiento y en las demás pantallas.
        self.cliente.post(f"/equipo/{self.num_monitor}/mantenimiento",
                          data={"fecha": "2025-01-15", "tipo": "preventivo"})
        self.assertIn(enlace, self.html(ficha)[1])
        self.assertIn(enlace, self.html("/etiquetas?q=monitor&area=Terapia")[1])
        self.assertIn(enlace, self.html("/equipo/nuevo")[1])

    def test_volver_sin_filtros_despues_de_limpiar(self):
        self.html("/?q=monitor")
        self.html("/")
        self.assertIn('<a href="/">← Volver a la búsqueda</a>',
                      self.html(f"/e/{self.codigos[self.num_monitor]}")[1])

    def test_volver_no_sale_sin_sesion_y_se_borra_al_salir(self):
        self.html("/?q=monitor")
        self.cliente.post("/salir")
        html = self.html(f"/e/{self.codigos[self.num_monitor]}")[1]
        self.assertNotIn("Volver a la búsqueda", html)
        self.entrar()
        self.assertIn('<a href="/">← Volver a la búsqueda</a>',
                      self.html(f"/e/{self.codigos[self.num_monitor]}")[1])

    def test_sin_texto_muestra_todo_menos_baja(self):
        respuesta, html = self.html("/")
        self.assertEqual(respuesta.status_code, 200)
        esperados = set(self.codigos) - {self.num_baja}
        self.assertEqual(self.codigos_en(html), esperados)
        self.assertIn(f"{len(esperados)} equipos", html)

    def test_sin_acentos_ni_mayusculas(self):
        _, html = self.html("/?q=ELECTROCARDIOGRAFO")
        self.assertEqual(self.codigos_en(html), {self.num_ecg})
        self.assertIn("1 equipo", html)

    def test_varias_palabras(self):
        _, html = self.html("/?q=monitor+mindray")
        self.assertEqual(self.codigos_en(html), {self.num_monitor})

    def test_filtro_area(self):
        _, html = self.html("/?area=Urgencias")
        self.assertEqual(self.codigos_en(html), {self.num_ecg, self.num_otro_monitor})

    def test_incluir_baja(self):
        _, html = self.html("/?baja=1")
        self.assertIn(self.num_baja, self.codigos_en(html))

    def test_filtrar_por_estatus_baja(self):
        _, html = self.html("/?estatus=Baja")
        self.assertEqual(self.codigos_en(html), {self.num_baja})

    def test_estatus_fuera_de_catalogo_en_filtro(self):
        _, html = self.html("/")
        self.assertIn('<option value="Prestado"', html)
        self.assertEqual(html.count('<option value="Baja"'), 1)

    def test_filtros_quedan_seleccionados(self):
        _, html = self.html("/?q=edan&area=Urgencias&baja=1")
        self.assertIn('value="edan"', html)
        self.assertIn('<option value="Urgencias" selected', html)
        self.assertIn('value="1" checked', html)

    def test_texto_largo_y_comodines(self):
        respuesta, html = self.html("/?q=" + "a%25_ " * 500)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("0 equipos", html)

    def test_texto_se_escapa(self):
        _, html = self.html("/?q=%22%3E%3Cscript%3E")
        self.assertNotIn("<script>", html)

    def test_componente_marcado(self):
        _, html = self.html("/?q=cab9")
        self.assertIn(">Componente<", html)


class PruebasPresentacion(unittest.TestCase):

    def test_sin_dato(self):
        for valor in (None, "", "   ", "S/D", "n/a", "NA", "-", "--"):
            with self.subTest(valor=valor):
                self.assertEqual(aplicacion.sin_dato(valor), "Sin dato")
        self.assertEqual(aplicacion.sin_dato(" Mindray "), "Mindray")
        self.assertEqual(aplicacion.sin_dato(12), "12")
        self.assertEqual(aplicacion.sin_dato("NAD"), "NAD")

    def test_fecha_larga(self):
        self.assertEqual(aplicacion.fecha_larga("2025-01-15"), "15 de enero de 2025")
        self.assertEqual(aplicacion.fecha_larga("2026-12-01"), "1 de diciembre de 2026")
        self.assertEqual(aplicacion.fecha_larga(None), "Sin registro")
        self.assertEqual(aplicacion.fecha_larga("", "Sin dato"), "Sin dato")
        self.assertEqual(aplicacion.fecha_larga("no es fecha"), "no es fecha")

    def test_fecha_y_hora_en_ciudad_de_mexico(self):
        self.assertEqual(aplicacion.fecha_larga("2026-10-29T16:45:00-06:00"),
                         "29 de octubre de 2026, 16:45")
        # Una hora en UTC se muestra en hora de Ciudad de México.
        self.assertEqual(aplicacion.fecha_larga("2026-10-30T02:00:00+00:00"),
                         "29 de octubre de 2026, 20:00")

    def test_clase_estatus(self):
        casos = {"Funcional": "verde", "En Revisión": "ambar", "en revision": "ambar",
                 "En Mantenimiento": "ambar", "Fuera de Servicio": "rojo",
                 "No Funcional": "rojo", "Baja": "rojo", "Prestado": "gris", None: "gris"}
        for estatus, clase in casos.items():
            with self.subTest(estatus=estatus):
                self.assertEqual(aplicacion.clase_estatus(estatus), clase)

    def test_es_tmp_y_es_baja(self):
        self.assertTrue(aplicacion.es_tmp("TMP-004"))
        self.assertTrue(aplicacion.es_tmp("tmp-004"))
        self.assertFalse(aplicacion.es_tmp("CRM GDL 01 02 03"))
        self.assertFalse(aplicacion.es_tmp(None))
        self.assertTrue(db.es_baja("Baja"))
        self.assertTrue(db.es_baja(" BAJA "))
        self.assertFalse(db.es_baja("Funcional"))
        self.assertFalse(db.es_baja(None))


class PruebasConfiguracion(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = Path(self.carpeta.name)

    def tearDown(self):
        self.carpeta.cleanup()

    def crear(self, **ajustes):
        base = {"RUTA_DB": self.ruta / "prueba.db",
                "RUTA_CLAVE_SECRETA": self.ruta / "instancia" / "clave.txt",
                "ES_PRODUCCION": False}
        base.update(ajustes)
        return aplicacion.crear_app(base)

    def test_clave_secreta_se_crea_una_vez(self):
        ruta = self.ruta / "instancia" / "clave.txt"
        primera = aplicacion.cargar_clave_secreta(ruta)
        self.assertEqual(len(primera), 64)
        self.assertEqual(aplicacion.cargar_clave_secreta(ruta), primera)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(ruta.stat().st_mode), 0o600)

    def test_clave_secreta_vacia_falla(self):
        ruta = self.ruta / "clave.txt"
        ruta.write_text("\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            aplicacion.cargar_clave_secreta(ruta)

    def test_produccion_arranca(self):
        # Ya hay inicio de sesión: el candado del chat 3 se quitó y la app arranca en producción.
        app = self.crear(ES_PRODUCCION=True)
        self.assertNotIn("SESION_PROVISIONAL", app.config)

    def test_cookie_de_sesion(self):
        app = self.crear()
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertFalse(app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(app.config["PERMANENT_SESSION_LIFETIME"].total_seconds(), 12 * 3600)
        app = self.crear(ES_PRODUCCION=True)
        self.assertTrue(app.config["SESSION_COOKIE_SECURE"])

    def test_csrf_activo(self):
        app = self.crear()
        self.assertIn("csrf", app.extensions)
        self.assertIsNone(app.config["WTF_CSRF_TIME_LIMIT"])   # dura lo que la sesión, no 1 hora

    def test_base_nueva_vacia_funciona(self):
        cliente = self.crear().test_client()
        conexion = db.conectar(self.ruta / "prueba.db")
        crear_usuarios(conexion)
        conexion.close()
        cliente.post("/entrar", data={"usuario": "diego", "contrasena": CONTRASENA,
                                      "csrf_token": self.token(cliente)})
        respuesta = cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("0 equipos", respuesta.get_data(as_text=True))

    def token(self, cliente):
        """Token CSRF de la página de entrada (aquí el CSRF está prendido)."""
        html = cliente.get("/entrar").get_data(as_text=True)
        return html.split('name="csrf_token" value="')[1].split('"')[0]

    def test_cabeceras_de_seguridad(self):
        respuesta = self.crear().test_client().get("/entrar")
        self.assertEqual(respuesta.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(respuesta.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", respuesta.headers["Content-Security-Policy"])

    def test_estilos_se_sirven(self):
        respuesta = self.crear().test_client().get("/static/estilos.css")
        self.assertEqual(respuesta.status_code, 200)
        respuesta.close()

    def test_interruptor_de_tema(self):
        cliente = self.crear().test_client()
        html = cliente.get("/entrar").get_data(as_text=True)
        self.assertIn('id="interruptor-tema"', html)
        self.assertIn('src="/static/tema.js"', html)     # archivo aparte: la política no permite <script> en línea
        respuesta = cliente.get("/static/tema.js")
        self.assertEqual(respuesta.status_code, 200)
        respuesta.close()


if __name__ == "__main__":
    unittest.main()