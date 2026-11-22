const buscador = document.querySelector("[data-busqueda]");
if (buscador) {
  const cerca = buscador.querySelector("[data-cerca]");
  const orden = buscador.elements.orden;
  const estado = buscador.querySelector("[data-estado]");
  const buscar = buscador.querySelector('button:not([type])');
  const error = buscador.querySelector("[data-error]");
  const resultados = document.querySelector("#lista-resultados");
  const titulo = document.querySelector("#titulo-resultados");
  let activa;

  const mostrarError = (mensaje) => {
    error.textContent = mensaje;
    error.hidden = !mensaje;
  };

  const consultar = async (url, guardar = true) => {
    activa?.abort();
    const solicitud = new AbortController();
    activa = solicitud;
    const limite = setTimeout(() => solicitud.abort(), 12000);
    const endpoint = new URL(buscador.dataset.endpoint, location.origin);
    endpoint.search = url.search;
    buscar.disabled = true;
    cerca.disabled = true;
    resultados.setAttribute("aria-busy", "true");
    estado.textContent = "Buscando puestos…";
    mostrarError("");
    try {
      const respuesta = await fetch(endpoint, {
        headers: { Accept: "application/json" }, signal: solicitud.signal,
      });
      if (!respuesta.headers.get("Content-Type")?.includes("application/json")) {
        throw new Error("El servicio de búsqueda no está disponible. Inténtalo de nuevo.");
      }
      const datos = await respuesta.json();
      if (activa !== solicitud) return;
      if (!respuesta.ok) {
        throw new Error(Object.values(datos.errores ?? {}).join(" ") || "No pudimos hacer la búsqueda.");
      }
      const fragmento = document.createElement("template");
      fragmento.innerHTML = datos.html;
      resultados.replaceChildren(fragmento.content);
      const filtros = url.searchParams;
      titulo.textContent = ["q", "ingrediente", "producto", "distrito", "estado", "pagina"].some(
        (campo) => filtros.get(campo)?.trim(),
      ) || filtros.get("orden") === "cerca" ? "Resultados de búsqueda" : "Puestos recientes";
      if (guardar && url.href !== location.href) history.pushState(null, "", url);
    } catch (fallo) {
      if (activa !== solicitud) return;
      mostrarError(fallo.name === "AbortError" ? "La búsqueda tardó demasiado. Inténtalo de nuevo." :
        fallo instanceof TypeError ? "No pudimos conectar con el buscador. Revisa tu conexión e inténtalo de nuevo." :
        fallo.message);
    } finally {
      clearTimeout(limite);
      if (activa === solicitud) {
        activa = null;
        buscar.disabled = false;
        cerca.disabled = false;
        resultados.setAttribute("aria-busy", "false");
        estado.textContent = "";
      }
    }
  };

  const limpiarUbicacion = () => {
    buscador.querySelectorAll('[name="lat"], [name="lon"]').forEach((campo) => campo.remove());
  };

  const localizar = () => {
    if (!navigator.geolocation) {
      estado.textContent = "Tu navegador no permite usar la ubicación.";
      orden.value = "reciente";
      return;
    }
    estado.textContent = "Permite el acceso a tu ubicación para ordenar los puestos por distancia.";
    cerca.disabled = true;
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      limpiarUbicacion();
      for (const [nombre, valor] of [["lat", coords.latitude], ["lon", coords.longitude]]) {
        const campo = document.createElement("input");
        campo.type = "hidden";
        campo.name = nombre;
        campo.value = valor.toFixed(3);
        buscador.append(campo);
      }
      orden.value = "cerca";
      buscador.requestSubmit();
    }, () => {
      cerca.disabled = false;
      orden.value = "reciente";
      limpiarUbicacion();
      estado.textContent = "No pudimos obtener tu ubicación. Puedes buscar por nombre o distrito.";
    }, { timeout: 10000, maximumAge: 60000 });
  };

  cerca.hidden = false;
  cerca.addEventListener("click", localizar);
  buscador.addEventListener("submit", (evento) => {
    evento.preventDefault();
    if (orden.value === "cerca" && !buscador.elements.lat) {
      if (!cerca.disabled) localizar();
      return;
    }
    if (orden.value !== "cerca") limpiarUbicacion();
    const url = new URL(location.pathname, location.origin);
    for (const [campo, valor] of new FormData(buscador)) {
      const limpio = valor.trim();
      if (limpio && !(campo === "orden" && limpio === "reciente")) url.searchParams.set(campo, limpio);
    }
    consultar(url);
  });
  resultados.addEventListener("click", (evento) => {
    const enlace = evento.target.closest(".paginacion a");
    if (!enlace || evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.altKey) return;
    evento.preventDefault();
    consultar(new URL(enlace.href));
  });
  window.addEventListener("popstate", () => location.reload());
  window.addEventListener("pageshow", (evento) => {
    if (evento.persisted && !activa) {
      buscar.disabled = false;
      cerca.disabled = false;
      estado.textContent = "";
    }
  });
}

const acceso = document.querySelector("[data-acceso]");
if (acceso) {
  const contrasena = acceso.elements.password;
  const mostrar = acceso.querySelector("[data-mostrar]");
  const ingresar = acceso.querySelector("[type=submit]");
  const aviso = acceso.querySelector('[role="status"]');
  mostrar.hidden = false;
  mostrar.addEventListener("click", () => {
    const visible = contrasena.type === "text";
    contrasena.type = visible ? "password" : "text";
    mostrar.textContent = visible ? "Mostrar" : "Ocultar";
    mostrar.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
  });
  acceso.addEventListener("submit", () => {
    ingresar.disabled = true;
    ingresar.textContent = "Ingresando…";
    aviso.textContent = "Verificando tus datos.";
  });
  window.addEventListener("pageshow", (evento) => {
    if (evento.persisted) {
      ingresar.disabled = false;
      ingresar.textContent = "Ingresar";
      aviso.textContent = "";
    }
  });
}
