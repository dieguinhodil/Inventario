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

Última actualización: 2026-10-30

---

## 0. Estado actual

| Parte | Estado |
|---|---|
| **Versión 1** (QR con todos los datos en el enlace + visor en GitHub Pages) | ✅ Terminada, pero **queda reemplazada** por la versión 2. **No imprimir** sus 293 etiquetas: quedarían obsoletas |
| **Versión 2** (app web con base de datos en PythonAnywhere) | ⏳ En construcción. ✅ `db.py` (2026-10-29, versión combinada, 42 pruebas). ✅ `importar_excel.py` (2026-10-29, 30 pruebas). ✅ `app.py` + búsqueda + ficha + plantillas + estilos (2026-10-30, versión combinada). ⏳ Lo demás. ⚠️ El inicio de sesión todavía es **provisional** (ver "Sesión provisional", sección 4) |
| Repositorio | `dieguinhodil/Inventario`. La versión 1 queda guardada con la etiqueta **`v1`** (commit `de4d04b`). GitHub Pages **desactivado**. Verificado que ni el Excel, ni CSV, ni `.db`, ni `instancia/` están ni estuvieron en el historial |

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
| Qué lleva el QR | Solo la dirección de la ficha con un **código aleatorio permanente** de 8 caracteres: `https://bi0medic4crm.pythonanywhere.com/e/k7q2xpm4`. No es adivinable, así que nadie puede recorrer el inventario cambiando el número. **No** lleva el ID interno (los `TMP-…` van a cambiar) ni el `num` consecutivo |
| Quién edita | **Solo el usuario y su jefa**, con usuario y contraseña. Usuarios de la app: **`jefatura`** y **`diego`** (uno por persona, para saber quién hizo cada cambio). Contraseñas de 12 caracteres o más, que no se usen en otro lado |
| Qué es público | **Solo la ficha** que abre el QR (`/e/<codigo>`). La búsqueda y todo lo demás **piden sesión** |
| Mantenimientos | **Historial** (fecha, tipo, descripción, quién lo hizo). El "último mantenimiento preventivo" se calcula del historial, no se escribe a mano |
| Zona horaria | Todas las fechas y horas (`creado_en`, `actualizado_en`, `fecha_hora`) se guardan en **hora de Ciudad de México con su desfase** (`2026-10-29T16:45:00-06:00`), porque PythonAnywhere trabaja en UTC. Constante `config.ZONA_HORARIA` |
| Búsqueda | **Sin acentos ni mayúsculas** ("electrocardiografo" encuentra "Electrocardiógrafo") y **por palabras**: cada palabra debe aparecer en alguno de los campos (serie, ID, tipo, marca, modelo). "monitor mindray" encuentra los monitores Mindray |
| Equipos en Baja | Se importan los 316 equipos, también los de Baja, porque la base de datos es el inventario completo. La búsqueda los oculta por defecto (si se filtra explícitamente por estatus "Baja", sí aparecen; los equipos **sin** estatus no se ocultan) y no se les imprime QR |
| ID interno | Campo editable. Los `TMP-` se asignan **solo a equipos que no están en Baja** (los mismos 16 de la versión 1: `TMP-001`…`TMP-016`), con las reglas de la sección 7. Los equipos en Baja sin ID válido quedan con `id_interno` vacío (NULL) |
| Respaldos | El plan gratuito no tiene tareas programadas, así que habrá un botón **"Descargar respaldo"** (Excel y archivo de la base de datos) que se usa con regularidad. La copia de la base de datos se hace con `sqlite3` `backup()`, no copiando el archivo |
| Borrado de equipos | **Los equipos nunca se borran**: se marcan como Baja. Así un QR viejo nunca abre la ficha de otro equipo |
| Importación única | Los códigos de los QR se generan al importar. **Una vez impresas las etiquetas, no se vuelve a importar el Excel**: los códigos cambiarían y todas las etiquetas dejarían de funcionar. `importar_excel.py` se niega a correr si la base ya tiene equipos. Antes de imprimir sí se puede repetir (borrando a mano `instancia/inventario.db`) |
| Dueño de la cuenta | **Jefatura de Biomédica** (cuenta institucional, no personal del usuario) |
| Dominio propio | **No** se va a pagar. Los QR quedan ligados a `bi0medic4crm.pythonanywhere.com`. Si algún día se cambia de servicio, habrá que reimprimir las etiquetas. Se le explicará al personal |
| Tamaño de etiqueta | **3×3 cm**. Con el enlace corto (50 caracteres: `https://bi0medic4crm.pythonanywhere.com/e/` + código de 8) el QR es versión 4 (33 módulos): QR de ~2.1–2.2 cm, módulo de ~0.63–0.67 mm (más que en la versión 1, 0.57 mm) y zona blanca de 4 módulos (~2.5 mm). El lado exacto se fija en el chat de etiquetas. **Mínimo recomendado: 2.5×2.5 cm** (módulo ~0.51 mm); a 2×2 cm el módulo baja a ~0.39 mm, por debajo del mínimo de 0.5 mm |
| Contenedores (Docker) | No aplican en PythonAnywhere. Se reconsidera solo si se cambia de servidor |
| Organización | Un archivo de Python por responsabilidad; un chat de Claude por parte (sección 10) |

### Condiciones del plan gratuito de PythonAnywhere (verificadas el 2026-10-28)

- **1 app web** en `https://bi0medic4crm.pythonanywhere.com`, **con HTTPS** incluido.
- **512 MB de disco** (sobra para SQLite con miles de equipos) y 100 segundos de CPU al día.
- **Dominio propio: solo en planes de pago** (desde 10 USD al mes).
- **La app web vence si no se usa en 1 mes.** No se confirmó si el tráfico diario basta para mantenerla o si hay que entrar a la cuenta y pulsar un botón para extenderla. Mientras se aclara, hay que entrar a la cuenta una vez al mes.
- Sin tareas programadas, sin MySQL (en cuentas nuevas) y sin soporte directo (solo foros).

Fuentes: [Precios](https://www.pythonanywhere.com/pricing/) · [Funciones de cuentas gratuitas](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) · [Cambios a cuentas gratuitas](https://blog.pythonanywhere.com/221/) · [Dominios propios](https://help.pythonanywhere.com/pages/CustomDomains/)

## 3. Pendientes (decidir antes de imprimir etiquetas)

- [x] **Cuenta de PythonAnywhere creada** (2026-10-29), a nombre de la Jefatura de Biomédica.
- [x] **Usuario de la cuenta: `Bi0medic4CRM`** (con cero y cuatro) → dirección **`https://bi0medic4crm.pythonanywhere.com`**. Enlace completo de un QR: 50 caracteres → QR versión 4 (33 módulos). Ya está en `BASE_URL`. No se puede cambiar sin reimprimir todas las etiquetas.
- [ ] **Guía breve para el personal** (se hace **al final**, con la app terminada) que explique las limitaciones: la ficha necesita internet, la app depende de PythonAnywhere (sin dominio propio), alguien debe renovar la cuenta cada mes y descargar respaldos.
- [ ] **Vencimiento mensual de la app**: confirmar cómo funciona; mientras tanto, recordatorio mensual para entrar a la cuenta.
- [ ] **Avisos para no dejar vencer la app** (cuando se confirme cómo funciona el vencimiento):
      un aviso dentro de la app, visible solo con sesión, que diga cuántos días faltan para renovar en PythonAnywhere
      y cuántos días lleva sin descargarse un respaldo. Limitaciones del plan gratuito: la app no puede mandar correos
      ni avisos programados (no hay tareas programadas y la salida a internet está restringida), y el aviso solo se ve
      si alguien entra a la app. Por eso se complementa con un **recordatorio de calendario** de la jefatura.
- [ ] **Fechas de mantenimiento de la jefa**: capturarlas en el Excel **antes** de la importación definitiva (la que se hace justo antes de imprimir), o después en la app. Una vez impresas las etiquetas ya no se puede reimportar.
- [ ] **Bloqueo por IP compartida** (decidido 2026-10-30, falta programarlo en el chat 4): bloquear por **usuario** con `MAX_INTENTOS = 5` y por **IP** con `MAX_INTENTOS_IP = 20` (ya están en `config.py`). En el hospital `jefatura` y `diego` salen a internet con la misma IP; así un error de uno no bloquea al otro. Requiere cambiar `db.minutos_bloqueado`, que hoy usa `MAX_INTENTOS` para los dos casos.
- [ ] **Cambiar contraseña**: no está en `db.py`. Se agrega en el chat 4 (en `crear_usuario.py` y/o una pantalla para el usuario con sesión).
- [ ] **Ocultar Notas y "Realizado por" en la ficha pública** (decidido 2026-10-30, falta programarlo): mover las **Notas** y la columna **"Realizado por"** del historial a lo que solo se ve **con sesión** en `ficha.html` (con `hay_sesion`), y ajustar `pruebas_app.py`. Se hace en el chat 4, junto con la sesión real.
- [ ] **Logo de la cabecera:** confirmar con la jefatura si se puede usar la cruz roja dibujada con CSS o si hay que pedir el logotipo oficial de Cruz Roja Mexicana. El uso del emblema está regulado.
- [ ] **`requirements.txt`**: ningún chat lo tiene asignado. Se genera con `pip freeze > requirements.txt` en la laptop y se revisa en el chat 6 antes de publicar. Mínimo: `flask`, `flask-wtf`, `openpyxl`, `qrcode[pil]`, `reportlab` (más `tzdata` si alguien usa Windows).

## 4. Modelo de datos (SQLite)

### Tabla `equipos`
| Campo | Tipo | Notas |
|---|---|---|
| `num` | INTEGER PRIMARY KEY AUTOINCREMENT | Número interno permanente (solo para la base de datos y las rutas con sesión). Nunca se reutiliza ni se edita. **No** va en el QR |
| `codigo` | TEXT NOT NULL UNIQUE | **Código aleatorio del QR**: 8 caracteres generados con `secrets`, con un alfabeto sin caracteres confusos (sin `0`, `o`, `1`, `l`, `i`). Se asigna al crear el equipo y **nunca cambia** |
| `id_interno` | TEXT UNIQUE COLLATE NOCASE, NULL si está vacío | `CRM GDL AA BB CC` o `TMP-NNN`. Editable. Único cuando no es NULL, sin distinguir mayúsculas |
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
- La `fecha` **no puede ser posterior a hoy** (evita errores de captura). El `tipo` se guarda en minúsculas.
- Registrar un mantenimiento **no** cambia `actualizado_en` / `actualizado_por` del equipo; el mantenimiento tiene su propio `creado_en` y `registrado_por`.
- Al importar, la columna K del Excel ("Último MPrev") se guarda como un mantenimiento preventivo con descripción "Importado del inventario de junio 2025".

### Tabla `intentos_entrada` (límite de intentos de inicio de sesión)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `usuario` | TEXT | Usuario que se intentó |
| `ip` | TEXT | |
| `fecha_hora` | TEXT ISO | |
| `exitoso` | INTEGER (0/1) | |

- Si hay `MAX_INTENTOS` (5) fallidos para un **usuario**, o `MAX_INTENTOS_IP` (20) para una **IP**, en `MINUTOS_BLOQUEO` minutos, se bloquea el inicio de sesión durante `MINUTOS_BLOQUEO` minutos. **No es una lista de redes permitidas:** se puede entrar desde cualquier red; solo se frena a quien falla muchas veces.
- Se guarda en SQLite y no en memoria (por ejemplo, Flask-Limiter), porque en PythonAnywhere la memoria se pierde cada vez que se recarga la app.
- El bloqueo dura `MINUTOS_BLOQUEO` minutos **desde el fallo con el que se llegó a `MAX_INTENTOS`**.
- Un inicio de sesión **exitoso reinicia** la cuenta de fallos de ese usuario o IP.
- Los intentos de más de 30 días se borran solos al registrar uno nuevo.
- **`auth.py` no debe revisar la contraseña ni registrar intentos mientras haya bloqueo** (si los registra, el bloqueo se alarga).

### Tabla `usuarios`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | INTEGER PK | |
| `usuario` | TEXT único, `COLLATE NOCASE` | "Diego" y "diego" son el mismo usuario |
| `nombre` | TEXT | |
| `hash_contrasena` | TEXT | Con `werkzeug.security` (nunca la contraseña en texto) |

### Componentes (padre/hijo)
- Un componente es un equipo más (tiene su propio `num`, ficha y QR si se necesita), con `padre_num` apuntando al equipo padre.
- Un solo nivel: un componente no puede tener componentes propios.
- Los equipos no se borran. Para quitar un componente de su padre se desliga (`padre_num = NULL`) o se marca como Baja.
- `db.py` valida: que el padre exista, que el padre no sea a su vez componente, que un equipo no sea su propio padre y que un equipo con componentes no se vuelva componente. **No** valida que el padre esté en Baja.

### Contrato de `db.py` ✅ (programado 2026-10-29, versión combinada, 42 pruebas)

| Función | Uso |
|---|---|
| `conectar(ruta=None)`, `crear_tablas(conexion)`, `transaccion(conexion)` | Conexión y estructura. `conectar()` registra en SQLite la función `sin_acentos()` para la búsqueda |
| `obtener_equipo_por_codigo`, `obtener_equipo_por_num`, `listar_componentes` | Ficha |
| `buscar_equipos(conexion, texto, area, estatus, incluir_baja)`, `valores_distintos(conexion, campo)` | Búsqueda, filtros, etiquetas, respaldo |
| `insertar_equipo(conexion, datos, usuario) -> num`, `actualizar_equipo(conexion, num, cambios, usuario)` | Alta y edición. `insertar_equipo` devuelve el `num` del equipo nuevo (**no hay función de borrar**) |
| `registrar_mantenimiento(conexion, equipo_num, fecha, tipo, descripcion, realizado_por, registrado_por)`, `listar_mantenimientos(conexion, equipo_num=None)`, `ultimo_preventivo` | Mantenimientos |
| `crear_usuario(conexion, usuario, nombre, hash_contrasena)`, `obtener_usuario` | Usuarios (el hash lo hace quien llama, con `werkzeug.security`) |
| `registrar_intento(conexion, usuario, ip, exitoso)`, `minutos_bloqueado(conexion, usuario, ip)` | Límite de intentos |
| `respaldar_db(conexion, ruta_destino)` | Respaldo con `backup()`. Escribe en un archivo: `respaldo.py` debe usar un archivo temporal para mandarlo como descarga |
| `ahora()`, `hoy()`, `normalizar_texto()`, `ErrorDatos` | Utilidades |

- **Sin Flask:** `db.py` no depende de Flask. `app.py` abre una conexión por petición (`flask.g`) con `db.conectar()` y la cierra en `teardown_appcontext`.
- **Transacciones:** cada función que escribe guarda sus cambios sola. `importar_excel.py` debe envolver todo en `with db.transaccion(conexion):`, para que se guarden los 316 equipos o ninguno.
- **Errores:** los datos inválidos lanzan `db.ErrorDatos` con un mensaje en español, listo para mostrarse al usuario; `app.py` lo atrapa y lo muestra tal cual en el formulario.
- **Índices:** en `padre_num`, `mantenimientos(equipo_num, fecha)` e `intentos_entrada(fecha_hora)`. `codigo` e `id_interno` ya lo tienen por ser `UNIQUE`. No hay índice en `serie` porque `LIKE '%texto%'` no lo usaría (con cientos de equipos no hace falta).
- **Zona horaria:** usa `config.ZONA_HORARIA` (verificado en el código el 2026-10-30). Las fechas y horas se comparan como texto; funciona porque Ciudad de México ya no cambia de horario (el desfase siempre es `-06:00`).
- `obtener_equipo_por_codigo` pasa el código a minúsculas, así que un código escrito en mayúsculas también se encuentra.

### `importar_excel.py` ✅ (programado 2026-10-29, versión combinada, 30 pruebas)
- Todo dentro de `with db.transaccion(conexion):`.
- Asignar `TMP-` solo a equipos que no están en Baja (sección 2).
- **Estatus con la forma exacta de `config.ESTATUS`** ("Baja", no "baja"), para que el filtro de estatus no muestre dos opciones. Al 2026-10-29 el Excel trae los 6 estatus escritos de forma uniforme, pero la regla protege contra capturas futuras.
- Generar el `codigo` aleatorio de cada equipo (lo hace `insertar_equipo` o el importador, según el contrato de `db.py`).
- Columna K → un mantenimiento preventivo con `config.DESCRIPCION_MPREV_IMPORTADO`.
- **Fechas aceptadas en la columna K** (las de `limpieza.limpiar_fecha`): celda de fecha, número serial de Excel (1990–2100), `AAAA-MM-DD`, `DD/MM/AAAA`, `DD-MM-AAAA`, `DD.MM.AAAA` y `DD/MM/AA`. La columna K se valida **antes** de `limpieza.limpiar()`, porque esta deja vacía una fecha que no reconoce en lugar de detenerse: el importador se detiene y avisa la fila.
- Reutiliza `lector_excel.py`, `limpieza.py` e `ids.py` **sin cambios**.
- También rechaza fechas de la columna K **posteriores a hoy**, y muestra **todas** las filas con problema de una vez.
- Los datos importados quedan con `actualizado_por` y `registrado_por` = **`importacion`** (no es un usuario de la app).
- Un estatus que no esté en `config.ESTATUS` se guarda tal cual y se avisa en el resumen.
- Se niega a correr si la base ya tiene equipos (ver "Importación única", sección 2).

**Resultado verificado con `INVENTARIO_JUNIO_2025`** (cotejado contra el Excel el 2026-10-30):

| Concepto | Cantidad |
|---|---|
| Equipos importados | 316 |
| `TMP-001`…`TMP-016` (los mismos de la versión 1) | 16 |
| Equipos en Baja sin ID → `id_interno` NULL | 15 |
| Equipos en Baja que conservan su ID (2 válidos + 6 `CRMG 023…` con formato distinto) | 8 |
| Mantenimientos preventivos importados (147 de equipos activos + 2 de equipos en Baja) | 149 |

### `app.py` y plantillas ✅ (chat 3, 2026-10-30, versión combinada)

- **Pruebas:** `pruebas_app.py`. Correr con `python3 -m unittest pruebas_app -v` (usa una base y una clave temporales). Probado en pantalla de iPhone (393 px, WebKit) y de PC (1280 px, Chromium), sin errores en consola ni desplazamiento horizontal. **Probado con una base de prueba, no con la base real de 316 equipos.**
- **Arranque:** laptop `flask --app app run`. En PythonAnywhere (chat 6), el archivo WSGI pone `os.environ["INVENTARIO_PRODUCCION"] = "1"` **antes** de `from app import app as application`.
- **Fábrica** `crear_app(ajustes=None)` y `app = crear_app()` al final. `ajustes` permite cambiar `RUTA_DB`, `RUTA_CLAVE_SECRETA`, `ES_PRODUCCION` y `SESION_PROVISIONAL` (lo usan las pruebas).
- **Al arrancar** (y también al hacer `import app`): crea las tablas si no existen (`db.crear_tablas`, no borra datos) y la clave secreta si no existe. Esto **no estorba** a `importar_excel.py`, que solo se niega si la base **tiene equipos**, no si el archivo existe (verificado en su código el 2026-10-30).
- **Clave secreta:** la crea `app.py` (`cargar_clave_secreta`) en `config.RUTA_CLAVE_SECRETA`: 64 caracteres hexadecimales con `secrets`, permisos 600, sin sobrescribir si otro proceso la acaba de crear. Si se borra, se genera otra y se cierran todas las sesiones (no se pierden datos). Si está vacía o tiene menos de 32 caracteres, la app no arranca y avisa. En PythonAnywhere **se genera sola**; no se sube desde la laptop.
- **Conexión por petición:** `obtener_conexion()` en `flask.g` y `cerrar_conexion` en `teardown_appcontext`.
- **Cookie de sesión:** `HttpOnly`, `SameSite=Lax`, `Secure` solo si `ES_PRODUCCION`. ⚠️ Se **asigna** directamente: `app.config.setdefault("SESSION_COOKIE_SECURE", ...)` **no funciona** porque Flask ya trae ese valor en `False`.
- **CSRF:** `CSRFProtect` ya está activo (variable `csrf`). Cada formulario POST lleva `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **`MAX_CONTENT_LENGTH` = 1 MB.**
- **Nombres para `url_for`:** `buscar` (`/`) y `ficha` (`/e/<codigo>`, armada con `config.RUTA_FICHA`).
- **Errores 404 y 500:** `templates/error.html`, sin detalles técnicos.
- **Búsqueda (`GET /`):** parámetros `q`, `area`, `estatus` y `baja=1` ("Incluir equipos en Baja"). `q` se corta a 100 caracteres (`LARGO_MAX_BUSQUEDA`). Sin texto ni filtros muestra todo el inventario sin las Bajas (unos 300; no hace falta paginar). El filtro de estatus ofrece `config.ESTATUS` en su orden y después cualquier otro estatus que exista en la base. Cada resultado es una tarjeta que lleva a la ficha, con estatus en color, aviso "ID temporal" y marca "Componente".
- **Ficha (`GET /e/<codigo>`):** antes de consultar la base revisa que el código tenga 8 caracteres del alfabeto; si no, 404 (acepta mayúsculas).
  - **Pública:** tipo, marca y modelo; estatus con color; aviso de Baja; aviso de ID temporal; ID, serie, tipo, marca, modelo y área; ubicación y cuenta fijas; último preventivo; equipo padre o componentes (con enlace); historial (fecha, tipo, descripción); fecha de la última actualización.
  - **Solo con sesión:** **Notas**, **"Realizado por"** y "Registrado por" en el historial, y la sección "Datos internos" (num, código del QR, ID original, fila del Excel, fecha de alta, "Actualizado por").
  - ⚠️ Decidido el 2026-10-30: Notas y "Realizado por" pasan a solo con sesión. **El código del chat 3 todavía los muestra en público**; lo cambia el chat 4. Se ocultan porque los nombres de usuario facilitarían adivinar con qué usuario entrar, y el `num` no debe ser público.

### Sesión provisional → instrucciones para el chat 4 ⚠️

Mientras no exista `auth.py`, `app.py` tiene un bloque **"Sesión: PROVISIONAL hasta el chat 4"**:

| Pieza | Qué hace hoy | Qué debe hacer el chat 4 |
|---|---|---|
| `requiere_sesion(vista)` | Decorador **vacío**; ya está puesto en la búsqueda | Programarlo en `auth.py` (manda a `/entrar` a quien no tenga sesión) y en `app.py` usar `from auth import requiere_sesion` |
| `hay_sesion()` | Devuelve `True` mientras `SESION_PROVISIONAL` esté activo | Que diga si de verdad hay un usuario con sesión. **Conservar el nombre `hay_sesion`**: lo usan las plantillas |
| `app.config["SESION_PROVISIONAL"] = True` | Muestra el aviso "Modo de desarrollo" en todas las páginas | **Borrarlo**, junto con el bloque provisional, la variable `sesion_provisional` de las plantillas y el aviso en `base.html` |
| Candado de producción en `crear_app()` | Si `ES_PRODUCCION` y `SESION_PROVISIONAL` → la app **se niega a arrancar** (`RuntimeError`) | Quitarlo cuando ya haya inicio de sesión |

- Hay marcadores `{# ... #}` en `base.html` ("Nuevo equipo", "Respaldo", "Salir") y en `ficha.html` (Editar, Registrar mantenimiento, Agregar componente, QR/etiqueta) para los botones de los chats 4 y 5.
- Las pruebas `PruebasFichaSinSesion` usan `SESION_PROVISIONAL=False`; el chat 4 las adapta.
- **Hoy la búsqueda está abierta.** Es aceptable solo en la laptop; el candado impide publicarla así.
- **IP real en PythonAnywhere (verificado 2026-10-30):** `request.remote_addr` devuelve la IP del balanceador de carga de PythonAnywhere, **no** la del usuario. La IP real llega en la cabecera **`X-Real-IP`** ([ayuda de PythonAnywhere](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses/)). `auth.py` debe usar `request.headers.get("X-Real-IP")` **solo si `ES_PRODUCCION`**, y `request.remote_addr` en la laptop. Si usara `remote_addr` en PythonAnywhere, todos compartirían la misma IP y un bloqueo por IP los bloquearía a todos.
- Sin sesión, `/` redirige a `/entrar`. La ficha pública no enlaza a la búsqueda.

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

**Cómo quedó implementado (chat 3):**
- Filtros de Jinja que deben usar **todas** las plantillas: `| sin_dato`, `| fecha_larga` (fecha y hora en hora de Ciudad de México, "29 de octubre de 2026, 16:45"; vacío → "Sin registro" o el texto que se le pase), `| clase_estatus` (`verde`, `ambar`, `rojo`, `gris`). Pruebas `is tmp` e `is baja`.
- `templates/macros.html`: `estatus(...)`, `nombre_equipo(...)`, `id_interno(...)`. Se usan con `{% import "macros.html" as m %}`.
- **Logo en la cabecera** (agregado 2026-10-30): cruz roja sobre un cuadro blanco, dibujada solo con CSS (sin archivos de imagen).
  ⚠️ El chat 3 había decidido no usar el emblema porque su uso está regulado. Pendiente confirmar con la jefatura (o el área de comunicación de la delegación) si esta cruz dibujada es aceptable o si hay que usar el **logotipo oficial** de Cruz Roja Mexicana (sección 3).
- **Interruptor de modo claro / oscuro** en la cabecera, en todas las páginas (también en la ficha pública). Sin elección, sigue el modo del teléfono o la PC; la elección se guarda en ese navegador (`localStorage`). Vive en `static/tema.js`.
- Todas las páginas llevan `<meta name="robots" content="noindex, nofollow">` para que los buscadores no las indexen.
- Sin fuentes ni archivos externos (carga rápida con red lenta).

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
├── crear_usuario.py     ← script para dar de alta a los usuarios `jefatura` y `diego`
├── pruebas_app.py       ← pruebas de app.py: python3 -m unittest pruebas_app -v (usa una base temporal)
├── modulos/             ← reutilizados de la versión 1 (solo los usa importar_excel.py)
│   ├── lector_excel.py
│   ├── limpieza.py
│   └── ids.py
├── templates/           ← base.html, macros.html, buscar.html, ficha.html, error.html
│                           (entrar.html y editar.html los hace el chat 4)
├── static/
│   ├── estilos.css
│   └── tema.js          ← interruptor claro/oscuro (único JavaScript de la app; archivo aparte por la CSP)
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

**Cómo se aplican en la versión 2:**
- **Equipos activos (no Baja):** `ids.asignar_ids()` se aplica solo a ellos. Así salen los mismos 16 TMP de la versión 1.
- **Equipos en Baja:** los resuelve `importar_excel.py`. Sin ID o con ID repetido en **todo** el inventario → `NULL`. ID único (válido o con formato distinto) → lo conserva. Nunca reciben TMP.
- **Así quedó en el código** (`importar_excel.asignar_id_interno`, verificado el 2026-10-30), que combina las dos descripciones de los agentes:
  1. `ids.asignar_ids(activos)` da el `id_interno` y el motivo de los equipos activos (los mismos 16 TMP).
  2. `ids.asignar_ids(todas_las_filas)` se usa **solo para los equipos en Baja**: si su motivo es "sin ID" o "repetido" (contando contra todo el inventario) → `NULL`; si no, conservan su ID.
  - Consecuencia: si un equipo activo y uno en Baja tuvieran el mismo ID, el activo lo conserva y el de Baja queda en `NULL`. Así nunca se repite un ID. Hoy no pasa en el Excel.

## 8. `config.py` (versión 2, generado el 2026-10-28, actualizado el 2026-10-29)

El archivo completo lo tiene el usuario. Resumen:

| Grupo | Constantes |
|---|---|
| Rutas | `CARPETA_BASE` (carpeta de `config.py`), `CARPETA_INSTANCIA`, `RUTA_DB`, `RUTA_CLAVE_SECRETA`. Son objetos `Path` calculados desde `CARPETA_BASE`, para que funcionen igual en la laptop y en PythonAnywhere |
| Zona horaria | `ZONA_HORARIA = ZoneInfo("America/Mexico_City")` (agregada 2026-10-29) |
| Servidor | `BASE_URL = "https://bi0medic4crm.pythonanywhere.com"`, `RUTA_FICHA = "/e/"`, `ES_PRODUCCION` (variable de entorno `INVENTARIO_PRODUCCION=1`, solo en PythonAnywhere) |
| Código del QR | `LARGO_CODIGO = 8`, `ALFABETO_CODIGO = "23456789abcdefghjkmnpqrstuvwxyz"` (31 caracteres, ~8.5 × 10¹¹ combinaciones) |
| Inicio de sesión | `MAX_INTENTOS = 5` (por usuario), `MAX_INTENTOS_IP = 20` (por IP, agregada 2026-10-30), `MINUTOS_BLOQUEO = 15` |
| Catálogos | `ESTATUS` (6 valores), `ESTATUS_EXCLUIDOS = ["baja"]` (sin TMP, sin QR, ocultos en búsqueda), `TIPOS_MANTENIMIENTO` |
| Texto fijo | `CUENTA_FIJA = "Cruz Roja Mexicana"`, `UBICACION_FIJA = "Delegación Guadalajara"` |
| Etiquetas | `TAM_ETIQUETA_CM = 3`, `TAM_QR_CM = 2.1` (se ajusta en el chat de etiquetas), `CORRECCION_QR = "M"` |
| Importación (v1) | `RUTA_EXCEL`, `HOJA`, `PRIMERA_FILA`, `COL_INI`, `COL_FIN`, `COLUMNAS`, `SIN_ID`, `FORMATO_ID`, `PREFIJO_TMP`, `DESCRIPCION_MPREV_IMPORTADO` |
| Normalización | `NORMALIZAR_MARCAS`, `NORMALIZAR_TIPOS` (sin cambios) |

**Se quitaron** (solo los usaba la versión 1): `CAMPOS_QR`, `CARPETA_SALIDA`, `CARPETA_QR`, `CSV_REVISION`, `CSV_EXCLUIDOS`, `PDF_ETIQUETAS` y la `BASE_URL` de GitHub Pages.

## 9. Reglas para todos los chats

- Python 3.10+. Dependencias: `flask`, `flask-wtf` (protección CSRF en formularios), `openpyxl`, `qrcode[pil]`, `reportlab`.
  Si alguien desarrolla en **Windows**, agregar `tzdata` (lo necesita `zoneinfo`); en macOS y PythonAnywhere no hace falta.
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
- Todo debe poder probarse primero en la laptop del usuario (`flask --app app run`) antes de subirlo a PythonAnywhere.
- **Pruebas:** antes de subir cambios a PythonAnywhere, correr `python3 -m unittest pruebas_app` en la laptop. Cada chat que agregue rutas agrega sus pruebas a ese archivo o a uno nuevo `pruebas_<parte>.py`.
- **Cabeceras de seguridad (desde el chat 3):** `app.py` manda en todas las respuestas `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y `Referrer-Policy: same-origin`. Por eso:
  - **Nada de `<script>` ni `style="..."` dentro del HTML**: el navegador los bloquea.
  - El JavaScript va en archivos `static/*.js` y los estilos en `static/estilos.css`.
  - Imágenes solo del mismo sitio o `data:` (la ruta `/equipo/<num>/qr.png` funciona sin cambios).
  - La política está en `POLITICA_CONTENIDO` de `app.py`; si un chat necesita cambiarla, se acuerda aquí.
- Cada chat parte de los archivos que le dé el usuario. En el proyecto de Claude solo viven `arquitectura.md` y el Excel.
- Si un chat toma una decisión que afecta a otras partes, avisa al usuario para anotarla aquí.
- Al auditar un archivo, también se buscan líneas que no cambian nada (código muerto o repetido), se eliminan y se anota cada una en el chat.
- Respuestas en español, paso a paso. Si no se hizo una acción o se omitió información, decirlo.

## 10. Orden de chats (versión 2)

1. ✅ Arquitectura versión 2 (este documento)
2. ✅ `db.py` (42 pruebas) + `importar_excel.py` (30 pruebas), versiones combinadas → base de datos local con los 316 equipos y sus mantenimientos
3. ✅ `app.py` + búsqueda + ficha (solo lectura) + `templates/` (base, macros, buscar, ficha, error) + `static/estilos.css` + `pruebas_app.py` (versión combinada, probada en WebKit/iPhone y Chromium)
4. ⏳ `auth.py` + `crear_usuario.py` + edición + registro de mantenimientos + alta de equipos y componentes. **Tareas pendientes que le tocan (de los chats anteriores):** (1) cambiar `db.minutos_bloqueado` para usar `MAX_INTENTOS_IP` en el caso de la IP; (2) usar `X-Real-IP` en PythonAnywhere; (3) ocultar Notas y "Realizado por" sin sesión en `ficha.html` y ajustar `pruebas_app.py`; (4) cambiar contraseña. **Al terminar `auth.py`:** reemplazar `requiere_sesion` y `hay_sesion` provisionales de `app.py` y quitar `SESION_PROVISIONAL` (mientras exista, la app se niega a arrancar en PythonAnywhere). Ver "Sesión provisional" en la sección 4
5. ⏳ `qr.py` + `etiquetas.py` (QR y etiqueta individual, PDF de varias)
6. ⏳ `respaldo.py` + publicación en PythonAnywhere + prueba con el iPhone