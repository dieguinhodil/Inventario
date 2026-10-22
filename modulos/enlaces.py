"""
Paso 5 — Construir el enlace del QR.

Contrato:
    construir_enlace(equipo: dict, base_url=config.BASE_URL) -> str

- Formato: base_url + "#" + "clave=valor&clave=valor..."
- Claves completas, en el orden de config.CAMPOS_QR. La clave "id" toma equipo["id_final"].
- Valores codificados con urllib.parse.quote(valor, safe="").
- Omite campos vacíos.
- Debe coincidir EXACTAMENTE con lo que lee docs/visor.js.

Estado: PENDIENTE — se programa en su propio chat siguiendo arquitectura.md.
"""
import config


def construir_enlace(equipo, base_url=config.BASE_URL):
    raise NotImplementedError


if __name__ == "__main__":
    ejemplo = {"id_final": "CRM GDL 02 01 01", "tipo": "Aspirador", "marca": "HERGOM",
               "modelo": "7A-23D", "serie": "120601062", "area": "Urgencias",
               "estatus": "Funcional", "ultimo_mprev": "2025-01-15"}
    print(construir_enlace(ejemplo))
