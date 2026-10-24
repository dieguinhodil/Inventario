# Arquitectura — App de inventario (Cruz Roja Guadalajara)

> **Para cualquier chat nuevo del proyecto:** lee este documento completo antes de escribir código.
> Este chat programa SOLO el módulo que se indique, respetando los contratos de abajo.
> Si un contrato necesita cambiar, se cambia primero en el chat de arquitectura (el del `main.py`) y se actualiza este documento.
>
> **Documento vigente:** `Inventario/arquitectura.md`. Si existe `claude/arquitectura.md`, es una versión vieja (16-oct) y no debe usarse.

Última actualización: 2026-10-23

---

## 0. Estado actual

| Pieza | Estado |
|---|---|
| `config.py` | ✅ Listo. Diccionarios de normalización llenos |
| `main.py` | ✅ Listo. Se detiene con aviso en el primer módulo pendiente. CSV en `utf-8-sig` (acentos correctos al abrirlos en Excel) |
| `requirements.txt`, `.gitignore` | ✅ Listos |
| `modulos/lector_excel.py` | ✅ Listo — 316 filas |
| `modulos/limpieza.py` | ✅ Listo |
| `modulos/filtros.py` | ✅ Listo — 293 incluidos, 23 excluidos |
| `modulos/ids.py` | ✅ Listo — 16 TMP (8 sin ID + 8 repetidos) |
| `modulos/enlaces.py` | ✅ Listo — 293 enlaces, el más largo 279 caracteres |
| `modulos/generador_qr.py` | ✅ Listo — 293 QR, todos se leen de vuelta con su enlace exacto |
| `modulos/pdf_etiquetas.py` | ⏳ **Pendiente** (último módulo). Ver instrucciones en la sección 7 |
| `docs/` (visor) | ✅ Listo — probado en Chromium y WebKit (Safari/iPhone), modo claro y oscuro |

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
| Tamaño de etiqueta | **5×5 cm**: QR + ID en texto debajo. Lado del QR ~4.2 cm (**ver pendiente de espacio vertical, sección 3**) |
| Equipos excluidos | Solo estatus **Baja** (23). Fuera de Servicio y demás sí llevan QR |
| IDs "Sin información" y repetidos | Se marcan como temporales `TMP-001`, `TMP-002`… en orden de fila del Excel |
| Repetidos | Si un ID aparece 2+ veces entre los incluidos, **todas** sus filas reciben TMP |
| ID original | Se conserva en `id_original` para trazabilidad (CSV de revisión) |
| Visor | GitHub Pages, repo `Inventario`, rama `main`, carpeta `/docs`. URL: **https://dieguinhodil.github.io/Inventario/** (con I mayúscula) |
| Cuenta y Ubicación | No van en el QR; texto fijo en el visor: **Cuenta = "Cruz Roja Mexicana"**, **Ubicación = "Delegación Guadalajara"** (en el Excel la columna dice "Cruz Roja Guadalajara"; en el visor se muestra "Delegación Guadalajara" por decisión del usuario) |
| Cabecera del visor | "Cruz Roja Mexicana" + subtítulo "Inventario de equipo biomédico" |
| Campos vacíos en el visor | `ultimo_mprev` vacío → "Sin registro"; cualquier otro campo vacío → "Sin dato". Los valores `S/D`, `N/A`, `NA`, `-`, `--`, `Sin dato` también se muestran como "Sin dato" (solo en el visor; el enlace los lleva tal cual) |
| Color del estatus | Verde: Funcional · Ámbar: En Revisión, En Mantenimiento · Rojo: Fuera de Servicio, No Funcional (y Baja, aunque no llega al QR) · Gris neutro: cualquier otro valor |
| Aviso de ID temporal | Si el ID empieza con `TMP-`, el visor muestra un aviso de "ID temporal" |
| Página sin datos | Si se abre el visor sin `#` o sin datos, muestra "Escanea el QR de un equipo" |
| Normalización | Variantes de marca y tipo → forma oficial vía `config.py`; la comparación ignora mayúsculas, acentos y espacios extra (función `limpieza.clave`, compartida por `filtros` e `ids`) |
| Contenedores (Docker) | Al final, cuando el proyecto esté terminado. Por ahora `requirements.txt` + entorno virtual |
| Organización | Un módulo de Python por responsabilidad; un chat de Claude por módulo |

## 3. Pendientes conocidos

- [ ] **Espacio vertical de la etiqueta (decidir en el chat de `pdf_etiquetas`):** con QR de 4.2 cm no caben en 5 cm
      el margen de 3 mm arriba + QR 42 mm + 3 mm de separación + texto del ID (~2.5 mm) + margen abajo (≈ 53 mm).
      Opción sugerida: **QR de 3.8 cm** (3 + 38 + 3 + 2.5 + 3 ≈ 49.5 mm). El módulo más pequeño queda en
      38 / 65 ≈ 0.58 mm, todavía arriba del mínimo de 0.5 mm. Si se cambia, actualizar `TAM_QR_CM` en
      `generador_qr.py` (solo afecta el aviso de tamaño mínimo); lo ideal es moverlo a `config.py` para que ambos módulos usen el mismo valor.
- [ ] **Fechas de último MPrev:** hoy 147 de 293 equipos incluidos tienen fecha. La jefa de servicio tiene fechas más recientes de casi todos; se capturarán manualmente en la columna K del Excel más adelante. Si no hay fecha, el campo se omite del enlace y el visor muestra "Sin registro".
- [ ] Antes de imprimir: regenerar QR después de capturar las fechas nuevas (el QR guarda los datos del momento en que se genera). Los enlaces crecerán; `generador_qr` avisa si algún módulo queda por debajo de 0.5 mm.
- [ ] Borrar `claude/arquitectura.md` (versión vieja duplicada) para que ningún chat la lea por error.

## 4. Datos de origen

- Hoja `GUADALAJARA`, encabezados en la fila 4, datos desde la **fila 5**, columnas **B a K** (316 filas).
- Columnas: ID Interno, Cuenta, Tipo Activo, Marca, Modelo, No. Serie, Ubicación, Área, Estatus, Último MPrev.
- Estructura del ID: `CRM GDL AA BB CC` (AA área, BB tipo de equipo, CC consecutivo).
- Resultado verificado: 316 leídas → 23 excluidas (Baja) → 293 incluidas → 16 TMP
  (8 sin ID + 8 con ID repetido). Los 6 IDs `CRMG 023…` están todos en Baja.
- Último MPrev viene como fecha de Excel (`datetime`) o vacío.
- Campos vacíos: 16 filas sin Área en el Excel, pero 15 están en Baja → **solo 1 equipo incluido** sin área.
  1 equipo incluido sin No. Serie (celda vacía). Además 133 series dicen literalmente "S/D".
- QR resultantes: versiones **8 a 12** (49 a 65 módulos por lado).

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
├── arquitectura.md      ← este documento
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

### `lector_excel.py` ✅
```python
def leer_hoja(ruta, hoja=config.HOJA) -> list[dict]
```
Lee desde `config.PRIMERA_FILA`, columnas `config.COL_INI..COL_FIN` (B..K). Omite filas totalmente vacías.
Devuelve valores tal cual vienen (sin limpiar), con `fila_excel` = número de fila real.
Si la hoja no existe, lanza `ValueError` con la lista de hojas disponibles.

### `limpieza.py` ✅
```python
def limpiar(equipos: list[dict]) -> list[dict]
def clave(texto) -> str      # forma de comparar: sin mayúsculas, acentos ni espacios sobrantes
```
- Quita espacios al inicio/fin y espacios dobles (incluye tabs, espacio duro y caracteres invisibles); `None` → `""`.
- Números (serie, modelo) → texto sin `.0` (ej. `120601062`).
- Fechas (`ultimo_mprev`) → `AAAA-MM-DD`. Acepta fecha de Excel, número serial o texto (`AAAA-MM-DD`, `DD/MM/AAAA`, etc.).
  Si no se reconoce, la deja vacía y avisa con un warning indicando la fila (no inventa fechas).
- Unifica variantes con `config.NORMALIZAR_MARCAS` y `config.NORMALIZAR_TIPOS` (variante → forma oficial).
- No elimina filas ni cambia `fila_excel`. Devuelve una lista nueva (no modifica la original).
- `clave()` la usan también `filtros.py` e `ids.py`.

### `filtros.py` ✅
```python
def separar_por_estatus(equipos, excluidos=config.ESTATUS_EXCLUIDOS) -> tuple[list[dict], list[dict]]
    # devuelve (incluidos, excluidos); compara con limpieza.clave
def filtrar(equipos, area=None, estatus=None) -> list[dict]
    # filtro general reutilizable (ej. solo Urgencias). El área es un parámetro, no un módulo.
```

### `ids.py` ✅
```python
def asignar_ids(equipos: list[dict]) -> list[dict]
```
Agrega `id_original`, `id_final`, `motivo_id` (`""`, `"sin_id"`, `"id_repetido"`, `"formato_distinto"`).
TMP solo para `sin_id` e `id_repetido`; `formato_distinto` conserva su ID y solo se marca.
`id_repetido` tiene prioridad sobre `formato_distinto` (un ID con formato distinto que además se repite recibe TMP).
Numeración `TMP-001`… en orden de `fila_excel`. Validación con `config.FORMATO_ID`. La lista se devuelve en el mismo orden de entrada.

### `enlaces.py` ✅
```python
def construir_enlace(equipo: dict, base_url=config.BASE_URL) -> str
def leer_enlace(enlace: str) -> dict   # hace lo mismo que visor.js; sirve para pruebas
```
Claves completas en el orden de `config.CAMPOS_QR`:
`id, tipo, marca, modelo, serie, area, estatus, ultimo_mprev`. La clave `id` toma `equipo["id_final"]`.
Codifica con `urllib.parse.quote(valor, safe="")`. Omite campos vacíos.
Si el equipo no trae `id_final`, lanza `KeyError` (hay que correr `ids.asignar_ids()` antes).
Debe coincidir con `docs/visor.js`.

### `generador_qr.py` ✅
```python
def generar_qr(enlace: str, ruta_salida: str) -> str
def info_qr(enlace: str) -> dict       # versión, módulos, tamaño de módulo (mm) y píxeles
```
- Librería `qrcode`, corrección de errores `config.CORRECCION_QR` ("M"), `border=0` (el margen lo pone el PDF).
- Versión del QR automática según el largo del enlace (hoy 8 a 12).
- `TAM_MODULO_PX = 10` → PNG de **490 a 650 px** por lado (~390 ppp impreso a 4.2 cm).
- PNG en blanco y negro puro (1 bit), ~1–2 KB.
- Avisa con un warning (sin detenerse) si el módulo impreso quedaría por debajo de `MODULO_MIN_MM = 0.5`,
  calculado con `TAM_QR_CM = 4.2`. **Si el PDF usa otro lado de QR, actualizar `TAM_QR_CM`.**
- Crea la carpeta de salida si no existe. Guarda PNG y devuelve la ruta.

### `pdf_etiquetas.py` ⏳
```python
def armar_pdf(equipos: list[dict], ruta_pdf: str, tam_cm=config.TAM_ETIQUETA_CM) -> str
```
Cada equipo trae `ruta_qr` e `id_final`. Etiqueta 5×5 cm: QR + `id_final` en texto debajo.
Hoja carta, rejilla 4 × 5 = 20 etiquetas por hoja (~15 hojas). Líneas de corte tenues. Librería `reportlab`.

**Instrucciones del chat de `generador_qr` (obligatorias):**
- Los PNG **no traen margen** y su tamaño en píxeles **varía (490 a 650 px)**. El PDF debe dibujarlos
  **siempre a un lado fijo** (~4.2 cm, o el valor que se decida) usando `drawImage(..., width=, height=)`,
  nunca a su tamaño natural.
- El **margen blanco alrededor del QR debe ser de al menos ~3 mm (4 módulos)** por los cuatro lados,
  **incluido el espacio entre el QR y el texto del ID**. Sin ese margen la cámara puede no reconocerlo.
- Revisar el pendiente de espacio vertical (sección 3) antes de fijar el lado del QR.

### `docs/` (visor) ✅
- Lee `location.hash`, decodifica los campos (`decodeURIComponent`) y los muestra como ficha.
  Ignora claves que no estén en `CAMPOS_QR`; si una clave se repite, gana la primera.
- Cabecera: "Cruz Roja Mexicana" / "Inventario de equipo biomédico".
- Texto fijo en `visor.js`:
  ```javascript
  CUENTA = "Cruz Roja Mexicana";
  UBICACION = "Delegación Guadalajara";
  ```
- **Campos vacíos:** si falta `ultimo_mprev` → "Sin registro"; cualquier otro campo ausente o vacío → "Sin dato".
  Los valores `S/D`, `N/A`, `NA`, `-`, `--`, `Sin dato` también se muestran como "Sin dato" (solo en el visor).
- **Fecha:** `2025-01-15` se muestra como "15 de enero de 2025" (valida que la fecha exista en el calendario).
- **Color del estatus:**
  | Estatus | Color |
  |---|---|
  | Funcional | Verde |
  | En Revisión, En Mantenimiento | Ámbar |
  | Fuera de Servicio, No Funcional, Baja | Rojo |
  | Cualquier otro valor | Gris neutro |
- **ID temporal:** si `id` empieza con `TMP-`, muestra el aviso "ID temporal: este equipo no tenía un ID interno válido o estaba repetido en el inventario."
- **Sin datos:** si la página se abre sin `#` o sin campos, muestra "Escanea el QR de un equipo".
- **Seguridad:** los valores se insertan siempre con `textContent` (nunca `innerHTML`), porque cualquiera puede escribir un enlace con datos inventados.
- HTML + CSS + JS sin librerías. No hace ninguna petición a servidores con los datos:
  `index.html` lo garantiza con una Content-Security-Policy que bloquea cualquier recurso externo.
- Pie: "Datos al momento de imprimir la etiqueta. Esta página no envía información a ningún servidor."

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

La versión completa y vigente es `Inventario/config.py`.
Las constantes de Cuenta y Ubicación del visor viven en `docs/visor.js`, no en `config.py`.

## 9. Reglas para todos los chats

- Python 3.10+. Dependencias: `openpyxl`, `qrcode[pil]`, `reportlab`.
  Opcional solo para pruebas: `zxing-cpp` (lee de vuelta los QR en la prueba de `generador_qr.py`).
- Nombres de funciones y variables en español, sin acentos.
- Cada módulo se puede probar solo con su bloque `if __name__ == "__main__":`.
- Cada chat parte del archivo del módulo en el proyecto (`Inventario/modulos/...`).
- Si un chat toma una decisión que afecta a otros módulos o al visor, avisa al usuario para anotarla aquí.
- Respuestas en español, paso a paso. Si no se hizo una acción o se omitió información, decirlo.

## 10. Orden de chats

1. ✅ Arquitectura + `main.py` + `config.py`
2. ✅ `lector_excel.py`
3. ✅ `limpieza.py`
4. ✅ `filtros.py` + `ids.py`
5. ✅ `enlaces.py` + `docs/visor.js` + `docs/estilos.css`
6. ✅ `generador_qr.py` · ⏳ `pdf_etiquetas.py` (siguiente)