"""
pruebas_etiquetas.py — Pruebas de qr.py, etiquetas.py y de las rutas del QR y las etiquetas
(chat 5).

Uso:  python3 -m unittest pruebas_etiquetas -v

Cada prueba usa una base de datos y una clave secreta temporales: no toca instancia/.

Las pruebas de lectura de vuelta (que el QR del PDF se escanee con el enlace exacto) solo
corren si están instalados zxing-cpp y pypdfium2 (no hacen falta para la app):
    pip install zxing-cpp pypdfium2
Sin ellos, esas pruebas aparecen como "skipped".
"""

import io
import re
import unittest
from datetime import timedelta
from unittest import mock

# pruebas_app cambia las rutas de config a una carpeta temporal antes de importar app.py.
from pruebas_app import BaseApp

import config  # noqa: E402
import db  # noqa: E402
import etiquetas  # noqa: E402
import qr  # noqa: E402

try:
    import pypdfium2
    import zxingcpp
    from PIL import Image
    PUEDE_LEER = True
except ImportError:
    PUEDE_LEER = False

CODIGO = "k7q2xpm4"
PUNTOS_POR_MM = 72 / 25.4


def equipo_prueba(**datos):
    """Equipo como lo devuelve la base (solo los campos que usan qr.py y etiquetas.py)."""
    base = {"num": 1, "codigo": CODIGO, "id_interno": "CRM GDL 06 01 10", "estatus": "Funcional",
            "area": "Urgencias"}
    base.update(datos)
    return base


def paginas(pdf):
    """Tamaño (ancho, alto) en mm de cada página de un PDF hecho con reportlab."""
    cajas = re.findall(rb"/MediaBox \[ 0 0 ([\d.]+) ([\d.]+) \]", pdf)
    return [(round(float(a) / PUNTOS_POR_MM, 1), round(float(b) / PUNTOS_POR_MM, 1))
            for a, b in cajas]


def leer_qr_pdf(pdf, ppp=300):
    """Enlaces de los QR que se leen en la primera página del PDF."""
    pagina = pypdfium2.PdfDocument(pdf)[0]
    imagen = pagina.render(scale=ppp / 72, grayscale=True).to_pil()
    return [r.text for r in zxingcpp.read_barcodes(imagen, formats=zxingcpp.BarcodeFormat.QRCode)]


# --- qr.py ---------------------------------------------------------------------------------------

class PruebasQr(unittest.TestCase):

    def test_enlace(self):
        enlace = qr.enlace_equipo(CODIGO)
        self.assertEqual(enlace, "https://bi0medic4crm.pythonanywhere.com/e/k7q2xpm4")
        self.assertEqual(len(enlace), 50)
        self.assertEqual(qr.enlace_equipo(" K7Q2XPM4 "), enlace)      # mayúsculas → minúsculas

    def test_enlace_codigo_no_valido(self):
        for codigo in ("", None, "k7q2xpm", "k7q2xpm40", "k7q2xpm0", "k7q2/pm4"):
            with self.subTest(codigo=codigo), self.assertRaises(ValueError):
                qr.enlace_equipo(codigo)

    def test_version_4_para_todos(self):
        # El enlace siempre mide lo mismo: todos los QR son versión 4 (33 módulos).
        for codigo in (CODIGO, "zzzzzzzz", "22222222"):
            with self.subTest(codigo=codigo):
                self.assertEqual(len(qr.matriz(qr.enlace_equipo(codigo))), 33)

    def test_png(self):
        datos = qr.png(qr.enlace_equipo(CODIGO))
        self.assertTrue(datos.startswith(b"\x89PNG"))
        if PUEDE_LEER:
            imagen = Image.open(io.BytesIO(datos))
            self.assertEqual(imagen.size, (410, 410))                # (33 + 2 × 4) × 10 px
            self.assertEqual([r.text for r in zxingcpp.read_barcodes(imagen)],
                             [qr.enlace_equipo(CODIGO)])


# --- etiquetas.py ----------------------------------------------------------------------------------

class PruebasMedidas(unittest.TestCase):

    def test_medidas_3_cm(self):
        m = etiquetas.calcular_medidas(33)
        self.assertEqual(m["tam_mm"], 30)
        self.assertGreaterEqual(m["modulo_mm"], etiquetas.MODULO_MIN_MM)
        self.assertGreaterEqual((m["tam_mm"] - m["qr_mm"]) / 2, m["zona_mm"])   # zona blanca a los lados
        self.assertEqual(etiquetas.etiquetas_por_hoja(), 48)                     # 6 × 8 en carta

    def test_qr_que_no_cabe(self):
        with mock.patch.object(config, "TAM_QR_CM", 2.6), self.assertRaises(ValueError):
            etiquetas.calcular_medidas(33)

    def test_modulo_demasiado_chico(self):
        with mock.patch.object(config, "TAM_QR_CM", 1.5), self.assertRaises(ValueError):
            etiquetas.calcular_medidas(33)


class PruebasQuienLlevaEtiqueta(unittest.TestCase):

    def test_motivos(self):
        casos = {
            etiquetas.MENSAJE_BAJA: [equipo_prueba(estatus="Baja"), equipo_prueba(estatus=" baja ")],
            etiquetas.MENSAJE_SIN_ID: [equipo_prueba(id_interno=None), equipo_prueba(id_interno="  ")],
            etiquetas.MENSAJE_ID_LARGO: [equipo_prueba(id_interno="W" * 40)],
            etiquetas.MENSAJE_ID_CARACTERES: [equipo_prueba(id_interno="ID ★ 1")],
        }
        for mensaje, equipos in casos.items():
            for equipo in equipos:
                with self.subTest(equipo=equipo):
                    self.assertEqual(etiquetas.motivo_sin_etiqueta(equipo), mensaje)

    def test_si_llevan(self):
        for datos in ({}, {"id_interno": "TMP-016"}, {"id_interno": "CRMG 023 4567 89"},
                      {"estatus": None}, {"estatus": "Prestado"}, {"estatus": "Fuera de Servicio"}):
            with self.subTest(datos=datos):
                self.assertIsNone(etiquetas.motivo_sin_etiqueta(equipo_prueba(**datos)))

    def test_letra_mas_chica_si_no_cabe(self):
        self.assertEqual(etiquetas.tamano_fuente("CRM GDL 06 01 10"), etiquetas.FUENTE_PT)
        self.assertLess(etiquetas.tamano_fuente("CRM GDL 06 01 10 XXX"), etiquetas.FUENTE_PT)

    def test_separar_y_ordenar(self):
        a = equipo_prueba(num=1, id_interno="B-2", area="Urgencias")
        b = equipo_prueba(num=2, id_interno="A-1", area="Urgencias")
        c = equipo_prueba(num=3, id_interno="Z-9", area=None)
        d = equipo_prueba(num=4, id_interno="C-3", area="Quirófano")
        sin_id = equipo_prueba(num=5, id_interno=None)
        imprimibles, excluidos = etiquetas.separar([a, b, c, d, sin_id])
        self.assertEqual(excluidos, [(sin_id, etiquetas.MENSAJE_SIN_ID)])
        orden = etiquetas.ordenar_para_imprimir(imprimibles)
        self.assertEqual([e["num"] for e in orden], [4, 2, 1, 3])     # Quirófano, Urgencias, sin área


class PruebasPdf(unittest.TestCase):

    def test_una_etiqueta_mide_3_cm(self):
        pdf = etiquetas.pdf_una(equipo_prueba())
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(paginas(pdf), [(30.0, 30.0)])

    def test_hoja_carta(self):
        equipos = [equipo_prueba(num=i, id_interno=f"ID-{i}") for i in range(49)]
        pdf = etiquetas.pdf_hoja(equipos)
        self.assertEqual(paginas(pdf), [(215.9, 279.4)] * 2)            # 48 + 1

    def test_no_genera_si_no_lleva_etiqueta(self):
        with self.assertRaises(etiquetas.ErrorEtiqueta):
            etiquetas.pdf_una(equipo_prueba(estatus="Baja"))
        with self.assertRaises(etiquetas.ErrorEtiqueta):
            etiquetas.pdf_hoja([])
        with self.assertRaisesRegex(etiquetas.ErrorEtiqueta, "número 7"):
            etiquetas.pdf_hoja([equipo_prueba(), equipo_prueba(num=7, id_interno=None)])

    @unittest.skipUnless(PUEDE_LEER, "requiere zxing-cpp y pypdfium2")
    def test_el_qr_del_pdf_se_lee(self):
        enlace = qr.enlace_equipo(CODIGO)
        self.assertEqual(leer_qr_pdf(etiquetas.pdf_una(equipo_prueba())), [enlace])
        # En la hoja carta, a 150 ppp (más o menos lo que ve la cámara de un teléfono).
        otros = [equipo_prueba(num=i, codigo=c, id_interno=f"ID-{i}")
                 for i, c in enumerate(("22222222", "zzzzzzzz", "abcdefgh"))]
        leidos = leer_qr_pdf(etiquetas.pdf_hoja(otros), ppp=150)
        self.assertEqual(sorted(leidos), sorted(qr.enlace_equipo(e["codigo"]) for e in otros))

    @unittest.skipUnless(PUEDE_LEER, "requiere zxing-cpp y pypdfium2")
    def test_el_id_va_en_el_pdf(self):
        pagina = pypdfium2.PdfDocument(etiquetas.pdf_una(equipo_prueba()))[0]
        self.assertEqual(pagina.get_textpage().get_text_range().strip(), "CRM GDL 06 01 10")


# --- Rutas ---------------------------------------------------------------------------------------

class BaseEtiquetas(BaseApp):
    """Crea sus propios equipos (con la palabra "zzetiqueta" en el tipo, para filtrarlos)."""

    def setUp(self):
        super().setUp()
        conexion = self.conexion()

        def alta(**datos):
            num = db.insertar_equipo(conexion, datos, "prueba")
            return num, db.obtener_equipo_por_num(conexion, num)["codigo"]

        self.num_activo, self.cod_activo = alta(
            tipo="Zzetiqueta monitor", id_interno="ZZ GDL 01", estatus="Funcional", area="Terapia")
        self.num_otro, _ = alta(tipo="Zzetiqueta bomba", id_interno="ZZ GDL 02",
                                estatus="En Revisión", area="Quirófano")
        self.num_sin_id, self.cod_sin_id = alta(tipo="Zzetiqueta sensor", estatus="Funcional")
        self.num_baja, self.cod_baja = alta(tipo="Zzetiqueta viejo", id_interno="ZZ GDL 99",
                                            estatus="Baja")


class PruebasRutasSinSesion(BaseEtiquetas):

    def test_todo_pide_sesion(self):
        for url in (f"/equipo/{self.num_activo}/etiqueta", f"/equipo/{self.num_activo}/qr.png",
                    f"/equipo/{self.num_activo}/etiqueta.pdf", "/etiquetas", "/etiquetas.pdf"):
            with self.subTest(url=url):
                respuesta = self.cliente.get(url)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta.headers["Location"].startswith("/entrar"))

    def test_ficha_publica_sin_boton(self):
        html = self.cliente.get(f"/e/{self.cod_activo}").get_data(as_text=True)
        self.assertNotIn("QR / etiqueta", html)


class PruebasEtiquetaDeUnEquipo(BaseEtiquetas):

    def setUp(self):
        super().setUp()
        self.entrar()

    def test_boton_en_la_ficha(self):
        html = self.cliente.get(f"/e/{self.cod_activo}").get_data(as_text=True)
        self.assertIn(f'href="/equipo/{self.num_activo}/etiqueta">QR / etiqueta', html)
        # Sin ID también aparece (la pantalla explica qué falta); en Baja no.
        self.assertIn("QR / etiqueta", self.cliente.get(f"/e/{self.cod_sin_id}").get_data(as_text=True))
        self.assertNotIn("QR / etiqueta", self.cliente.get(f"/e/{self.cod_baja}").get_data(as_text=True))

    def test_pantalla(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_activo}/etiqueta")
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(f'src="/equipo/{self.num_activo}/qr.png"', html)
        self.assertIn(qr.enlace_equipo(self.cod_activo), html)
        self.assertIn(f'href="/equipo/{self.num_activo}/etiqueta.pdf"', html)
        self.assertIn(f'href="/equipo/{self.num_activo}/etiqueta.pdf?hoja=carta"', html)

    def test_pantalla_sin_id_y_en_baja(self):
        for num, mensaje in ((self.num_sin_id, "no tiene ID interno"), (self.num_baja, "Baja")):
            with self.subTest(num=num):
                html = self.cliente.get(f"/equipo/{num}/etiqueta").get_data(as_text=True)
                self.assertIn(mensaje, html)
                self.assertNotIn("qr.png", html)
                self.assertNotIn("etiqueta.pdf", html)
                self.assertIn(f'href="/equipo/{num}/editar"', html)

    def test_equipo_inexistente(self):
        for url in ("/equipo/9999/etiqueta", "/equipo/9999/qr.png", "/equipo/9999/etiqueta.pdf",
                    "/equipo/abc/etiqueta"):
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).status_code, 404)

    def test_png(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_activo}/qr.png")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "image/png")
        self.assertIn("no-store", respuesta.headers["Cache-Control"])
        self.assertTrue(respuesta.data.startswith(b"\x89PNG"))

    def test_pdf_de_una(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_activo}/etiqueta.pdf")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "application/pdf")
        self.assertIn("inline", respuesta.headers["Content-Disposition"])
        self.assertIn("etiqueta_ZZ_GDL_01.pdf", respuesta.headers["Content-Disposition"])
        self.assertEqual(paginas(respuesta.data), [(30.0, 30.0)])

    def test_pdf_de_una_en_carta(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_activo}/etiqueta.pdf?hoja=carta")
        self.assertEqual(paginas(respuesta.data), [(215.9, 279.4)])
        self.assertIn("etiqueta_ZZ_GDL_01_carta.pdf", respuesta.headers["Content-Disposition"])

    def test_sin_id_y_en_baja_no_genera_nada(self):
        for num in (self.num_sin_id, self.num_baja):
            for url in (f"/equipo/{num}/qr.png", f"/equipo/{num}/etiqueta.pdf",
                        f"/equipo/{num}/etiqueta.pdf?hoja=carta"):
                with self.subTest(url=url):
                    respuesta = self.cliente.get(url)
                    self.assertEqual(respuesta.status_code, 409)
                    self.assertEqual(respuesta.mimetype, "text/html")

    def test_cabeceras_de_seguridad(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_activo}/etiqueta.pdf")
        self.assertEqual(respuesta.headers["X-Content-Type-Options"], "nosniff")


class PruebasVariasEtiquetas(BaseEtiquetas):

    def setUp(self):
        super().setUp()
        self.entrar()

    def test_boton_en_la_busqueda(self):
        html = self.cliente.get("/?q=zzetiqueta&area=Terapia").get_data(as_text=True)
        self.assertIn('href="/etiquetas?q=zzetiqueta&amp;area=Terapia"', html)
        self.assertNotIn("Imprimir etiquetas", self.cliente.get("/?q=nadaquecoincida").get_data(as_text=True))

    def test_resumen(self):
        respuesta = self.cliente.get("/etiquetas?q=zzetiqueta")
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("2 etiquetas", html)
        self.assertIn("1 hoja carta", html)
        self.assertIn('href="/etiquetas.pdf?q=zzetiqueta"', html)
        self.assertIn("Sin etiqueta (1)", html)                     # el que no tiene ID
        self.assertIn(f'href="/e/{self.cod_sin_id}"', html)
        self.assertNotIn(f'href="/e/{self.cod_baja}"', html)          # la búsqueda oculta Baja

    def test_resumen_de_bajas(self):
        html = self.cliente.get("/etiquetas?q=zzetiqueta&estatus=Baja").get_data(as_text=True)
        self.assertIn("Ningún equipo de esta búsqueda puede llevar etiqueta", html)
        self.assertNotIn("etiquetas.pdf", html)
        self.assertIn(etiquetas.MENSAJE_BAJA, html)

    def test_pdf(self):
        respuesta = self.cliente.get("/etiquetas.pdf?q=zzetiqueta")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "application/pdf")
        self.assertEqual(paginas(respuesta.data), [(215.9, 279.4)])
        self.assertIn(f"etiquetas_{db.hoy().isoformat()}.pdf", respuesta.headers["Content-Disposition"])

    @unittest.skipUnless(PUEDE_LEER, "requiere zxing-cpp y pypdfium2")
    def test_pdf_solo_lleva_los_imprimibles_por_area(self):
        datos = self.cliente.get("/etiquetas.pdf?q=zzetiqueta&baja=1").data
        texto = pypdfium2.PdfDocument(datos)[0].get_textpage().get_text_range()
        self.assertLess(texto.index("ZZ GDL 02"), texto.index("ZZ GDL 01"))   # Quirófano antes que Terapia
        self.assertNotIn("ZZ GDL 99", texto)                                   # Baja, aunque se pida baja=1

    def test_pdf_sin_imprimibles(self):
        for url in ("/etiquetas.pdf?q=zzetiqueta+sensor", "/etiquetas.pdf?q=zzetiqueta&estatus=Baja"):
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).status_code, 409)


class PruebasConfig(BaseApp):

    def test_horas_sesion_desde_config(self):
        self.assertEqual(self.app.config["PERMANENT_SESSION_LIFETIME"],
                         timedelta(hours=config.HORAS_SESION))


if __name__ == "__main__":
    unittest.main()
