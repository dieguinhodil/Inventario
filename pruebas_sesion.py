"""
pruebas_sesion.py — Pruebas de auth.py, crear_usuario.py y de los cambios a db.py del chat 4
(bloqueo por IP con MAX_INTENTOS_IP y cambiar_contrasena).

Uso:  python3 -m unittest pruebas_sesion -v

Cada prueba usa una base de datos y una clave secreta temporales: no toca instancia/.
"""

import io
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path

# pruebas_app cambia las rutas de config a una carpeta temporal antes de importar app.py.
from pruebas_app import CONTRASENA, BaseApp, aplicacion, hash_rapido

import auth  # noqa: E402
import config  # noqa: E402
import crear_usuario  # noqa: E402
import db  # noqa: E402


def contar_intentos(conexion):
    return conexion.execute("SELECT COUNT(*) FROM intentos_entrada").fetchone()[0]


# --- db.py ------------------------------------------------------------------------------------

class PruebasBloqueoDb(unittest.TestCase):

    def setUp(self):
        self.conexion = db.conectar(":memory:")
        db.crear_tablas(self.conexion)

    def tearDown(self):
        self.conexion.close()

    def fallar(self, usuario, ip, veces):
        for _ in range(veces):
            db.registrar_intento(self.conexion, usuario, ip, False)

    def test_usuario_se_bloquea_con_max_intentos(self):
        self.fallar("diego", "1.1.1.1", config.MAX_INTENTOS - 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "diego", "9.9.9.9"), 0)
        self.fallar("diego", "1.1.1.1", 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "diego", "9.9.9.9"),
                         config.MINUTOS_BLOQUEO)

    def test_ip_compartida_no_se_bloquea_con_max_intentos(self):
        # Varios usuarios fallan desde la misma IP: con MAX_INTENTOS fallos la IP sigue libre.
        for i in range(config.MAX_INTENTOS):
            self.fallar(f"usuario{i}", "1.1.1.1", 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "jefatura", "1.1.1.1"), 0)

    def test_ip_se_bloquea_con_max_intentos_ip(self):
        for i in range(config.MAX_INTENTOS_IP - 1):
            self.fallar(f"usuario{i}", "1.1.1.1", 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "jefatura", "1.1.1.1"), 0)
        self.fallar("otro", "1.1.1.1", 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "jefatura", "1.1.1.1"),
                         config.MINUTOS_BLOQUEO)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "jefatura", "2.2.2.2"), 0)

    def test_exito_reinicia_ip(self):
        for i in range(config.MAX_INTENTOS_IP - 1):
            self.fallar(f"usuario{i}", "1.1.1.1", 1)
        db.registrar_intento(self.conexion, "diego", "1.1.1.1", True)
        self.fallar("otro", "1.1.1.1", 1)
        self.assertEqual(db.minutos_bloqueado(self.conexion, "jefatura", "1.1.1.1"), 0)

    def test_fallos_viejos_no_cuentan(self):
        viejo = "2020-01-01T10:00:00-06:00"
        for _ in range(config.MAX_INTENTOS):
            self.conexion.execute("INSERT INTO intentos_entrada (usuario, ip, fecha_hora, exitoso) "
                                  "VALUES ('diego', '1.1.1.1', ?, 0)", (viejo,))
        self.assertEqual(db.minutos_bloqueado(self.conexion, "diego", "1.1.1.1"), 0)


class PruebasCambiarContrasenaDb(unittest.TestCase):

    def setUp(self):
        self.conexion = db.conectar(":memory:")
        db.crear_tablas(self.conexion)
        db.crear_usuario(self.conexion, "diego", "Diego", "hash-viejo")

    def tearDown(self):
        self.conexion.close()

    def test_cambia_el_hash(self):
        db.cambiar_contrasena(self.conexion, "DIEGO", "hash-nuevo")   # sin distinguir mayúsculas
        self.assertEqual(db.obtener_usuario(self.conexion, "diego")["hash_contrasena"], "hash-nuevo")

    def test_usuario_inexistente(self):
        with self.assertRaises(db.ErrorDatos):
            db.cambiar_contrasena(self.conexion, "nadie", "hash-nuevo")

    def test_hash_vacio(self):
        with self.assertRaises(db.ErrorDatos):
            db.cambiar_contrasena(self.conexion, "diego", "")


# --- auth.py sin peticiones -------------------------------------------------------------------

class PruebasAuthUtilidades(unittest.TestCase):

    def test_validar_contrasena_nueva(self):
        buena = "una-frase-larga-segura"
        auth.validar_contrasena_nueva(buena, buena, "diego")       # no lanza error
        casos = {
            "no coinciden": (buena, buena + "x"),
            "corta": ("corta123", "corta123"),
            "larga": ("x" * 129, "x" * 129),
            "espacios": (" " + buena, " " + buena),
            "usuario": ("soy-Diego-12345", "soy-Diego-12345"),
        }
        for motivo, (contrasena, confirmacion) in casos.items():
            with self.subTest(motivo=motivo), self.assertRaises(db.ErrorDatos):
                auth.validar_contrasena_nueva(contrasena, confirmacion, "diego")

    def test_destino_seguro(self):
        for destino in ("/", "/?q=monitor", "/e/k7q2xpm4", "/equipo/3/editar"):
            with self.subTest(destino=destino):
                self.assertTrue(auth.destino_seguro(destino))
        for destino in ("", "https://otro.com", "//otro.com", "/\\otro.com", "otro",
                        "javascript:alert(1)", "/\nx", "/" + "a" * 600, None):
            with self.subTest(destino=destino):
                self.assertFalse(auth.destino_seguro(destino))


class PruebasIpCliente(unittest.TestCase):

    def crear(self, produccion):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = Path(carpeta.name)
        return aplicacion.crear_app({"RUTA_DB": ruta / "p.db", "RUTA_CLAVE_SECRETA": ruta / "c.txt",
                                     "ES_PRODUCCION": produccion})

    def test_produccion_usa_x_real_ip(self):
        app = self.crear(True)
        with app.test_request_context(headers={"X-Real-IP": "201.1.2.3"},
                                      environ_base={"REMOTE_ADDR": "10.0.0.1"}):
            self.assertEqual(auth.ip_cliente(), "201.1.2.3")
        with app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.1"}):
            self.assertEqual(auth.ip_cliente(), "10.0.0.1")     # sin la cabecera

    def test_laptop_ignora_x_real_ip(self):
        app = self.crear(False)
        with app.test_request_context(headers={"X-Real-IP": "201.1.2.3"},
                                      environ_base={"REMOTE_ADDR": "127.0.0.1"}):
            self.assertEqual(auth.ip_cliente(), "127.0.0.1")


# --- Inicio y cierre de sesión ------------------------------------------------------------------

class PruebasEntrar(BaseApp):

    def test_busqueda_sin_sesion_manda_a_entrar(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers["Location"], "/entrar")

    def test_vuelve_a_la_pagina_pedida(self):
        respuesta = self.cliente.get("/?q=monitor")
        self.assertIn("/entrar?siguiente=", respuesta.headers["Location"])
        html = self.cliente.get(respuesta.headers["Location"]).get_data(as_text=True)
        self.assertIn('name="siguiente" value="/?q=monitor"', html)
        respuesta = self.cliente.post("/entrar", data={"usuario": "diego", "contrasena": CONTRASENA,
                                                       "siguiente": "/?q=monitor"})
        self.assertEqual(respuesta.headers["Location"], "/?q=monitor")

    def test_siguiente_externo_se_ignora(self):
        respuesta = self.cliente.post("/entrar", data={"usuario": "diego", "contrasena": CONTRASENA,
                                                       "siguiente": "https://otro.com/"})
        self.assertEqual(respuesta.headers["Location"], "/")

    def test_entrar_y_salir(self):
        respuesta = self.entrar()
        self.assertEqual(respuesta.status_code, 302)
        html = self.cliente.get("/").get_data(as_text=True)
        self.assertIn("Salir", html)
        self.assertIn('class="cabecera-marca cabecera-enlace" href="/"', html)   # logo → búsqueda
        self.assertIn('aria-label="Ir a la búsqueda"', html)
        respuesta = self.cliente.post("/salir")
        self.assertEqual(respuesta.headers["Location"], "/entrar")
        self.assertEqual(self.cliente.get("/").status_code, 302)
        self.assertIn("Sesión cerrada", self.cliente.get("/entrar").get_data(as_text=True))

    def test_salir_solo_con_post(self):
        self.entrar()
        self.assertEqual(self.cliente.get("/salir").status_code, 405)
        self.assertEqual(self.cliente.get("/").status_code, 200)     # sigue con sesión

    def test_usuario_sin_distinguir_mayusculas(self):
        self.assertEqual(self.entrar(usuario=" DIEGO ").status_code, 302)

    def test_contrasena_incorrecta_y_usuario_inexistente_dan_el_mismo_mensaje(self):
        for usuario in ("diego", "nadie"):
            with self.subTest(usuario=usuario):
                respuesta = self.entrar(usuario=usuario, contrasena="equivocada-123")
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("Usuario o contraseña incorrectos.", respuesta.get_data(as_text=True))
        self.assertEqual(contar_intentos(self.conexion()), 2)

    def test_campos_vacios_no_registran_intento(self):
        respuesta = self.entrar(usuario="", contrasena="")
        self.assertIn("Escribe tu usuario", respuesta.get_data(as_text=True))
        self.assertEqual(contar_intentos(self.conexion()), 0)

    def test_bloqueo_por_usuario(self):
        for _ in range(config.MAX_INTENTOS):
            html = self.entrar(contrasena="equivocada-123").get_data(as_text=True)
        self.assertIn("Demasiados intentos", html)
        intentos = contar_intentos(self.conexion())
        # Bloqueado: ni con la contraseña correcta entra, y el intento no se registra.
        html = self.entrar().get_data(as_text=True)
        self.assertIn("Demasiados intentos", html)
        self.assertEqual(contar_intentos(self.conexion()), intentos)
        # Desde la misma IP, el otro usuario sí puede entrar.
        self.assertEqual(self.entrar(usuario="jefatura").status_code, 302)

    def test_ya_con_sesion_entrar_redirige(self):
        self.entrar()
        self.assertEqual(self.cliente.get("/entrar").status_code, 302)

    def test_usuario_muy_largo(self):
        respuesta = self.entrar(usuario="x" * 500)
        self.assertIn("incorrectos", respuesta.get_data(as_text=True))
        self.assertEqual(contar_intentos(self.conexion()), 0)

    def test_usuario_borrado_pierde_la_sesion(self):
        self.entrar()
        conexion = self.conexion()
        with conexion:
            conexion.execute("DELETE FROM usuarios WHERE usuario = 'diego'")
        self.assertEqual(self.cliente.get("/").status_code, 302)

    def test_post_sin_sesion_avisa(self):
        respuesta = self.cliente.post("/equipo/1/editar", data={"tipo": "X"})
        self.assertEqual(respuesta.headers["Location"], "/entrar")
        html = self.cliente.get("/entrar").get_data(as_text=True)
        self.assertIn("no se guardó", html)


class PruebasBloqueoPorIpEnProduccion(BaseApp):
    """En PythonAnywhere todos llegan con la misma remote_addr; la IP real viene en X-Real-IP."""

    def setUp(self):
        super().setUp()
        self.app.config["ES_PRODUCCION"] = True
        self.app.config["SESSION_COOKIE_SECURE"] = True
        self.cliente = self.app.test_client()

    def post(self, usuario, contrasena, ip):
        return self.cliente.post("/entrar", base_url="https://localhost",
                                 data={"usuario": usuario, "contrasena": contrasena},
                                 headers={"X-Real-IP": ip})

    def test_bloqueo_por_ip_real(self):
        for i in range(config.MAX_INTENTOS_IP):
            self.post(f"intruso{i}", "equivocada-123", "201.0.0.1")
        html = self.post("jefatura", CONTRASENA, "201.0.0.1").get_data(as_text=True)
        self.assertIn("Demasiados intentos", html)
        ips = {fila[0] for fila in self.conexion().execute("SELECT DISTINCT ip FROM intentos_entrada")}
        self.assertEqual(ips, {"201.0.0.1"})
        # Desde otra IP real (aunque remote_addr sea la misma) sí entra.
        self.assertEqual(self.post("jefatura", CONTRASENA, "189.0.0.2").status_code, 302)


class PruebasCsrf(BaseApp):

    csrf = True

    def test_post_sin_token_se_rechaza(self):
        respuesta = self.entrar()
        self.assertEqual(respuesta.status_code, 400)
        html = respuesta.get_data(as_text=True)
        self.assertIn("caducó", html)
        self.assertNotIn("CSRF", html)               # sin detalles técnicos

    def test_post_con_token_funciona(self):
        html = self.cliente.get("/entrar").get_data(as_text=True)
        token = html.split('name="csrf_token" value="')[1].split('"')[0]
        respuesta = self.cliente.post("/entrar", data={"usuario": "diego", "contrasena": CONTRASENA,
                                                       "csrf_token": token})
        self.assertEqual(respuesta.status_code, 302)


# --- Cambiar contraseña ---------------------------------------------------------------------------

class PruebasCambiarContrasena(BaseApp):

    NUEVA = "otra-frase-larga-456"

    def cambiar(self, actual=CONTRASENA, nueva=NUEVA, confirmacion=None):
        return self.cliente.post("/contrasena", data={
            "actual": actual, "nueva": nueva,
            "confirmacion": nueva if confirmacion is None else confirmacion})

    def test_pide_sesion(self):
        self.assertEqual(self.cliente.get("/contrasena").status_code, 302)

    def test_cambio_correcto_cierra_otras_sesiones(self):
        otro_dispositivo = self.app.test_client()
        otro_dispositivo.post("/entrar", data={"usuario": "diego", "contrasena": CONTRASENA})
        self.entrar()
        respuesta = self.cambiar()
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.cliente.get("/").status_code, 200)          # esta sigue abierta
        self.assertEqual(otro_dispositivo.get("/").status_code, 302)      # la otra se cerró
        self.cliente.post("/salir")
        self.assertEqual(self.entrar().status_code, 200)                  # la vieja ya no sirve
        self.assertEqual(self.entrar(contrasena=self.NUEVA).status_code, 302)

    def test_contrasena_actual_incorrecta_cuenta_como_intento(self):
        self.entrar()
        respuesta = self.cambiar(actual="equivocada-123")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("actual no es correcta", respuesta.get_data(as_text=True))
        fila = self.conexion().execute(
            "SELECT exitoso FROM intentos_entrada ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(fila[0], 0)

    def test_errores_de_la_nueva(self):
        self.entrar()
        casos = {"no coinciden": (self.NUEVA, "distinta-123456"),
                 "debe tener al menos": ("corta", "corta"),
                 "distinta de la actual": (CONTRASENA, CONTRASENA)}
        for mensaje, (nueva, confirmacion) in casos.items():
            with self.subTest(mensaje=mensaje):
                respuesta = self.cambiar(nueva=nueva, confirmacion=confirmacion)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn(mensaje, respuesta.get_data(as_text=True))

    def test_cambio_desde_la_consola_cierra_la_sesion(self):
        self.entrar()
        db.cambiar_contrasena(self.conexion(), "diego", hash_rapido(self.NUEVA))
        self.assertEqual(self.cliente.get("/").status_code, 302)


# --- crear_usuario.py ----------------------------------------------------------------------------

class PruebasCrearUsuario(unittest.TestCase):

    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.ruta_db = Path(carpeta.name) / "usuarios.db"

    def correr(self, argumentos, respuestas):
        respuestas = iter(respuestas)
        salida = io.StringIO()
        with redirect_stdout(salida), redirect_stderr(salida):
            codigo = crear_usuario.main(argumentos, pedir=lambda _texto: next(respuestas),
                                        ruta_db=self.ruta_db)
        return codigo, salida.getvalue()

    def usuario(self, nombre):
        with closing(db.conectar(self.ruta_db)) as conexion:
            return db.obtener_usuario(conexion, nombre)

    def test_crear(self):
        clave = "frase-larga-del-taller"
        codigo, salida = self.correr(["Diego", "Diego Ponce"], [clave, clave])
        self.assertEqual(codigo, 0, salida)
        fila = self.usuario("diego")
        self.assertEqual(fila["usuario"], "diego")          # se guarda en minúsculas
        self.assertEqual(fila["nombre"], "Diego Ponce")
        self.assertNotIn(clave, fila["hash_contrasena"])
        self.assertTrue(auth.check_password_hash(fila["hash_contrasena"], clave))

    def test_vuelve_a_pedir_si_no_sirve(self):
        clave = "frase-larga-del-taller"
        codigo, salida = self.correr(["diego", "Diego"], ["corta", "corta", clave, "otra",
                                                          clave, clave])
        self.assertEqual(codigo, 0)
        self.assertIn("al menos 12", salida)
        self.assertIn("no coinciden", salida)

    def test_repetido(self):
        clave = "frase-larga-del-taller"
        self.correr(["diego", "Diego"], [clave, clave])
        codigo, salida = self.correr(["diego", "Diego"], [clave, clave])
        self.assertEqual(codigo, 1)
        self.assertIn("Ya existe", salida)

    def test_nombres_no_validos(self):
        for usuario in ("di", "diego ponce", "dieguíto", "importacion", "x" * 31):
            with self.subTest(usuario=usuario):
                codigo, _ = self.correr([usuario, "Nombre"], [])
                self.assertEqual(codigo, 1)

    def test_falta_nombre(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            self.correr(["diego"], [])

    def test_cambiar(self):
        vieja, nueva = "frase-larga-del-taller", "otra-frase-larga-99"
        self.correr(["diego", "Diego"], [vieja, vieja])
        codigo, _ = self.correr(["--cambiar", "diego"], [nueva, nueva])
        self.assertEqual(codigo, 0)
        self.assertTrue(auth.check_password_hash(self.usuario("diego")["hash_contrasena"], nueva))

    def test_cambiar_inexistente(self):
        codigo, salida = self.correr(["--cambiar", "nadie"], [])
        self.assertEqual(codigo, 1)
        self.assertIn("No existe", salida)

    def test_cancelar(self):
        def cancelar(_texto):
            raise KeyboardInterrupt
        salida = io.StringIO()
        with redirect_stdout(salida), redirect_stderr(salida):
            codigo = crear_usuario.main(["diego", "Diego"], pedir=cancelar, ruta_db=self.ruta_db)
        self.assertEqual(codigo, 1)
        self.assertIsNone(self.usuario("diego"))


if __name__ == "__main__":
    unittest.main()