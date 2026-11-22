#!/usr/bin/env bash
set -euo pipefail

origen="${1%/}"
opciones=(--fail --silent --show-error --max-time 20)
if [[ "${2:-}" == "proxy-local" ]]; then
  opciones+=(-H 'X-Forwarded-Proto: https')
  respuesta=$(curl --silent --show-error --max-time 10 --output /dev/null --write-out '%{http_code}' "$origen/health/")
  test "$respuesta" = 301
  echo "La aplicación redirige HTTP a HTTPS."
fi

curl "${opciones[@]}" "$origen/health/" | jq -e '.estado == "ok"' >/dev/null
curl "${opciones[@]}" "$origen/" | grep -F 'Consulta de puestos de ceviche' >/dev/null
curl "${opciones[@]}" "$origen/api/puestos/?q=JESUS%20MARIA" |
  jq -e '(.errores == {}) and (.resultados | type == "array") and (.paginacion.pagina == 1)' >/dev/null
curl "${opciones[@]}" "$origen/static/puestos/estilos.css" | grep -F '.login-panel' >/dev/null
curl "${opciones[@]}" "$origen/static/puestos/interaccion.js" | grep -F '[data-busqueda]' >/dev/null
curl "${opciones[@]}" --dump-header - --output /dev/null "$origen/login/" |
  grep -Ei '^set-cookie: csrftoken=.*; Secure' >/dev/null

echo "Portada, API, archivos estáticos y cookie CSRF verificados."
