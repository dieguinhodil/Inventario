/*
 * visor.js — Ficha de equipo a partir del enlace del QR.
 *
 * Contrato (arquitectura.md, sección 7, "docs/ (visor)"):
 *   - Lee location.hash:  #id=...&tipo=...&marca=...&modelo=...&serie=...&area=...&estatus=...&ultimo_mprev=AAAA-MM-DD
 *   - Las claves y su orden coinciden con config.CAMPOS_QR y con modulos/enlaces.py.
 *   - Los valores vienen codificados con urllib.parse.quote(valor, safe="") y se
 *     decodifican con decodeURIComponent.
 *   - Cuenta y Ubicación son texto fijo (iguales en las 316 filas).
 *   - Si falta ultimo_mprev se muestra "Sin registro".
 *   - Sin librerías y sin ninguna petición a servidores: todo ocurre en el navegador.
 *
 * Seguridad: cualquiera puede escribir un enlace con datos inventados, así que
 * los valores se insertan SIEMPRE con textContent (nunca innerHTML).
 */
(function () {
  "use strict";

  // --- Debe coincidir con config.CAMPOS_QR -----------------------------------
  var CAMPOS_QR = ["id", "tipo", "marca", "modelo", "serie", "area", "estatus", "ultimo_mprev"];

  // Texto fijo (no viaja en el QR)
  var CUENTA = "Cruz Roja Mexicana";
  var UBICACION = "Cruz Roja Guadalajara";

  var PREFIJO_TMP = "TMP-";          // config.PREFIJO_TMP
  var SIN_REGISTRO = "Sin registro"; // para ultimo_mprev vacío
  var SIN_DATO = "Sin dato";         // para cualquier otro campo vacío

  // Valores que en el Excel significan "no hay dato" (ej. 133 series dicen "S/D")
  var VALORES_VACIOS = ["s/d", "n/a", "na", "-", "--", "sin dato"];

  // Etiquetas visibles, en el orden en que se muestran en la ficha
  var FILAS = [
    { clave: "tipo",      etiqueta: "Tipo de equipo" },
    { clave: "marca",     etiqueta: "Marca" },
    { clave: "modelo",    etiqueta: "Modelo" },
    { clave: "serie",     etiqueta: "No. de serie", mono: true },
    { clave: "area",      etiqueta: "Área" },
    { fijo: UBICACION,    etiqueta: "Ubicación" },
    { fijo: CUENTA,       etiqueta: "Cuenta" }
  ];

  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

  // --- Lectura del hash ------------------------------------------------------

  function decodificar(texto) {
    try {
      return decodeURIComponent(texto);
    } catch (e) {
      return texto; // secuencia % mal formada: se muestra tal cual
    }
  }

  /** Convierte "#id=A&tipo=B" en { id: "A", tipo: "B" }. Ignora claves desconocidas. */
  function leerHash(hash) {
    var datos = {};
    var texto = (hash || "").replace(/^#/, "");
    if (!texto) return datos;

    texto.split("&").forEach(function (par) {
      if (!par) return;
      var pos = par.indexOf("=");
      var clave = decodificar(pos === -1 ? par : par.slice(0, pos)).trim();
      var valor = pos === -1 ? "" : decodificar(par.slice(pos + 1)).trim();
      if (CAMPOS_QR.indexOf(clave) === -1) return;   // clave que no está en el contrato
      if (clave in datos) return;                      // si se repite, gana la primera
      if (valor !== "" && VALORES_VACIOS.indexOf(normalizar(valor)) === -1) datos[clave] = valor;
    });
    return datos;
  }

  // --- Formatos --------------------------------------------------------------

  /** "2025-01-15" -> "15 de enero de 2025". Si no tiene ese formato, se devuelve igual. */
  function formatearFecha(valor) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor || "");
    if (!m) return valor;
    var anio = parseInt(m[1], 10);
    var mes = parseInt(m[2], 10);
    var dia = parseInt(m[3], 10);
    // Comprueba contra el calendario real (rechaza 2025-02-31, 2025-13-01...)
    var fecha = new Date(Date.UTC(anio, mes - 1, dia));
    if (fecha.getUTCMonth() !== mes - 1 || fecha.getUTCDate() !== dia) return valor;
    return dia + " de " + MESES[mes - 1] + " de " + anio;
  }

  /** Para comparar: sin acentos, minúsculas y espacios simples (como limpieza.clave). */
  function normalizar(texto) {
    return (texto || "")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/\s+/g, " ").trim();
  }

  /** Clase de color para el estatus (los 6 valores que hay en la hoja GUADALAJARA). */
  function claseEstatus(estatus) {
    switch (normalizar(estatus)) {
      case "funcional":         return "estatus--ok";
      case "en revision":
      case "en mantenimiento":  return "estatus--aviso";
      case "fuera de servicio":
      case "no funcional":
      case "baja":              return "estatus--alerta";
      default:                  return "estatus--neutro";
    }
  }

  // --- Construcción del DOM --------------------------------------------------

  function el(etiqueta, clase, texto) {
    var nodo = document.createElement(etiqueta);
    if (clase) nodo.className = clase;
    if (texto !== undefined) nodo.textContent = texto;
    return nodo;
  }

  function contenedor() {
    var nodo = document.getElementById("visor");
    if (!nodo) {
      nodo = el("main");
      nodo.id = "visor";
      document.body.appendChild(nodo);
    }
    return nodo;
  }

  function encabezado() {
    var cab = el("header", "cabecera");
    var cruz = el("span", "cabecera__cruz");
    cruz.setAttribute("aria-hidden", "true");
    var textos = el("div", "cabecera__textos");
    textos.appendChild(el("p", "cabecera__titulo", UBICACION));
    textos.appendChild(el("p", "cabecera__subtitulo", "Inventario de equipo biomédico"));
    cab.appendChild(cruz);
    cab.appendChild(textos);
    return cab;
  }

  function fila(etiqueta, valor, opciones) {
    opciones = opciones || {};
    var dt = el("dt", "dato__etiqueta", etiqueta);
    var dd = el("dd", "dato__valor", valor || opciones.vacio || SIN_DATO);
    if (!valor) dd.classList.add("dato__valor--vacio");
    if (valor && opciones.mono) dd.classList.add("dato__valor--mono");
    var envoltura = el("div", "dato");
    envoltura.appendChild(dt);
    envoltura.appendChild(dd);
    return envoltura;
  }

  function fichaEquipo(datos) {
    var ficha = el("article", "ficha");

    // ID + estatus
    var cabeza = el("div", "ficha__cabeza");
    cabeza.appendChild(el("p", "ficha__rotulo", "ID interno"));
    cabeza.appendChild(el("h1", "ficha__id", datos.id || SIN_DATO));

    var estatus = el("p", "estatus " + claseEstatus(datos.estatus), datos.estatus || "Estatus sin dato");
    cabeza.appendChild(estatus);
    ficha.appendChild(cabeza);

    if (datos.id && datos.id.toUpperCase().indexOf(PREFIJO_TMP) === 0) {
      ficha.appendChild(el("p", "aviso",
        "ID temporal: este equipo no tenía un ID interno válido o estaba repetido en el inventario."));
    }

    // Datos generales
    var lista = el("dl", "datos");
    FILAS.forEach(function (f) {
      if (f.fijo) {
        lista.appendChild(fila(f.etiqueta, f.fijo));
      } else {
        lista.appendChild(fila(f.etiqueta, datos[f.clave], { mono: f.mono }));
      }
    });
    ficha.appendChild(lista);

    // Mantenimiento
    var mant = el("section", "mantenimiento");
    mant.appendChild(el("h2", "mantenimiento__titulo", "Último mantenimiento preventivo"));
    var fecha = datos.ultimo_mprev ? formatearFecha(datos.ultimo_mprev) : SIN_REGISTRO;
    var valor = el("p", "mantenimiento__fecha", fecha);
    if (!datos.ultimo_mprev) valor.classList.add("mantenimiento__fecha--vacio");
    mant.appendChild(valor);
    ficha.appendChild(mant);

    return ficha;
  }

  function fichaVacia() {
    var ficha = el("article", "ficha ficha--vacia");
    ficha.appendChild(el("h1", "ficha__vacia-titulo", "Escanea el QR de un equipo"));
    ficha.appendChild(el("p", "ficha__vacia-texto",
      "Esta página muestra la ficha de un equipo biomédico. Apunta la cámara del teléfono a la etiqueta QR pegada en el equipo."));
    return ficha;
  }

  function pie() {
    return el("footer", "pie",
      "Datos al momento de imprimir la etiqueta. Esta página no envía información a ningún servidor.");
  }

  // --- Render ----------------------------------------------------------------

  function mostrar() {
    var datos = leerHash(window.location.hash);
    var raiz = contenedor();
    raiz.textContent = "";            // limpia cualquier contenido previo

    raiz.appendChild(encabezado());
    var hayDatos = Object.keys(datos).length > 0;
    raiz.appendChild(hayDatos ? fichaEquipo(datos) : fichaVacia());
    raiz.appendChild(pie());

    document.title = hayDatos && datos.id ? datos.id + " · Inventario" : "Inventario · " + UBICACION;
  }

  window.addEventListener("hashchange", mostrar);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mostrar);
  } else {
    mostrar();
  }
})();