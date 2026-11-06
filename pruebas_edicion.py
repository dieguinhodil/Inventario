"""
pruebas_edicion.py — Pruebas de edición y alta de equipos y componentes, y del registro de
mantenimientos (chat 4).

Uso:  python3 -m unittest pruebas_edicion -v

Cada prueba usa una base de datos y una clave secreta temporales: no toca instancia/.
"""

import unittest
from datetime import timedelta

# pruebas_app cambia las rutas de config a una carpeta temporal antes de importar app.py.
from pruebas_app import BaseApp, aplicacion

import db  # noqa: E402


class BaseEdicion(BaseApp):

    def setUp(self):
        super().setUp()
        self.entrar()

    def equipo(self, num):
        return db.obtener_equipo_por_num(self.conexion(), num)

    def formulario(self, num, **cambios):
        """Datos actuales del equipo como los manda el formulario de edición, con `cambios`."""
        equipo = self.equipo(num)
        datos = {campo: "" if equipo[campo] is None else str(equipo[campo])
                 for campo in ("id_interno", "tipo", "marca", "modelo", "serie", "area",
                               "estatus", "notas", "padre_num")}
        datos["version"] = aplicacion.version_equipo(equipo)
        datos.update(cambios)
        return datos

    def editar(self, num, **cambios):
        return self.cliente.post(f"/equipo/{num}/editar", data=self.formulario(num, **cambios))


class PruebasSinSesion(BaseApp):

    def test_todo_pide_sesion(self):
        for metodo, url in (("get", "/equipo/nuevo"), ("get", f"/equipo/{self.num_ecg}/editar"),
                            ("post", "/equipo/nuevo"), ("post", f"/equipo/{self.num_ecg}/editar"),
                            ("post", f"/equipo/{self.num_ecg}/mantenimiento")):
            with self.subTest(url=url, metodo=metodo):
                respuesta = getattr(self.cliente, metodo)(url, data={"tipo": "Intruso"})
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta.headers["Location"].startswith("/entrar"))
        self.assertEqual(self.equipo_tipo(), "Electrocardiógrafo")
        self.assertEqual(len(db.listar_mantenimientos(self.conexion(), self.num_ecg)), 2)

    def equipo_tipo(self):
        return db.obtener_equipo_por_num(self.conexion(), self.num_ecg)["tipo"]


class PruebasEditar(BaseEdicion):

    def test_pantalla_muestra_los_datos(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_ecg}/editar")
        html = respuesta.get_data(as_text=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('value="CRM GDL 01 02 03"', html)
        self.assertIn('<option value="Funcional" selected', html)
        self.assertIn('name="version"', html)
        self.assertIn('<datalist id="lista-areas">', html)

    def test_equipo_inexistente(self):
        self.assertEqual(self.cliente.get("/equipo/9999/editar").status_code, 404)

    def test_guardar_cambios(self):
        respuesta = self.editar(self.num_ecg, area=" Terapia ", serie="ECG999")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.headers["Location"], f"/e/{self.codigos[self.num_ecg]}")
        equipo = self.equipo(self.num_ecg)
        self.assertEqual(equipo["area"], "Terapia")
        self.assertEqual(equipo["serie"], "ECG999")
        self.assertEqual(equipo["actualizado_por"], "diego")
        html = self.cliente.get(respuesta.headers["Location"]).get_data(as_text=True)
        self.assertIn("Cambios guardados", html)

    def test_sin_cambios_no_toca_el_equipo(self):
        antes = self.equipo(self.num_ecg)["actualizado_en"]
        respuesta = self.editar(self.num_ecg)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.equipo(self.num_ecg)["actualizado_en"], antes)
        self.assertEqual(self.equipo(self.num_ecg)["actualizado_por"], "prueba")

    def test_saltos_de_linea_de_las_notas(self):
        self.editar(self.num_ecg, notas="Línea 1\r\nLínea 2")
        self.assertEqual(self.equipo(self.num_ecg)["notas"], "Línea 1\nLínea 2")
        # Las notas que ya tenían \n no cuentan como cambio al volver a guardar.
        antes = self.equipo(self.num_cable)["actualizado_en"]
        self.editar(self.num_cable, notas=self.equipo(self.num_cable)["notas"].replace("\n", "\r\n"))
        self.assertEqual(self.equipo(self.num_cable)["actualizado_en"], antes)

    def test_estatus_con_la_forma_del_catalogo(self):
        self.editar(self.num_ecg, estatus="baja")
        self.assertEqual(self.equipo(self.num_ecg)["estatus"], "Baja")

    def test_estatus_fuera_del_catalogo(self):
        respuesta = self.editar(self.num_ecg, estatus="Prestado")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Elige un estatus", respuesta.get_data(as_text=True))
        # Pero un equipo que ya lo tiene puede conservarlo al editar otra cosa.
        respuesta = self.editar(self.num_raro, marca="Nueva marca")
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.equipo(self.num_raro)["estatus"], "Prestado")

    def test_tipo_obligatorio(self):
        respuesta = self.editar(self.num_ecg, tipo="  ")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("El tipo de equipo es obligatorio", respuesta.get_data(as_text=True))

    def test_id_repetido(self):
        respuesta = self.editar(self.num_otro_monitor, id_interno="crm gdl 01 02 03")
        self.assertEqual(respuesta.status_code, 400)
        html = respuesta.get_data(as_text=True)
        self.assertIn("Ya existe un equipo con el ID interno", html)
        self.assertIn('value="crm gdl 01 02 03"', html)     # se conserva lo capturado

    def test_campo_demasiado_largo(self):
        respuesta = self.editar(self.num_ecg, modelo="x" * 201)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("máximo 200 caracteres", respuesta.get_data(as_text=True))

    def test_texto_se_escapa(self):
        self.editar(self.num_ecg, modelo='"><script>alert(1)</script>')
        html = self.cliente.get(f"/equipo/{self.num_ecg}/editar").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)", html)

    def test_cambio_de_otra_persona_no_se_sobrescribe(self):
        datos = self.formulario(self.num_ecg, area="Terapia")
        db.actualizar_equipo(self.conexion(), self.num_ecg, {"area": "Quirófano"}, "jefatura")
        respuesta = self.cliente.post(f"/equipo/{self.num_ecg}/editar", data=datos)
        self.assertEqual(respuesta.status_code, 409)
        html = respuesta.get_data(as_text=True)
        self.assertIn("Otra persona guardó cambios", html)
        self.assertIn("Guardado ahora: Quirófano", html)
        self.assertEqual(self.equipo(self.num_ecg)["area"], "Quirófano")
        # Al volver a guardar (con la versión nueva que trae la pantalla) sí se guarda.
        version = html.split('name="version" value="')[1].split('"')[0]
        datos["version"] = version
        self.assertEqual(self.cliente.post(f"/equipo/{self.num_ecg}/editar", data=datos).status_code, 302)
        self.assertEqual(self.equipo(self.num_ecg)["area"], "Terapia")

    def test_cambio_de_otra_persona_igual_al_mio_no_avisa(self):
        # Las dos personas pusieron lo mismo: no hay nada que revisar.
        datos = self.formulario(self.num_ecg, area="Quirófano")
        db.actualizar_equipo(self.conexion(), self.num_ecg, {"area": "Quirófano"}, "jefatura")
        respuesta = self.cliente.post(f"/equipo/{self.num_ecg}/editar", data=datos)
        self.assertEqual(respuesta.status_code, 302)
        html = self.cliente.get(respuesta.headers["Location"]).get_data(as_text=True)
        self.assertIn("No había cambios", html)


class PruebasPadre(BaseEdicion):

    def test_candidatos_a_padre(self):
        html = self.cliente.get(f"/equipo/{self.num_otro_monitor}/editar").get_data(as_text=True)
        self.assertIn(f'<option value="{self.num_ecg}"', html)
        self.assertIn(f'<option value="{self.num_monitor}"', html)        # tiene componentes, sí puede ser padre
        self.assertNotIn(f'<option value="{self.num_otro_monitor}"', html)  # él mismo
        self.assertNotIn(f'<option value="{self.num_baja}"', html)          # en Baja
        self.assertNotIn(f'<option value="{self.num_cable}"', html)         # ya es componente

    def test_ligar_y_desligar(self):
        self.editar(self.num_otro_monitor, padre_num=str(self.num_ecg))
        self.assertEqual(self.equipo(self.num_otro_monitor)["padre_num"], self.num_ecg)
        self.editar(self.num_otro_monitor, padre_num="")
        self.assertIsNone(self.equipo(self.num_otro_monitor)["padre_num"])

    def test_equipo_con_componentes_no_tiene_lista_de_padre(self):
        respuesta = self.cliente.get(f"/equipo/{self.num_monitor}/editar")
        html = respuesta.get_data(as_text=True)
        self.assertIn("Este equipo tiene 1 componente", html)
        self.assertNotIn('name="padre_num"', html)
        # El formulario no manda padre_num: guardar otros campos funciona.
        datos = self.formulario(self.num_monitor, marca="Mindray 2")
        del datos["padre_num"]
        self.assertEqual(self.cliente.post(f"/equipo/{self.num_monitor}/editar", data=datos).status_code, 302)
        # Y si alguien lo manda a mano, db.py lo rechaza.
        respuesta = self.editar(self.num_monitor, padre_num=str(self.num_ecg))
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tiene componentes", respuesta.get_data(as_text=True))

    def test_padre_actual_en_baja_sigue_en_la_lista(self):
        self.editar(self.num_otro_monitor, padre_num=str(self.num_ecg))
        db.actualizar_equipo(self.conexion(), self.num_ecg, {"estatus": "Baja"}, "prueba")
        html = self.cliente.get(f"/equipo/{self.num_otro_monitor}/editar").get_data(as_text=True)
        self.assertIn(f'<option value="{self.num_ecg}" selected', html)

    def test_no_puede_ser_su_propio_padre(self):
        respuesta = self.editar(self.num_ecg, padre_num=str(self.num_ecg))
        self.assertEqual(respuesta.status_code, 400)


class PruebasNuevo(BaseEdicion):

    def test_alta(self):
        respuesta = self.cliente.post("/equipo/nuevo", data={
            "tipo": "Bomba de infusión", "marca": "Baxter", "estatus": "Funcional",
            "padre_num": "", "id_interno": "", "notas": ""})
        self.assertEqual(respuesta.status_code, 302)
        codigo = respuesta.headers["Location"].rsplit("/", 1)[1]
        equipo = db.obtener_equipo_por_codigo(self.conexion(), codigo)
        self.assertEqual(equipo["tipo"], "Bomba de infusión")
        self.assertIsNone(equipo["id_interno"])
        self.assertEqual(equipo["actualizado_por"], "diego")
        self.assertEqual(len(equipo["codigo"]), 8)
        html = self.cliente.get(respuesta.headers["Location"]).get_data(as_text=True)
        self.assertIn("Equipo dado de alta", html)

    def test_pantalla_de_componente(self):
        html = self.cliente.get(f"/equipo/nuevo?padre={self.num_ecg}").get_data(as_text=True)
        self.assertIn(f'<option value="{self.num_ecg}" selected', html)
        self.assertIn('value="Urgencias"', html)                  # área del padre
        self.assertIn('<option value="Funcional" selected', html)

    def test_padre_no_valido_se_ignora(self):
        for padre in ("abc", "9999", str(self.num_cable)):
            with self.subTest(padre=padre):
                respuesta = self.cliente.get(f"/equipo/nuevo?padre={padre}")
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotIn(" selected>", respuesta.get_data(as_text=True).split('id="padre_num"')[1].split("</select>")[0])

    def test_alta_de_componente(self):
        respuesta = self.cliente.post("/equipo/nuevo", data={
            "tipo": "Sensor de SpO2", "estatus": "Funcional", "padre_num": str(self.num_ecg)})
        codigo = respuesta.headers["Location"].rsplit("/", 1)[1]
        self.assertEqual(db.obtener_equipo_por_codigo(self.conexion(), codigo)["padre_num"], self.num_ecg)

    def test_errores_conservan_lo_capturado(self):
        respuesta = self.cliente.post("/equipo/nuevo", data={"tipo": "", "marca": "Philips"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('value="Philips"', respuesta.get_data(as_text=True))


class PruebasMantenimiento(BaseEdicion):

    def registrar(self, num=None, **datos):
        base = {"fecha": db.hoy().isoformat(), "tipo": "preventivo",
                "descripcion": "Revisión general", "realizado_por": "Técnico interno"}
        base.update(datos)
        return self.cliente.post(f"/equipo/{num or self.num_monitor}/mantenimiento", data=base)

    def test_registrar(self):
        respuesta = self.registrar()
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.headers["Location"].endswith("#historial"))
        mto = db.listar_mantenimientos(self.conexion(), self.num_monitor)[0]
        self.assertEqual(mto["registrado_por"], "diego")
        self.assertEqual(mto["realizado_por"], "Técnico interno")
        self.assertEqual(db.ultimo_preventivo(self.conexion(), self.num_monitor),
                         db.hoy().isoformat())
        html = self.cliente.get(respuesta.headers["Location"].split("#")[0]).get_data(as_text=True)
        self.assertIn("Mantenimiento registrado", html)

    def test_fecha_futura(self):
        manana = (db.hoy() + timedelta(days=1)).isoformat()
        respuesta = self.registrar(fecha=manana, descripcion="Capturado")
        self.assertEqual(respuesta.status_code, 400)
        html = respuesta.get_data(as_text=True)
        self.assertIn("no puede ser posterior a hoy", html)
        self.assertIn('class="registrar-mto" open', html)          # el formulario queda abierto
        self.assertIn("Capturado", html)                           # con lo capturado
        self.assertEqual(db.listar_mantenimientos(self.conexion(), self.num_monitor), [])

    def test_tipo_no_valido(self):
        self.assertEqual(self.registrar(tipo="otro").status_code, 400)

    def test_equipo_inexistente(self):
        self.assertEqual(self.registrar(num=9999).status_code, 404)

    def test_solo_post(self):
        self.assertEqual(self.cliente.get(f"/equipo/{self.num_monitor}/mantenimiento").status_code, 405)

    def test_no_cambia_actualizado_en_del_equipo(self):
        antes = self.equipo(self.num_monitor)["actualizado_en"]
        self.registrar()
        self.assertEqual(self.equipo(self.num_monitor)["actualizado_en"], antes)


if __name__ == "__main__":
    unittest.main()