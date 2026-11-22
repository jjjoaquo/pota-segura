const buscador = document.querySelector("[data-busqueda]");
if (buscador) {
  const cerca = buscador.querySelector("[data-cerca]");
  const orden = buscador.elements.orden;
  const estado = buscador.querySelector("[data-estado]");
  const buscar = buscador.querySelector('button:not([type])');

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
    if (orden.value === "cerca" && !buscador.elements.lat) {
      evento.preventDefault();
      if (!cerca.disabled) localizar();
      return;
    }
    if (orden.value !== "cerca") limpiarUbicacion();
    buscar.disabled = true;
    estado.textContent = "Buscando puestos…";
  });
  window.addEventListener("pageshow", (evento) => {
    if (evento.persisted) {
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
