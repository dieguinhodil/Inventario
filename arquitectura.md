# Arquitectura — App de inventario (Cruz Roja Guadalajara)

> **Para cualquier chat nuevo del proyecto:** lee este documento completo antes de escribir código.
> Este chat programa SOLO el módulo que se indique, respetando los contratos de abajo.
> Si un contrato necesita cambiar, se cambia primero en el chat de arquitectura (el del `main.py`) y se actualiza este documento.

Última actualización: 2026-10-22

---

## 0. Estado actual

| Pieza | Estado |
|---|---|
| `config.py` | ✅ Listo. Diccionarios de normalización ya llenos (chat de limpieza) |
| `main.py` | ✅ Listo. Se detiene con aviso en el primer módulo pendiente |
| `requirements.txt`, `.gitignore` | ✅ Listos |
| `docs/` (visor) | ✅ Reglas de presentación definidas en su chat (ver sección 7, `docs/`) |
| `modulos/*.py` | ⏳ Cada uno lanza `NotImplementedError` hasta programarse en su chat. Actualizar esta tabla al terminar cada uno |

El flujo completo de `main.py` ya se probó con implementaciones provisionales: 316 leídas → 293 incluidas → 16 TMP → 293 QR → PDF. Enlace más largo: 279 caracteres.

## 1. Objetivo

Generar un QR único por equipo de la hoja **GUADALAJARA** del Excel `INVENTARIO_JUNIO_2025`.
Cada QR contiene un enlace a una página visor en GitHub Pages con los datos del equipo **después del `#`**
(ej. `https://dieguinhodil.github.io/Inventario/#id=...`). Así lo lee la cámara del iPhone y los datos
nunca se envían al servidor. Después se arma un PDF imprimible con las etiquetas.

Más adelante: ficha técnica completa en una página web (fuera del alcance de esta versión).

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Datos en el QR | ID, tipo, marca, modelo, no. serie, área, estatus, **último mantenimiento preventivo** |
| Formato del enlace | Claves completas y valores sin abreviar: `#id=...&tipo=...&marca=...&modelo=...&serie=...&area=...&estatus=...&ultimo_mprev=AAAA-MM-DD` |
| Tamaño de etiqueta | **5×5 cm** (QR de ~4.2 cm + ID en texto). Módulo del QR ≈ 0.65–0.74 mm, lectura segura |
| Equipos excluidos | Solo estatus **Baja** (23). Fuera de Servicio y demás sí llevan QR |
| IDs "Sin información" y repetidos | Se marcan como temporales `TMP-001`, `TMP-002`… en orden de fila del Excel |
| Repetidos | Si un ID aparece 2+ veces entre los incluidos, **todas** sus filas reciben TMP |
| ID original | Se conserva en `id_original` para trazabilidad (CSV de revisión) |
| Visor | GitHub Pages, repo `Inventario`, rama `main`, carpeta `/docs`. URL: **https://dieguinhodil.github.io/Inventario/** (con I mayúscula) |
| Cuenta y Ubicación | Iguales en las 316 filas → no van en el QR; texto fijo en el visor |
| Campos vacíos en el visor | `ultimo_mprev` vacío → "Sin registro"; cualquier otro campo vacío → "Sin dato" |
| Color del estatus | Verde: Funcional · Ámbar: En Revisión, En Mantenimiento · Rojo: Fuera de Servicio, No Funcional |
| Aviso de ID temporal | Si el ID empieza con `TMP-`, el visor muestra un aviso de "ID temporal" |
| Página sin datos | Si se abre el visor sin `#` o sin datos, muestra "Escanea el QR de un equipo" |
| Normalización | Variantes de marca y tipo → forma oficial vía `config.py`; la comparación ignora mayúsculas, acentos y espacios extra |
| Contenedores (Docker) | Al final, cuando el proyecto esté terminado. Por ahora `requirements.txt` + entorno virtual |
| Organización | Un módulo de Python por responsabilidad; un chat de Claude por módulo |

## 3. Pendientes conocidos

- [ ] **Fechas de último MPrev:** hoy 147 de 293 equipos incluidos tienen fecha. La jefa de servicio tiene fechas más recientes de casi todos; se capturarán manualmente en la columna K del Excel más adelante. Por ahora se trabaja con las que hay; si no hay fecha, el campo se omite del enlace y el visor muestra "Sin registro".
- [ ] Antes de imprimir: regenerar QR después de capturar las fechas nuevas (el QR guarda los datos del momento en que se genera).

## 4. Datos de origen

- Hoja `GUADALAJARA`, encabezados en la fila 4, datos desde la **fila 5**, columnas **B a K** (316 filas).
- Columnas: ID Interno, Cuenta, Tipo Activo, Marca, Modelo, No. Serie, Ubicación, Área, Estatus, Último MPrev.
- Estructura del ID: `CRM GDL AA BB CC` (AA área, BB tipo de equipo, CC consecutivo).
- Resultado verificado: 316 leídas → 23 excluidas (Baja) → 293 incluidas → 16 TMP
  (8 sin ID + 8 con ID repetido). Los 6 IDs `CRMG 023…` están todos en Baja.
- Último MPrev viene como fecha de Excel (`datetime`) o vacío.
- Campos vacíos: 16 filas sin Área en el Excel, pero 15 están en Baja → **solo 1 equipo incluido** sin área.
  1 equipo incluido sin No. Serie (celda vacía). Además 133 series dicen literalmente "S/D" (no están vacías).

## 5. Diagrama de flujo (lógica de `main.py`)

1. Leer hoja GUADALAJARA → `lector_excel`
2. Limpiar espacios y textos → `limpieza`
3. ¿Estatus es Baja? Sí → excluir (y registrar en `salida/excluidos.csv`) / No → seguir → `filtros`
4. ¿ID válido y único? No → asignar TMP-NNN / Sí → seguir → `ids`
5. Construir enlace → `enlaces` (y guardar `salida/revision_qr.csv`)
6. Generar imagen QR → `generador_qr` (solo con `--qr`)
7. Armar PDF de etiquetas → `pdf_etiquetas` (solo con `--qr`)

Uso: `python main.py --excel INVENTARIO_JUNIO_2025.xlsx` (pasos 1–5) o agregar `--qr` (pasos 6–7).

## 6. Estructura del repositorio

```
Inventario/
├── main.py              ← sigue el diagrama de flujo
├── config.py            ← constantes compartidas (ver sección 8)
├── requirements.txt
├── .gitignore           ← excluye *.xlsx, *.csv y salida/
├── modulos/
│   ├── __init__.py
│   ├── lector_excel.py
│   ├── limpieza.py
│   ├── filtros.py
│   ├── ids.py
│   ├── enlaces.py
│   ├── generador_qr.py
│   └── pdf_etiquetas.py
├── docs/                ← lo que publica GitHub Pages
│   ├── index.html
│   ├── estilos.css
│   └── visor.js
└── salida/              ← CSV de revisión, QR, PDF (NO se sube)
```

⚠️ El repositorio es **público**: nunca subir el Excel, los CSV ni la carpeta `salida/`.

## 7. Contratos de los módulos

**Formato común — "equipo":** un `dict` con las claves de `config.COLUMNAS`
(`id`, `cuenta`, `tipo`, `marca`, `modelo`, `serie`, `ubicacion`, `area`, `estatus`, `ultimo_mprev`) más `fila_excel` (int).
Después de `limpieza`, todos los valores son `str` (vacío `""` si no hay dato).
Los módulos posteriores agregan claves, nunca quitan ni renombran las existentes.
Si un módulo no está terminado, su función lanza `NotImplementedError` (así `main.py` sabe que está pendiente).

### `lector_excel.py`
```python
def leer_hoja(ruta, hoja=config.HOJA) -> list[dict]
```
Lee desde `config.PRIMERA_FILA`, columnas `config.COL_INI..COL_FIN` (B..K). Omite filas totalmente vacías.
Devuelve valores tal cual vienen (sin limpiar), con `fila_excel` = número de fila real.

### `limpieza.py`
```python
def limpiar(equipos: list[dict]) -> list[dict]
```
- Quita espacios al inicio/fin y espacios dobles; `None` → `""`.
- Números de serie numéricos → texto sin `.0` (ej. `120601062`).
- Fechas (`ultimo_mprev`) → `AAAA-MM-DD`.
- Unifica variantes con `config.NORMALIZAR_MARCAS` y `config.NORMALIZAR_TIPOS` (variante → forma oficial).
  La comparación ignora mayúsculas, acentos y espacios extra.
- No elimina filas ni cambia `fila_excel`.

### `filtros.py`
```python
def separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS) -> tuple[list[dict], list[dict]]
    # devuelve (incluidos, excluidos); compara sin mayúsculas ni espacios
def filtrar(equipos, area=None, estatus=None) -> list[dict]
    # filtro general reutilizable (ej. solo Urgencias). El área es un parámetro, no un módulo.
```

### `ids.py`
```python
def asignar_ids(equipos: list[dict]) -> list[dict]
```
Agrega `id_original`, `id_final`, `motivo_id` (`""`, `"sin_id"`, `"id_repetido"`, `"formato_distinto"`).
TMP solo para `sin_id` e `id_repetido`; `formato_distinto` conserva su ID y solo se marca.
Numeración `TMP-001`… en orden de `fila_excel`. Validación con `config.FORMATO_ID`.

### `enlaces.py`
```python
def construir_enlace(equipo: dict, base_url=config.BASE_URL) -> str
```
Claves completas en el orden de `config.CAMPOS_QR`:
`id, tipo, marca, modelo, serie, area, estatus, ultimo_mprev`. La clave `id` toma `equipo["id_final"]`.
Codifica con `urllib.parse.quote(valor, safe="")`. Omite campos vacíos.
Debe coincidir con `docs/visor.js`.

### `generador_qr.py`
```python
def generar_qr(enlace: str, ruta_salida: str) -> str
```
Librería `qrcode`, corrección de errores `config.CORRECCION_QR` ("M"), `border=0` (el margen lo pone el PDF).
Guarda PNG y devuelve la ruta.

### `pdf_etiquetas.py`
```python
def armar_pdf(equipos: list[dict], ruta_pdf: str, tam_cm=config.TAM_ETIQUETA_CM) -> str
```
Cada equipo trae `ruta_qr` e `id_final`. Etiqueta 5×5 cm: QR (~4.2 cm) + `id_final` en texto debajo.
Hoja carta, rejilla 4 × 5 = 20 etiquetas por hoja (~15 hojas). Líneas de corte tenues. Librería `reportlab`.

### `docs/` (visor)
- Lee `location.hash`, decodifica los campos (`decodeURIComponent`) y los muestra como ficha.
- Muestra Cuenta ("Cruz Roja Mexicana") y Ubicación ("Cruz Roja Guadalajara") como texto fijo.
- **Campos vacíos:** si falta `ultimo_mprev` → "Sin registro"; cualquier otro campo ausente o vacío → "Sin dato".
  Los valores que significan "sin dato" en el Excel (`S/D`, `N/A`, `-`) también se muestran como "Sin dato" (solo en el visor; el enlace los lleva tal cual).
- **Color del estatus:**
  | Estatus | Color |
  |---|---|
  | Funcional | Verde |
  | En Revisión, En Mantenimiento | Ámbar |
  | Fuera de Servicio, No Funcional | Rojo |
- **ID temporal:** si `id` empieza con `TMP-`, muestra un aviso de "ID temporal".
- **Sin datos:** si la página se abre sin `#` o sin campos, muestra "Escanea el QR de un equipo".
- HTML + CSS + JS sin librerías. No hace ninguna petición a servidores con los datos:
  `index.html` lo garantiza con una Content-Security-Policy que bloquea cualquier recurso externo.
- Probado en Chromium y WebKit (motor de Safari/iPhone), modo claro y oscuro, con enlaces reales del Excel.

## 8. `config.py` (resumen)

```python
RUTA_EXCEL = "INVENTARIO_JUNIO_2025.xlsx"
HOJA = "GUADALAJARA"
PRIMERA_FILA = 5
COL_INI, COL_FIN = 2, 11
COLUMNAS = ["id","cuenta","tipo","marca","modelo","serie","ubicacion","area","estatus","ultimo_mprev"]
SIN_ID = "Sin información"
ESTATUS_EXCLUIDOS = ["baja"]
FORMATO_ID = r"^CRM GDL \d{2} \d{2} \d{2}$"
PREFIJO_TMP = "TMP-"
BASE_URL = "https://dieguinhodil.github.io/Inventario/"
CAMPOS_QR = ["id","tipo","marca","modelo","serie","area","estatus","ultimo_mprev"]
TAM_ETIQUETA_CM = 5
CORRECCION_QR = "M"
NORMALIZAR_MARCAS = {   # variante -> forma oficial
    "Hergom Medical": "HERGOM",
    "Devilbiss": "Devilbiss Healthcare",
    "Precision Medical": "Precision Medical Equipment",
    "Saps": "SAPS",
    "Torino": "Torino (Oken)",
    "Puritan Bennett": "Puritan Bennett (Medtronic)",
    "Nellcor Puritan Bennett": "Puritan Bennett (Medtronic)",
}
NORMALIZAR_TIPOS = {
    "Maquina de anestesia": "Máquina de Anestesia",
}
CARPETA_SALIDA, CARPETA_QR = "salida", "salida/qr"
CSV_REVISION, CSV_EXCLUIDOS = "salida/revision_qr.csv", "salida/excluidos.csv"
PDF_ETIQUETAS = "salida/etiquetas.pdf"
```

La versión completa y vigente es el documento `config.py` del proyecto.

## 9. Reglas para todos los chats

- Python 3.10+. Dependencias: `openpyxl`, `qrcode[pil]`, `reportlab`.
- Nombres de funciones y variables en español, sin acentos.
- Cada módulo se puede probar solo con su bloque `if __name__ == "__main__":` (ya incluido en la plantilla).
- Cada chat parte de la plantilla del módulo (pídele al usuario que la pegue o la adjunte).
- Si un chat toma una decisión que afecta a otros módulos o al visor, avisa al usuario para anotarla aquí.
- Respuestas en español, paso a paso. Si no se hizo una acción o se omitió información, decirlo.

## 10. Orden sugerido de chats

1. ✅ Arquitectura + `main.py` + `config.py`
2. `lector_excel.py`
3. `limpieza.py` (diccionarios de normalización ya en `config.py`)
4. `filtros.py` + `ids.py` (ya existe una versión funcional en el script preliminar)
5. `enlaces.py` + `docs/visor.js` + `docs/estilos.css` (reglas del visor ya definidas)
6. `generador_qr.py` + `pdf_etiquetas.py`