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

Última actualización: 2026-11-06

---

## 0. Estado actual

| Parte | Estado |
|---|---|
| **Versión 1** (QR con todos los datos en el enlace + visor en GitHub Pages) | ✅ Terminada, pero **queda reemplazada** por la versión 2. **No imprimir** sus 293 etiquetas: quedarían obsoletas |
| **Versión 2** (app web con base de datos en PythonAnywhere) | ⏳ En construcción. ✅ `db.py` (2026-10-29, versión combinada, 42 pruebas). ✅ `importar_excel.py` (2026-10-29, 30 pruebas). ✅ `app.py` + búsqueda + ficha + plantillas + estilos (2026-10-30). ✅ `auth.py` + `crear_usuario.py` + edición + alta + mantenimientos + cambio de contraseña (2026-10-31, versión combinada, 110 pruebas). ✅ `qr.py` + `etiquetas.py` (2026-11-04, 34 pruebas). ⏳ Respaldo y publicación (chat 6) |
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
| De qué base salen las etiquetas | **Solo de la base de PythonAnywhere (producción).** Cada base genera sus propios códigos de QR al importar, así que una etiqueta impresa desde la base de la laptop **no funcionaría** en la app publicada. La base de la laptop es solo para pruebas |
| Dueño de la cuenta | **Jefatura de Biomédica** (cuenta institucional, no personal del usuario) |
| Dominio propio | **No** se va a pagar. Los QR quedan ligados a `bi0medic4crm.pythonanywhere.com`. Si algún día se cambia de servicio, habrá que reimprimir las etiquetas. Se le explicará al personal |
| Tamaño de etiqueta | **3×3 cm**. Enlace de 50 caracteres (`https://bi0medic4crm.pythonanywhere.com/e/` + código de 8) → QR versión 4 (33 módulos). **`TAM_QR_CM = 2.1` fijo:** módulo de 0.636 mm y zona blanca de 4 módulos (2.55 mm) por los cuatro lados. Mínimo recomendado si algún día se achica: 2.5×2.5 cm (módulo ~0.51 mm) |
| Contenido de la etiqueta | **Solo el QR y el ID interno** debajo (Helvetica Bold 7 pt; baja hasta 5 pt si el ID es largo). No cabe otro texto sin achicar el QR |
| Formatos de impresión | Todavía no se sabe con qué se imprimirá, así que hay dos: **PDF de una etiqueta = página de 3×3 cm** (impresora de etiquetas) y **hoja carta con 6×8 = 48 etiquetas** con líneas de corte tenues (impresora normal; 293 equipos ≈ 7 hojas). Siempre a **tamaño real (100 %)** |
| Equipos que no llevan etiqueta | **En Baja** (no aparece el botón; sus rutas responden 409; el PDF de varias los excluye siempre, aunque se filtre por Baja) y **sin ID interno** (no se imprime una etiqueta sin texto; la pantalla explica y manda a "Editar"). Tampoco si el ID no cabe ni a 5 pt o tiene caracteres que la fuente del PDF no puede escribir |
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
- [x] **Bloqueo por IP compartida** (2026-10-31): usuario con `MAX_INTENTOS = 5`, IP con `MAX_INTENTOS_IP = 20` en `db.minutos_bloqueado`.
- [x] **Cambiar contraseña** (2026-10-31): pantalla `/contrasena` ("Cuenta") y `crear_usuario.py --cambiar`.
- [x] **Notas y "Realizado por" solo con sesión** (2026-10-31).
- [x] **Logo y nombre de la cabecera como enlace a la búsqueda, solo con sesión** (2026-10-31).
- [ ] **Logo de la cabecera:** confirmar con la jefatura si se puede usar la cruz roja dibujada con CSS o si hay que pedir el logotipo oficial de Cruz Roja Mexicana. El uso del emblema está regulado.
- [ ] **`requirements.txt`**: ningún chat lo tiene asignado. Se genera con `pip freeze > requirements.txt` en la laptop y se revisa en el chat 6 antes de publicar. Mínimo: `flask`, `flask-wtf`, `openpyxl`, `qrcode[pil]`, `reportlab` (más `tzdata` si alguien usa Windows).
- [x] **Usuarios creados en la laptop** (confirmado el 2026-11-06).
- [ ] **Crear los usuarios en PythonAnywhere** (chat 6), en una consola Bash: `python3 crear_usuario.py jefatura "Jefatura de Biomédica"` y `python3 crear_usuario.py diego "Diego"`. Los de la laptop no se suben: cada lugar tiene su propia base de datos.
- [x] **Pruebas corridas en la laptop con los archivos reales** (confirmado por el usuario el 2026-11-06).
- [ ] **Probar en un iPhone real** (Safari): en especial el campo de fecha del mantenimiento. El chat 4 solo probó en Chrome.
- [ ] **⚠️ Decidir (usuario y jefa): ¿`TMP-NNN` automático para equipos nuevos sin ID?** (el siguiente después de `TMP-016`). Hoy quedan con el ID vacío, y desde el chat 5 **un equipo sin ID no puede imprimir etiqueta**. Mientras no se decida, cada equipo nuevo necesita que alguien le capture un ID a mano antes de etiquetarlo.
- [x] **`HORAS_SESION = 12` movido a `config.py`** (chat 5, 2026-11-04). `app.py` usa `config.HORAS_SESION`.
- [ ] **Detalle menor:** al dar de alta un componente, "Cancelar" lleva a la búsqueda; podría llevar a la ficha del padre.
- [ ] **Hojas de etiquetas precortadas:** cuando se sepa qué material se usará, si son hojas adhesivas precortadas, ajustar la cuadrícula de `etiquetas.pdf_hoja` a sus medidas (márgenes y separación entre etiquetas).
- [ ] **Prueba real de impresión:** imprimir una hoja a 100 %, medir que cada etiqueta mida 3 cm y escanear varias con el iPhone (con poca luz y desde distintos ángulos).
- [ ] **Importación definitiva en PythonAnywhere** (chat 6): elegir una de dos formas, **una sola vez** y antes de imprimir: (a) subir el Excel a PythonAnywhere, correr `importar_excel.py` en su consola Bash y borrar el Excel de ahí; o (b) importar en la laptop y subir ese `inventario.db` a `instancia/` de PythonAnywhere antes de que nadie use la app. Después, las etiquetas se imprimen **solo desde la app publicada**.
- [ ] **Respaldos (usuario y jefa):** decidir **dónde** se guardan los respaldos descargados (por ejemplo, una carpeta de la jefatura) y **cada cuánto** se descargan (se sugiere cada semana). El `.db` tiene los hashes de las contraseñas: no dejarlo en carpetas compartidas con todo el personal.
- [ ] **Texto del autor de los datos importados:** en "Actualizado por" y "Registrado por" (solo con sesión) aparece el usuario técnico `importacion`. Verificar si la ficha lo muestra como algo más claro ("Importado del Excel"); si no, es un cambio menor en `ficha.html`.

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
| `crear_usuario(conexion, usuario, nombre, hash_contrasena)`, `obtener_usuario`, `cambiar_contrasena(conexion, usuario, hash_contrasena)` | Usuarios (el hash lo hace quien llama). `cambiar_contrasena` (nueva, chat 4) lanza `ErrorDatos` si el usuario no existe o el hash está vacío |
| `registrar_intento(conexion, usuario, ip, exitoso)`, `minutos_bloqueado(conexion, usuario, ip)` | Límite de intentos: usuario con `MAX_INTENTOS` (5), IP con `MAX_INTENTOS_IP` (20) (cambiado en el chat 4) |
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

- **Pruebas:** `pruebas_app.py` (ver sección 9 para el comando completo). Correr con `python3 -m unittest pruebas_app -v` (usa una base y una clave temporales). Probado en pantalla de iPhone (393 px, WebKit) y de PC (1280 px, Chromium), sin errores en consola ni desplazamiento horizontal. **Probado con una base de prueba, no con la base real de 316 equipos.**
- **Arranque:** laptop `flask --app app run`. En PythonAnywhere (chat 6), el archivo WSGI pone `os.environ["INVENTARIO_PRODUCCION"] = "1"` **antes** de `from app import app as application`.
- **Fábrica** `crear_app(ajustes=None)` y `app = crear_app()` al final. `ajustes` permite cambiar `RUTA_DB`, `RUTA_CLAVE_SECRETA` y `ES_PRODUCCION` (lo usan las pruebas).
- **Al arrancar** (y también al hacer `import app`): crea las tablas si no existen (`db.crear_tablas`, no borra datos) y la clave secreta si no existe. Esto **no estorba** a `importar_excel.py`, que solo se niega si la base **tiene equipos**, no si el archivo existe (verificado en su código el 2026-10-30).
- **Clave secreta:** la crea `app.py` (`cargar_clave_secreta`) en `config.RUTA_CLAVE_SECRETA`: 64 caracteres hexadecimales con `secrets`, permisos 600, sin sobrescribir si otro proceso la acaba de crear. Si se borra, se genera otra y se cierran todas las sesiones (no se pierden datos). Si está vacía o tiene menos de 32 caracteres, la app no arranca y avisa. En PythonAnywhere **se genera sola**; no se sube desde la laptop.
- **Conexión por petición:** `obtener_conexion()` en `flask.g` y `cerrar_conexion` en `teardown_appcontext`.
- **Cookie de sesión:** `HttpOnly`, `SameSite=Lax`, `Secure` solo si `ES_PRODUCCION`. ⚠️ Se **asigna** directamente: `app.config.setdefault("SESSION_COOKIE_SECURE", ...)` **no funciona** porque Flask ya trae ese valor en `False`.
- **CSRF:** `CSRFProtect` ya está activo (variable `csrf`). Cada formulario POST lleva `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **`MAX_CONTENT_LENGTH` = 1 MB.**
- **Nombres para `url_for`:** `buscar` (`/`), `ficha` (`/e/<codigo>`, armada con `config.RUTA_FICHA`), `entrar`, `salir`, `cambiar_contrasena`, `nuevo_equipo`, `editar_equipo` y `registrar_mantenimiento`. Las rutas con número usan `<int:num>` (`/equipo/abc/editar` → 404).
- **Errores 400 (incluye token CSRF vencido), 404, 405, 413 y 500:** `templates/error.html`, sin detalles técnicos.
- **Búsqueda (`GET /`):** parámetros `q`, `area`, `estatus` y `baja=1` ("Incluir equipos en Baja"). `q` se corta a 100 caracteres (`LARGO_MAX_BUSQUEDA`). Sin texto ni filtros muestra todo el inventario sin las Bajas (unos 300; no hace falta paginar). El filtro de estatus ofrece `config.ESTATUS` en su orden y después cualquier otro estatus que exista en la base. Cada resultado es una tarjeta que lleva a la ficha, con estatus en color, aviso "ID temporal" y marca "Componente".
- **Enlace "← Volver a la búsqueda"** (con sesión): la ficha, el alta de equipo y las etiquetas de varios equipos regresan a la última búsqueda (texto, área, estatus e "Incluir Baja"). La búsqueda se guarda **en la sesión** (`session["ultima_busqueda"]`), no en la dirección de la ficha: así el enlace del QR no cambia, y se conserva después de editar o registrar un mantenimiento. "Limpiar" y "Salir" la borran. Sin sesión, la ficha no muestra este enlace.
- **Ficha (`GET /e/<codigo>`):** antes de consultar la base revisa que el código tenga 8 caracteres del alfabeto; si no, 404 (acepta mayúsculas). (El `app.py` del chat 3 no lo hacía; lo agregó el chat 4.)
  - **Pública:** tipo, marca y modelo; estatus con color; aviso de Baja; aviso de ID temporal; ID, serie, tipo, marca, modelo y área; ubicación y cuenta fijas; último preventivo; equipo padre o componentes (con enlace); historial (fecha, tipo, descripción); fecha de la última actualización.
  - **Solo con sesión:** **Notas**, **"Realizado por"** y "Registrado por" en el historial, y la sección "Datos internos" (num, código del QR, ID original, fila del Excel, fecha de alta, "Actualizado por").
  - Se ocultan porque las notas pueden tener información interna, los nombres de usuario facilitarían adivinar con qué usuario entrar, y el `num` no debe ser público. (Notas y "Realizado por" pasaron a solo con sesión en el chat 4.)

### `auth.py`, `crear_usuario.py` y edición ✅ (chat 4, 2026-10-31, versión combinada)

**Pruebas:** 110 en total (`pruebas_app.py`, `pruebas_sesion.py`, `pruebas_edicion.py`). Probado en pantalla de iPhone (393 px) y de PC (1280 px), modo claro y oscuro. **Probado con una base de prueba**, no con la real.

**La sesión provisional ya no existe:** se quitaron `SESION_PROVISIONAL`, el bloque provisional de `app.py`, la variable `sesion_provisional`, el aviso "Modo de desarrollo" y el candado de producción. La app ya arranca con `INVENTARIO_PRODUCCION=1`.

**Contrato de `auth.py`.** Solo tiene la lógica; las rutas las registra `app.py` (si `auth.py` usara la conexión de `flask.g`, habría un import circular).

| Función | Uso |
|---|---|
| `requiere_sesion(vista)` | Decorador. En GET manda a `/entrar?siguiente=<página>`. En POST manda a `/entrar` con el aviso "lo que estabas capturando no se guardó" |
| `hay_sesion()`, `usuario_actual()` | Si hay sesión y la fila del usuario. Las plantillas reciben `hay_sesion` y `usuario_actual` |
| `cargar_usuario(obtener_conexion)` | Lo llama `app.py` en `before_request`; deja el usuario en `g.usuario`. No abre la base si la cookie no trae usuario |
| `intentar_entrar(conexion, usuario, contrasena, ip)` | Devuelve `(fila, None)` o `(None, mensaje)`. Mientras hay bloqueo no revisa la contraseña ni registra el intento |
| `iniciar_sesion(fila)`, `cerrar_sesion()` | Abren y cierran la sesión |
| `verificar_contrasena_actual(conexion, fila, contrasena, ip)` | Para la pantalla de cambiar contraseña |
| `validar_contrasena_nueva(contrasena, confirmacion, usuario)`, `generar_hash(contrasena)` | También los usa `crear_usuario.py` |
| `ip_cliente()` | `X-Real-IP` si `ES_PRODUCCION` (verificado en la [ayuda de PythonAnywhere](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses/)); si falta, o en la laptop, `request.remote_addr` |
| `destino_seguro(destino)` | Evita que `?siguiente=` mande a otro sitio |

**Sesión y contraseñas:**
- La **sesión dura 12 horas sin usar la app** (`config.HORAS_SESION`).
- La cookie guarda una **huella de la contraseña** (HMAC del hash con la clave secreta, no el hash). Si la contraseña cambia, por la pantalla o por `crear_usuario.py --cambiar`, **se cierran solas todas las sesiones de ese usuario**. Al cambiarla desde la pantalla, la sesión actual sigue abierta y se cierran las de otros dispositivos.
- **Contraseñas:** de 12 a 128 caracteres, sin espacios al inicio ni al final, sin contener el nombre de usuario (el máximo evita que una contraseña enorme haga lento el hash).
- **Usuarios** (`crear_usuario.py`): de 3 a 30 caracteres (`a-z`, `0-9`, `.`, `_`, `-`), guardados en minúsculas. **`importacion` está reservado** (es el autor de los datos importados).
- **Usuario inexistente:** se calcula un hash de todos modos y se da el mismo mensaje que con la contraseña incorrecta, para que no se pueda averiguar qué usuarios existen.
- Un usuario de más de 30 caracteres se rechaza **sin registrar el intento**.
- **Fallar la contraseña actual en `/contrasena` cuenta como intento fallido** del usuario (así una sesión robada no sirve para adivinarla). 5 fallos ahí también bloquean `/entrar` 15 minutos.
- El token CSRF dura lo que la sesión (`WTF_CSRF_TIME_LIMIT = None`), no 1 hora: un formulario que se dejó abierto no pierde lo capturado.
- Si alguien olvida su contraseña, quien administra la app la cambia con `crear_usuario.py --cambiar` (en la consola de PythonAnywhere). La pantalla de entrada lo dice, y también que para ver una ficha no hace falta entrar.

**Edición y alta de equipos:**
- **Dos personas editando el mismo equipo:** el formulario lleva una huella del contenido. Si otra persona guardó mientras se editaba y **lo capturado es distinto de lo guardado ahora**, no se sobrescribe: responde 409 con el aviso, lo capturado y "Guardado ahora: …" junto a cada campo distinto; al volver a guardar, sí se guarda. Si lo capturado es igual a lo guardado, se trata como "No había cambios". (No se usa `actualizado_en` porque solo tiene segundos.)
- **El tipo es obligatorio** al dar de alta y al editar. Si un equipo importado no tuviera tipo, se captura al editarlo.
- **Estatus:** solo los de `config.ESTATUS`, guardados con su forma exacta. También se acepta "Sin dato" y el estatus actual del equipo aunque esté fuera del catálogo (por ejemplo "Prestado"), para no obligar a cambiarlo al editar otra cosa.
- **Largos máximos:** 200 caracteres por campo, 2000 en Notas y 1000 en la descripción del mantenimiento.
- Guardar sin cambios no toca `actualizado_en` y muestra "No había cambios".
- Las Notas guardan los saltos de línea como `\n`.
- **Lista "Componente de":** equipos que no son componentes, no están en Baja y no son el mismo equipo; siempre incluye al padre actual aunque esté en Baja. Una sola lista desplegable (unos 300). Si el equipo tiene componentes, en lugar de la lista dice "Este equipo tiene N componentes…".
- **Alta de componente** (`/equipo/nuevo?padre=N`): elige al padre y copia su área. Un `padre` no válido se ignora.
- **Alta:** estatus por defecto "Funcional"; **ID interno vacío** (sin `TMP-` automático; ver sección 3).
- El botón **"Agregar componente"** no aparece en componentes ni en equipos en Baja.
- Se pueden **registrar mantenimientos en equipos en Baja**.

**Pantallas:**
- **Cabecera con sesión:** Buscar · Nuevo equipo · Cuenta · Salir (en el iPhone dice "Nuevo" y la navegación baja a una segunda línea). "Salir" es un formulario POST con token CSRF.
- **Mensajes después de guardar** (en `base.html`): "Cambios guardados", "Equipo dado de alta", "Mantenimiento registrado", "Sesión cerrada", etc.
- **Registrar mantenimiento** no tiene pantalla propia: es un formulario **dentro de la ficha** (solo con sesión), que se despliega sin JavaScript (`<details>`). Si hay error, la ficha se vuelve a mostrar con el formulario abierto y lo capturado.


**Para el chat 6 (respaldo y publicación):**
- El enlace "Respaldo" va en el marcador de `base.html`.
- ⚠️ **El respaldo `.db` incluye los hashes de las contraseñas** y la tabla de intentos (con IPs): guardarlo con cuidado. El **Excel** del respaldo **no** debe incluir las tablas `usuarios` ni `intentos_entrada`.
- Al publicar: crear los usuarios **en una consola Bash de PythonAnywhere**, y **verificar `X-Real-IP`** (entrar una vez con contraseña equivocada y revisar que en `intentos_entrada` la IP guardada no sea la del balanceador de PythonAnywhere).
- **Importación definitiva** en PythonAnywhere (ver sección 3): las etiquetas solo se imprimen desde la base publicada.
- **Archivo WSGI:** `os.environ["INVENTARIO_PRODUCCION"] = "1"` antes de `from app import app as application`.
- **Activar "Force HTTPS"** en la pestaña Web de PythonAnywhere, para que nadie entre por `http://` (la cookie de sesión es `Secure` en producción y no funcionaría sin HTTPS).
- **Entorno virtual** en PythonAnywhere con la misma versión de Python que la laptop, e instalar `requirements.txt` (revisarlo antes: sin `zxing-cpp` ni `pypdfium2`).
- **Después de cada `git pull`**, recargar la app desde la pestaña Web. `git pull` no toca `instancia/` (está en `.gitignore`), pero conviene descargar un respaldo antes de cada actualización.
- **Revisar el vencimiento mensual** en la pestaña Web y anotar cómo funciona (sección 3).
- **Prueba final con un iPhone real:** escanear una etiqueta impresa desde la app publicada, entrar, editar y registrar un mantenimiento.

**Código muerto eliminado (regla de la sección 9):** `from functools import wraps`, `requiere_sesion`/`hay_sesion` provisionales, `SESION_PROVISIONAL` y el candado, la variable `sesion_provisional`, el aviso "Modo de desarrollo" en `base.html`, la regla `.aviso-desarrollo` en `estilos.css`, y la prueba `test_produccion_sin_auth_no_arranca` (reemplazada por `test_produccion_arranca`).

### `qr.py` y `etiquetas.py` ✅ (chat 5, 2026-11-04, 34 pruebas en `pruebas_etiquetas.py`)

**Contrato de `qr.py`:**

| Función | Uso |
|---|---|
| `enlace_equipo(codigo) -> str` | `BASE_URL + RUTA_FICHA + codigo` (valida el código; acepta mayúsculas) |
| `matriz(enlace) -> list[list[bool]]` | Módulos del QR sin zona blanca (la usa `etiquetas.py`) |
| `info_qr(enlace) -> dict` | `{"version": 4, "modulos": 33}` |
| `png(enlace, modulo_px=10, borde=4) -> bytes` | PNG en memoria, 1 bit, con 4 módulos de zona blanca (410 × 410 px) |

**Contrato de `etiquetas.py`:**

| Función | Uso |
|---|---|
| `motivo_sin_etiqueta(equipo) -> str \| None` | Por qué un equipo no lleva etiqueta (Baja, sin ID, ID muy largo, caracteres no imprimibles) |
| `separar(equipos) -> (imprimibles, excluidos)` | `excluidos` = lista de `(equipo, motivo)` |
| `ordenar_para_imprimir(equipos)` | Por área (sin área al final) y después por ID |
| `pdf_una(equipo) -> bytes` | Página de exactamente 3 × 3 cm |
| `pdf_hoja(equipos) -> bytes` | Hojas carta, 48 por hoja, líneas de corte, pie con hoja N de M y "imprimir a tamaño real" |
| `etiquetas_por_hoja()`, `calcular_medidas(modulos)` | Medidas. `calcular_medidas` se detiene con error si un cambio de `config` deja el QR sin zona blanca o con módulo < 0.5 mm |
| `ErrorEtiqueta` | Mensaje listo para mostrarse |

**Medidas de la etiqueta de 30 mm** (de arriba hacia abajo): 2.55 mm (4 módulos) · QR 21 mm · 2.55 mm · ID en Helvetica Bold 7 pt (mayúsculas de 1.8 mm) · ~2.1 mm abajo. A los lados del QR quedan 4.5 mm. "CRM GDL 06 01 10" mide 21.8 mm a 7 pt (cabe en 26 mm).

- El QR se dibuja **vectorial** (no como imagen): nítido en cualquier impresora.
- **CPU medida:** 300 etiquetas en 1.3 s; una etiqueta en 5 ms (el plan gratuito da 100 s al día).
- **Verificado:** los 300 QR y los 300 ID se leen de vuelta del PDF a 300 y a 150 ppp.
- 3 pruebas de lectura del QR solo corren con `pip install zxing-cpp pypdfium2` (la app no los necesita).
- `app.py`: nueva función `filtros_busqueda()`, que usan la búsqueda y las etiquetas.

## 5. Pantallas y rutas (Flask)

| Ruta | Quién | Qué hace |
|---|---|---|
| `GET /e/<codigo>` | **Todos (pública)** | **Ficha** (lo que abre el QR): datos, estatus con color, aviso de ID temporal, equipo padre o lista de componentes, último mantenimiento e historial. Con sesión, además muestra los botones de editar, registrar mantenimiento y QR. Código inexistente → página 404 sencilla |
| `GET/POST /entrar`, `POST /salir` | Todos | Inicio y cierre de sesión |
| `GET/POST /contrasena` | Con sesión | **"Cuenta"**: datos de la cuenta y cambio de contraseña (agregada en el chat 4) |
| `GET /` | Con sesión | Búsqueda: un cuadro de texto (serie, ID, tipo, marca, modelo) + filtros de área y estatus. Oculta Baja salvo que se pida. Sin sesión, redirige a `/entrar` |
| `GET/POST /equipo/<num>/editar` | Con sesión | Editar los datos del equipo (incluye ligarlo a un padre) |
| `GET/POST /equipo/nuevo` | Con sesión | Alta de equipo o componente (opcional: `?padre=<num>`); genera su `codigo` |
| `POST /equipo/<num>/mantenimiento` | Con sesión | Registrar un mantenimiento (el formulario está dentro de la ficha, sin pantalla propia) |
| `GET /equipo/<num>/etiqueta` (`etiqueta`) | Con sesión | **Vista previa** del QR, enlace, botones de PDF e instrucciones; si el equipo no lleva etiqueta, el motivo (agregada en el chat 5) |
| `GET /equipo/<num>/qr.png` (`qr_png`) | Con sesión | PNG del QR |
| `GET /equipo/<num>/etiqueta.pdf` (`etiqueta_pdf`) | Con sesión | PDF de **una** etiqueta en página de 3×3 cm; con `?hoja=carta`, en hoja carta |
| `GET /etiquetas` (`etiquetas`) | Con sesión | **Resumen antes de imprimir:** cuántas etiquetas, cuántas hojas y qué equipos quedan fuera y por qué (agregada en el chat 5) |
| `GET /etiquetas.pdf` (`etiquetas_pdf`) | Con sesión | PDF en hoja carta con los filtros `q`, `area`, `estatus` de la búsqueda |
| | | Todas las rutas de etiquetas abren el archivo en el navegador (`inline`) con `Cache-Control: private, no-store`. Equipo en Baja o sin ID → página de aviso con código 409. Botón "QR / etiqueta" en la ficha (no en Baja) y botón "Imprimir etiquetas" junto al conteo de la búsqueda |
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
- **Logo y nombre de la cabecera** llevan a la búsqueda, **solo con sesión** (`hay_sesion`); sin sesión quedan como texto. Con `aria-label="Ir a la búsqueda"`, sin subrayado, mismo color y estilo en `estilos.css` (✅ chat 4).
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
├── qr.py                ← enlace, matriz y PNG del QR de un equipo
├── etiquetas.py         ← PDF de una etiqueta (3×3 cm) o de varias (hoja carta, 48 por hoja)
├── respaldo.py          ← exporta Excel y copia de la base de datos
├── importar_excel.py    ← script de una sola vez: carga el Excel a la base de datos
├── crear_usuario.py     ← alta de usuarios y `--cambiar` contraseña (en la laptop y en la consola de PythonAnywhere)
├── pruebas_app.py       ← pruebas de app.py (búsqueda, ficha)
├── pruebas_sesion.py    ← pruebas de auth.py (entrar, bloqueo, contraseña)
├── pruebas_edicion.py   ← pruebas de edición, alta y mantenimientos
├── pruebas_etiquetas.py ← pruebas de qr.py, etiquetas.py y sus rutas
├── modulos/             ← reutilizados de la versión 1 (solo los usa importar_excel.py)
│   ├── lector_excel.py
│   ├── limpieza.py
│   └── ids.py
├── templates/           ← base.html, macros.html, buscar.html, ficha.html, error.html,
│                           entrar.html, editar.html, contrasena.html
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
| `generador_qr.py` | Reemplazado por `qr.py` (chat 5). Ya no se usa; está en la etiqueta `v1` de git |
| `pdf_etiquetas.py` | Reemplazado por `etiquetas.py` (chat 5), que dibuja el QR vectorial. Ya no se usa; está en la etiqueta `v1` de git |
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

## 8. `config.py` (versión 2, generado el 2026-10-28, actualizado el 2026-11-04)

El archivo completo lo tiene el usuario. Resumen:

| Grupo | Constantes |
|---|---|
| Rutas | `CARPETA_BASE` (carpeta de `config.py`), `CARPETA_INSTANCIA`, `RUTA_DB`, `RUTA_CLAVE_SECRETA`. Son objetos `Path` calculados desde `CARPETA_BASE`, para que funcionen igual en la laptop y en PythonAnywhere |
| Zona horaria | `ZONA_HORARIA = ZoneInfo("America/Mexico_City")` (agregada 2026-10-29) |
| Servidor | `BASE_URL = "https://bi0medic4crm.pythonanywhere.com"`, `RUTA_FICHA = "/e/"`, `ES_PRODUCCION` (variable de entorno `INVENTARIO_PRODUCCION=1`, solo en PythonAnywhere) |
| Código del QR | `LARGO_CODIGO = 8`, `ALFABETO_CODIGO = "23456789abcdefghjkmnpqrstuvwxyz"` (31 caracteres, ~8.5 × 10¹¹ combinaciones) |
| Inicio de sesión | `MAX_INTENTOS = 5` (por usuario), `MAX_INTENTOS_IP = 20` (por IP, agregada 2026-10-30), `MINUTOS_BLOQUEO = 15`, `HORAS_SESION = 12` (agregada 2026-11-04) |
| Catálogos | `ESTATUS` (6 valores), `ESTATUS_EXCLUIDOS = ["baja"]` (sin TMP, sin QR, ocultos en búsqueda), `TIPOS_MANTENIMIENTO` |
| Texto fijo | `CUENTA_FIJA = "Cruz Roja Mexicana"`, `UBICACION_FIJA = "Delegación Guadalajara"` |
| Etiquetas | `TAM_ETIQUETA_CM = 3`, `TAM_QR_CM = 2.1` (fijo desde el chat 5), `CORRECCION_QR = "M"` |
| Importación (v1) | `RUTA_EXCEL`, `HOJA`, `PRIMERA_FILA`, `COL_INI`, `COL_FIN`, `COLUMNAS`, `SIN_ID`, `FORMATO_ID`, `PREFIJO_TMP`, `DESCRIPCION_MPREV_IMPORTADO` |
| Normalización | `NORMALIZAR_MARCAS`, `NORMALIZAR_TIPOS` (sin cambios) |

**Se quitaron** (solo los usaba la versión 1): `CAMPOS_QR`, `CARPETA_SALIDA`, `CARPETA_QR`, `CSV_REVISION`, `CSV_EXCLUIDOS`, `PDF_ETIQUETAS` y la `BASE_URL` de GitHub Pages.

## 9. Reglas para todos los chats

- Python 3.10+. Dependencias: `flask`, `flask-wtf` (protección CSRF en formularios), `openpyxl`, `qrcode[pil]`, `reportlab`.
  Opcionales, **solo para pruebas** (no van en `requirements.txt` de PythonAnywhere): `zxing-cpp` y `pypdfium2`, para leer de vuelta los QR de los PDF.
  Si alguien desarrolla en **Windows**, agregar `tzdata` (lo necesita `zoneinfo`); en macOS y PythonAnywhere no hace falta.
- Nombres de funciones, variables, rutas y tablas en español, sin acentos.
- **Seguridad:**
  - Contraseñas solo como hash.
  - Toda ruta que modifica datos o genera QR/PDF exige sesión.
  - Formularios con token CSRF. El token dura lo que la sesión (`WTF_CSRF_TIME_LIMIT = None`), ligado a la cookie de sesión (12 horas sin usar la app).
  - Plantillas con autoescape (nunca `|safe` con datos del usuario).
  - Consultas SQL siempre con parámetros (`?`), nunca armando el texto con datos.
  - Cookie de sesión con `HttpOnly` y `SameSite=Lax` siempre, y `Secure` **solo si `ES_PRODUCCION`** (en la laptop no hay HTTPS y con `Secure` el inicio de sesión no funcionaría).
  - Límite de intentos de inicio de sesión guardado en SQLite (tabla `intentos_entrada`).
  - Respaldo de la base de datos con `sqlite3.Connection.backup()`, no copiando el archivo.
  - `.gitignore` con `instancia/`, el Excel y los `.db` **antes del primer commit** (el repositorio de GitHub puede ser público).
- **Nunca** compartir ni subir `instancia/` (base de datos y clave secreta) ni el Excel.
- Todo debe poder probarse primero en la laptop del usuario (`flask --app app run`) antes de subirlo a PythonAnywhere.
- **Pruebas:** antes de subir cambios a PythonAnywhere, correr en la laptop `python3 -m unittest pruebas_app pruebas_sesion pruebas_edicion pruebas_etiquetas` y también el archivo de pruebas de `db.py`. Cada chat que agregue rutas agrega sus pruebas a uno de esos archivos o a uno nuevo `pruebas_<parte>.py` (y lo suma a este comando).
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
4. ✅ `auth.py` + `crear_usuario.py` + edición + registro de mantenimientos + alta de equipos y componentes + cambio de contraseña (versión combinada, 110 pruebas: `pruebas_app` + `pruebas_sesion` + `pruebas_edicion`; probada en WebKit/iPhone y Chromium, claro y oscuro). Incluye las 5 tareas que le dejaron los chats anteriores
5. ✅ `qr.py` + `etiquetas.py` + rutas de QR y etiquetas + `pruebas_etiquetas.py` (34 pruebas; 2026-11-04). También movió `HORAS_SESION` a `config.py`
6. ⏳ `respaldo.py` + publicación en PythonAnywhere + prueba con el iPhone (ver "Para el chat 6" en la sección 4)
7. ⏳ Cierre: avisos para no dejar vencer la app (cuando se sepa cómo funciona el vencimiento), detalles menores pendientes de la sección 3 y **guía breve para el personal**