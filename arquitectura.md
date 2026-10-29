# Arquitectura — App de inventario (Cruz Roja Guadalajara) · Versión 2

> **Para cualquier chat nuevo del proyecto:** lee este documento completo antes de escribir código.
> Este chat programa SOLO la parte que se indique, respetando los contratos de abajo.
> Si un contrato necesita cambiar, se cambia primero en el chat de arquitectura y se actualiza este documento.
>
> Este es el **único** documento de arquitectura del proyecto.
>
> **El código NO está en el proyecto de Claude.** La única versión vive en la computadora del usuario (VS Code).
> Si necesitas un archivo, **pídeselo al usuario**; no asumas su contenido ni lo reconstruyas de memoria.
> Lo que describe este documento es el contrato; el archivo que te dé el usuario manda.

Última actualización: 2026-10-28

---

## 0. Estado actual

| Parte | Estado |
|---|---|
| **Versión 1** (QR con todos los datos en el enlace + visor en GitHub Pages) | ✅ Terminada, pero **queda reemplazada** por la versión 2. **No imprimir** sus 293 etiquetas: quedarían obsoletas |
| **Versión 2** (app web con base de datos en PythonAnywhere) | ⏳ Diseño listo (este documento). Sin código todavía |

## 1. Objetivo de la versión 2

Una **aplicación web** para el inventario de equipo biomédico que se usa desde el navegador (PC o iPhone), sin terminal:

- **Buscar** un equipo por no. de serie, ID interno, tipo, marca o modelo.
- **Ver la ficha** del equipo (lo que se abre al escanear su QR).
- **Editar** la información y **registrar mantenimientos** (con eso se actualiza la fecha del último mantenimiento).
- **Componentes hijos** ligados a un equipo padre.
- **Generar el QR de un solo equipo** (o de varios para la impresión inicial).
- **Un solo QR por equipo que no se reimprime**: el QR solo lleva la dirección del equipo; lo que cambia es la ficha.

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Dónde corre | **PythonAnywhere**, plan gratuito (Beginner). No depende de una PC del hospital |
| GitHub | Solo para **guardar y subir el código**. Se puede publicar en PythonAnywhere de dos formas: con `git pull` desde la consola de PythonAnywhere o subiendo los archivos desde su página. La app no depende de GitHub para funcionar |
| Por qué no las otras opciones | PC del hospital: es vieja y la oficina va a cambiar de red. Render: se duerme y su base de datos gratis se borra a los 30 días. Supabase: se pausa tras 1 semana sin uso |
| Permiso del hospital | Ya hay permiso para guardar el inventario en la nube (es inventario de equipo, sin datos de pacientes) |
| Herramientas | **Python + Flask + SQLite**, pantallas en **HTML + CSS** (plantillas Jinja), JavaScript solo si hace falta |
| Portabilidad | El mismo código corre en la laptop del usuario (para desarrollar), en PythonAnywhere o en cualquier otro servidor |
| Qué lleva el QR | Solo la dirección de la ficha con un **código aleatorio permanente** de 8 caracteres: `https://<usuario>.pythonanywhere.com/e/k7q2xpm4`. No es adivinable, así que nadie puede recorrer el inventario cambiando el número. **No** lleva el ID interno (los `TMP-…` van a cambiar) ni el `num` consecutivo |
| Quién edita | **Solo el usuario y su jefa**, con usuario y contraseña |
| Qué es público | **Solo la ficha** que abre el QR (`/e/<codigo>`). La búsqueda y todo lo demás **piden sesión** |
| Mantenimientos | **Historial** (fecha, tipo, descripción, quién lo hizo). El "último mantenimiento preventivo" se calcula del historial, no se escribe a mano |
| Equipos en Baja | Se importan los 316 equipos, también los de Baja, porque la base de datos es el inventario completo. La búsqueda los oculta por defecto y no se les imprime QR |
| ID interno | Campo editable. Los `TMP-` se asignan **solo a equipos que no están en Baja** (los mismos 16 de la versión 1: `TMP-001`…`TMP-016`), con las reglas de la sección 7. Los equipos en Baja sin ID válido quedan con `id_interno` vacío (NULL) |
| Respaldos | El plan gratuito no tiene tareas programadas, así que habrá un botón **"Descargar respaldo"** (Excel y archivo de la base de datos) que se usa con regularidad. La copia de la base de datos se hace con `sqlite3` `backup()`, no copiando el archivo |
| Borrado de equipos | **Los equipos nunca se borran**: se marcan como Baja. Así un QR viejo nunca abre la ficha de otro equipo |
| Dueño de la cuenta | **Jefatura de Biomédica** (cuenta institucional, no personal del usuario) |
| Dominio propio | **No** se va a pagar. Los QR quedan ligados a `<usuario>.pythonanywhere.com`. Si algún día se cambia de servicio, habrá que reimprimir las etiquetas. Se le explicará al personal |
| Tamaño de etiqueta | **3×3 cm**. Con el enlace corto (~52 caracteres con el código aleatorio) el QR es versión 4 (33 módulos): QR de ~2.1–2.2 cm, módulo de ~0.63–0.67 mm (más que en la versión 1, 0.57 mm) y zona blanca de 4 módulos (~2.5 mm). El lado exacto se fija en el chat de etiquetas. **Mínimo recomendado: 2.5×2.5 cm** (módulo ~0.51 mm); a 2×2 cm el módulo baja a ~0.39 mm, por debajo del mínimo de 0.5 mm |
| Contenedores (Docker) | No aplican en PythonAnywhere. Se reconsidera solo si se cambia de servidor |
| Organización | Un archivo de Python por responsabilidad; un chat de Claude por parte (sección 10) |

### Condiciones del plan gratuito de PythonAnywhere (verificadas el 2026-10-28)

- **1 app web** en `https://<usuario>.pythonanywhere.com`, **con HTTPS** incluido.
- **512 MB de disco** (sobra para SQLite con miles de equipos) y 100 segundos de CPU al día.
- **Dominio propio: solo en planes de pago** (desde 10 USD al mes).
- **La app web vence si no se usa en 1 mes.** No se confirmó si el tráfico diario basta para mantenerla o si hay que entrar a la cuenta y pulsar un botón para extenderla. Mientras se aclara, hay que entrar a la cuenta una vez al mes.
- Sin tareas programadas, sin MySQL (en cuentas nuevas) y sin soporte directo (solo foros).

Fuentes: [Precios](https://www.pythonanywhere.com/pricing/) · [Funciones de cuentas gratuitas](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) · [Cambios a cuentas gratuitas](https://blog.pythonanywhere.com/221/) · [Dominios propios](https://help.pythonanywhere.com/pages/CustomDomains/)

## 3. Pendientes (decidir antes de imprimir etiquetas)

- [ ] **Crear la cuenta de PythonAnywhere** con el correo de la **Jefatura de Biomédica**.
- [ ] **Nombre de usuario de la cuenta**: aparece en la dirección de todos los QR y no se puede cambiar sin reimprimir. Debe ser institucional y corto (ej. `biomedicacrgdl`), de **máximo 24 caracteres**: así el enlace con el código de 8 caracteres cabe en un QR versión 4 (hasta 62 caracteres) y la etiqueta de 3×3 cm sigue siendo segura. Cuando exista, actualizar `BASE_URL` en `config.py`.
- [ ] **Guía breve para el personal** (se hace **al final**, con la app terminada) que explique las limitaciones: la ficha necesita internet, la app depende de PythonAnywhere (sin dominio propio), alguien debe renovar la cuenta cada mes y descargar respaldos.
- [ ] **Vencimiento mensual de la app**: confirmar cómo funciona; mientras tanto, recordatorio mensual para entrar a la cuenta.
- [ ] **Avisos para no dejar vencer la app** (cuando se confirme cómo funciona el vencimiento):
      un aviso dentro de la app, visible solo con sesión, que diga cuántos días faltan para renovar en PythonAnywhere
      y cuántos días lleva sin descargarse un respaldo. Limitaciones del plan gratuito: la app no puede mandar correos
      ni avisos programados (no hay tareas programadas y la salida a internet está restringida), y el aviso solo se ve
      si alguien entra a la app. Por eso se complementa con un **recordatorio de calendario** de la jefatura.
- [ ] **Fechas de mantenimiento de la jefa**: capturarlas en la app (o en el Excel antes de importarlo).

## 4. Modelo de datos (SQLite)

### Tabla `equipos`
| Campo | Tipo | Notas |
|---|---|---|
| `num` | INTEGER PRIMARY KEY AUTOINCREMENT | Número interno permanente (solo para la base de datos y las rutas con sesión). Nunca se reutiliza ni se edita. **No** va en el QR |
| `codigo` | TEXT NOT NULL UNIQUE | **Código aleatorio del QR**: 8 caracteres generados con `secrets`, con un alfabeto sin caracteres confusos (sin `0`, `o`, `1`, `l`, `i`). Se asigna al crear el equipo y **nunca cambia** |
| `id_interno` | TEXT, NULL si está vacío | `CRM GDL AA BB CC` o `TMP-NNN`. Editable. Único cuando no es NULL |
| `id_original` | TEXT | El ID tal como venía en el Excel (trazabilidad) |
| `tipo`, `marca`, `modelo`, `serie`, `area`, `estatus` | TEXT | Mismos campos que el Excel, ya limpios y normalizados |
| `padre_num` | INTEGER, nullable, FK → `equipos.num` | Si tiene valor, el equipo es **componente** de ese padre |
| `notas` | TEXT | Texto libre |
| `fila_excel` | INTEGER, nullable | Fila de origen en el Excel (solo para los importados) |
| `creado_en`, `actualizado_en` | TEXT (fecha y hora ISO) | |
| `actualizado_por` | TEXT | Usuario que hizo el último cambio |

### Tabla `mantenimientos`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `equipo_num` | INTEGER FK → `equipos.num` | |
| `fecha` | TEXT `AAAA-MM-DD` | |
| `tipo` | TEXT | `preventivo` o `correctivo` |
| `descripcion` | TEXT | |
| `realizado_por` | TEXT | Quién hizo el mantenimiento (técnico o proveedor) |
| `registrado_por` | TEXT | Usuario de la app que lo capturó |
| `creado_en` | TEXT | |

- **Último mantenimiento preventivo** = la `fecha` más reciente con `tipo = 'preventivo'` de ese equipo.
- Al importar, la columna K del Excel ("Último MPrev") se guarda como un mantenimiento preventivo con descripción "Importado del inventario de junio 2025".

### Tabla `intentos_entrada` (límite de intentos de inicio de sesión)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `usuario` | TEXT | Usuario que se intentó |
| `ip` | TEXT | |
| `fecha_hora` | TEXT ISO | |
| `exitoso` | INTEGER (0/1) | |

- Si hay `MAX_INTENTOS` fallidos para un usuario o una IP en `MINUTOS_BLOQUEO` minutos, se bloquea el inicio de sesión durante `MINUTOS_BLOQUEO` minutos.
- Se guarda en SQLite y no en memoria (por ejemplo, Flask-Limiter), porque en PythonAnywhere la memoria se pierde cada vez que se recarga la app.

### Tabla `usuarios`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `usuario` | TEXT único | |
| `nombre` | TEXT | |
| `hash_contrasena` | TEXT | Con `werkzeug.security` (nunca la contraseña en texto) |

### Componentes (padre/hijo)
- Un componente es un equipo más (tiene su propio `num`, ficha y QR si se necesita), con `padre_num` apuntando al equipo padre.
- Un solo nivel: un componente no puede tener componentes propios.
- Los equipos no se borran. Para quitar un componente de su padre se desliga (`padre_num = NULL`) o se marca como Baja.

## 5. Pantallas y rutas (Flask)

| Ruta | Quién | Qué hace |
|---|---|---|
| `GET /e/<codigo>` | **Todos (pública)** | **Ficha** (lo que abre el QR): datos, estatus con color, aviso de ID temporal, equipo padre o lista de componentes, último mantenimiento e historial. Con sesión, además muestra los botones de editar, registrar mantenimiento y QR. Código inexistente → página 404 sencilla |
| `GET/POST /entrar`, `POST /salir` | Todos | Inicio y cierre de sesión |
| `GET /` | Con sesión | Búsqueda: un cuadro de texto (serie, ID, tipo, marca, modelo) + filtros de área y estatus. Oculta Baja salvo que se pida. Sin sesión, redirige a `/entrar` |
| `GET/POST /equipo/<num>/editar` | Con sesión | Editar los datos del equipo (incluye ligarlo a un padre) |
| `GET/POST /equipo/nuevo` | Con sesión | Alta de equipo o componente (opcional: `?padre=<num>`); genera su `codigo` |
| `POST /equipo/<num>/mantenimiento` | Con sesión | Registrar un mantenimiento |
| `GET /equipo/<num>/qr.png` | Con sesión | Imagen del QR de ese equipo |
| `GET /equipo/<num>/etiqueta.pdf` | Con sesión | PDF de **una** etiqueta |
| `GET /etiquetas.pdf` | Con sesión | PDF de varias etiquetas (según filtros de búsqueda), para la impresión inicial |
| `GET /respaldo` | Con sesión | Descarga Excel con todos los equipos y mantenimientos + archivo `.db` |

**Reglas de presentación** (heredadas del visor de la versión 1):
- Campo vacío → "Sin dato". Sin mantenimiento preventivo → "Sin registro". `S/D`, `N/A`, `NA`, `-`, `--` se muestran como "Sin dato".
- Fecha `2025-01-15` → "15 de enero de 2025".
- Color del estatus: verde Funcional · ámbar En Revisión, En Mantenimiento · rojo Fuera de Servicio, No Funcional, Baja · gris cualquier otro.
- ID que empieza con `TMP-` → aviso "ID temporal".
- Cabecera: "Cruz Roja Mexicana" / "Inventario de equipo biomédico". Ubicación fija: "Delegación Guadalajara". Cuenta: "Cruz Roja Mexicana".
- Pensada primero para iPhone (la ficha se abre desde la cámara) y que también se vea bien en PC.

## 6. Estructura del código

```
inventario/
├── app.py               ← crea la app Flask y registra las rutas
├── config.py            ← constantes (sección 8)
├── db.py                ← conexión, creación de tablas y consultas
├── auth.py              ← inicio de sesión y decorador "requiere sesión"
├── qr.py                ← genera el QR de un equipo (PNG en memoria)
├── etiquetas.py         ← PDF de una o varias etiquetas
├── respaldo.py          ← exporta Excel y copia de la base de datos
├── importar_excel.py    ← script de una sola vez: carga el Excel a la base de datos
├── crear_usuario.py     ← script para dar de alta al usuario y a su jefa
├── modulos/             ← reutilizados de la versión 1 (solo los usa importar_excel.py)
│   ├── lector_excel.py
│   ├── limpieza.py
│   └── ids.py
├── templates/           ← base.html, buscar.html, ficha.html, editar.html, entrar.html
├── static/
│   └── estilos.css
├── instancia/           ← inventario.db y clave secreta (NUNCA se comparten ni se suben)
├── .gitignore           ← instancia/, *.xlsx, *.csv, *.db (crearlo ANTES del primer commit)
└── requirements.txt
```

## 7. Qué se reutiliza de la versión 1

| Archivo v1 | En la versión 2 |
|---|---|
| `lector_excel.py`, `limpieza.py` (incluida `clave()`), `ids.py` | Se reutilizan tal cual en `importar_excel.py` |
| `config.py` (normalización de marcas y tipos, `FORMATO_ID`, `PREFIJO_TMP`, `SIN_ID`) | Se conserva y se le agregan las constantes nuevas |
| `generador_qr.py` | Base de `qr.py`: mismo nivel de corrección "M", pero devuelve el PNG en memoria en lugar de guardarlo en disco |
| `pdf_etiquetas.py` | Base de `etiquetas.py`: misma lógica (zona blanca ≥ 4 módulos, QR a lado fijo con `drawImage(width=, height=)`, impresión a 100 %), ahora para una o varias etiquetas de **3×3 cm**. El ID en texto debajo debe caber a lo ancho (~7 pt) |
| `docs/visor.js`, `estilos.css` | Sus reglas de presentación y estilo pasan a `ficha.html` y `static/estilos.css` |
| `filtros.py` | Lo reemplazan las consultas SQL de `db.py` |
| `enlaces.py`, `main.py`, visor de GitHub Pages | Ya no se usan |

**Reglas de IDs que se mantienen** (de `ids.py`): "Sin información" o vacío → `TMP-NNN`; ID repetido → todas sus filas `TMP-NNN`; formato distinto → conserva su ID y solo se marca; numeración en orden de fila del Excel.

## 8. `config.py` (versión 2, generado el 2026-10-28)

El archivo completo lo tiene el usuario. Resumen:

| Grupo | Constantes |
|---|---|
| Rutas | `CARPETA_BASE` (carpeta de `config.py`), `CARPETA_INSTANCIA`, `RUTA_DB`, `RUTA_CLAVE_SECRETA`. Son objetos `Path` calculados desde `CARPETA_BASE`, para que funcionen igual en la laptop y en PythonAnywhere |
| Servidor | `BASE_URL = "https://<usuario>.pythonanywhere.com"` (pendiente), `RUTA_FICHA = "/e/"`, `ES_PRODUCCION` (variable de entorno `INVENTARIO_PRODUCCION=1`, solo en PythonAnywhere) |
| Código del QR | `LARGO_CODIGO = 8`, `ALFABETO_CODIGO = "23456789abcdefghjkmnpqrstuvwxyz"` (31 caracteres, ~8.5 × 10¹¹ combinaciones) |
| Inicio de sesión | `MAX_INTENTOS = 5`, `MINUTOS_BLOQUEO = 15` |
| Catálogos | `ESTATUS` (6 valores), `ESTATUS_EXCLUIDOS = ["baja"]` (sin TMP, sin QR, ocultos en búsqueda), `TIPOS_MANTENIMIENTO` |
| Texto fijo | `CUENTA_FIJA = "Cruz Roja Mexicana"`, `UBICACION_FIJA = "Delegación Guadalajara"` |
| Etiquetas | `TAM_ETIQUETA_CM = 3`, `TAM_QR_CM = 2.1` (se ajusta en el chat de etiquetas), `CORRECCION_QR = "M"` |
| Importación (v1) | `RUTA_EXCEL`, `HOJA`, `PRIMERA_FILA`, `COL_INI`, `COL_FIN`, `COLUMNAS`, `SIN_ID`, `FORMATO_ID`, `PREFIJO_TMP`, `DESCRIPCION_MPREV_IMPORTADO` |
| Normalización | `NORMALIZAR_MARCAS`, `NORMALIZAR_TIPOS` (sin cambios) |

**Se quitaron** (solo los usaba la versión 1): `CAMPOS_QR`, `CARPETA_SALIDA`, `CARPETA_QR`, `CSV_REVISION`, `CSV_EXCLUIDOS`, `PDF_ETIQUETAS` y la `BASE_URL` de GitHub Pages.

## 9. Reglas para todos los chats

- Python 3.10+. Dependencias: `flask`, `flask-wtf` (protección CSRF en formularios), `openpyxl`, `qrcode[pil]`, `reportlab`.
- Nombres de funciones, variables, rutas y tablas en español, sin acentos.
- **Seguridad:**
  - Contraseñas solo como hash.
  - Toda ruta que modifica datos o genera QR/PDF exige sesión.
  - Formularios con token CSRF.
  - Plantillas con autoescape (nunca `|safe` con datos del usuario).
  - Consultas SQL siempre con parámetros (`?`), nunca armando el texto con datos.
  - Cookie de sesión con `HttpOnly` y `SameSite=Lax` siempre, y `Secure` **solo si `ES_PRODUCCION`** (en la laptop no hay HTTPS y con `Secure` el inicio de sesión no funcionaría).
  - Límite de intentos de inicio de sesión guardado en SQLite (tabla `intentos_entrada`).
  - Respaldo de la base de datos con `sqlite3.Connection.backup()`, no copiando el archivo.
  - `.gitignore` con `instancia/`, el Excel y los `.db` **antes del primer commit** (el repositorio de GitHub puede ser público).
- **Nunca** compartir ni subir `instancia/` (base de datos y clave secreta) ni el Excel.
- Todo debe poder probarse primero en la laptop del usuario (`flask run`) antes de subirlo a PythonAnywhere.
- Cada chat parte de los archivos que le dé el usuario. En el proyecto de Claude solo viven `arquitectura.md` y el Excel.
- Si un chat toma una decisión que afecta a otras partes, avisa al usuario para anotarla aquí.
- Al auditar un archivo, también se buscan líneas que no cambian nada (código muerto o repetido), se eliminan y se anota cada una en el chat.
- Respuestas en español, paso a paso. Si no se hizo una acción o se omitió información, decirlo.

## 10. Orden de chats (versión 2)

1. ✅ Arquitectura versión 2 (este documento)
2. ⏳ `db.py` + `importar_excel.py` → base de datos local con los 316 equipos y sus mantenimientos
3. ⏳ `app.py` + búsqueda + ficha (solo lectura) + `templates/` + `static/estilos.css`
4. ⏳ `auth.py` + `crear_usuario.py` + edición + registro de mantenimientos + alta de equipos y componentes
5. ⏳ `qr.py` + `etiquetas.py` (QR y etiqueta individual, PDF de varias)
6. ⏳ `respaldo.py` + publicación en PythonAnywhere + prueba con el iPhone