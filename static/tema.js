/*
 * tema.js — Interruptor de modo claro / oscuro.
 *
 * - Se carga en <head> SIN defer: pone el tema antes de que se dibuje la página (sin parpadeo).
 * - Mientras no se toque el interruptor, sigue el modo del teléfono o la PC.
 * - Al tocarlo, la elección se guarda en este navegador (localStorage).
 * - Va en un archivo aparte porque la política de seguridad de la app no permite <script> dentro del HTML.
 */
(function () {
  "use strict";

  var CLAVE = "tema";
  var raiz = document.documentElement;
  var sistema = window.matchMedia("(prefers-color-scheme: dark)");

  function guardado() {
    try {
      var valor = localStorage.getItem(CLAVE);
      return valor === "claro" || valor === "oscuro" ? valor : null;
    } catch (e) {
      return null;   // navegación privada o almacenamiento bloqueado: se sigue el sistema
    }
  }

  function actual() {
    return guardado() || (sistema.matches ? "oscuro" : "claro");
  }

  function aplicar(tema) {
    raiz.setAttribute("data-tema", tema);
    var boton = document.getElementById("interruptor-tema");
    if (boton) boton.setAttribute("aria-checked", tema === "oscuro" ? "true" : "false");
  }

  aplicar(actual());
  sistema.addEventListener("change", function () {
    if (!guardado()) aplicar(actual());
  });

  document.addEventListener("DOMContentLoaded", function () {
    var boton = document.getElementById("interruptor-tema");
    if (!boton) return;
    boton.hidden = false;          // sin JavaScript el interruptor no serviría, así que empieza oculto
    aplicar(actual());
    boton.addEventListener("click", function () {
      var nuevo = raiz.getAttribute("data-tema") === "oscuro" ? "claro" : "oscuro";
      try {
        localStorage.setItem(CLAVE, nuevo);
      } catch (e) { /* no se puede guardar: el cambio dura solo esta página */ }
      aplicar(nuevo);
    });
  });
})();
