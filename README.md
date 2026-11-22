# Pota Segura

Aplicación Django para declarar productos, registrar inspecciones y consultar puestos de ceviche.

## Puesta en marcha local

Usa Python 3.12. Desde el directorio del proyecto, ejecuta:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py crear_roles
python manage.py createsuperuser
python manage.py runserver
```

Abre http://127.0.0.1:8000/admin/, crea un usuario vendedor y otro inspector, y asígnales respectivamente los grupos Vendedor e Inspector. En la portada, inicia sesión como vendedor, registra un puesto y declara su producto. Cierra sesión, vuelve a entrar como inspector y registra una visita. Como visitante, abre la ficha pública y verifica la declaración y la última visita.

Ejecuta `python manage.py test --verbosity 2` para verificar los flujos principales.

## Render

Crea una base PostgreSQL y un servicio web Python vinculado a `main`. Configura `DATABASE_URL`, `DJANGO_SECRET_KEY` y `POTA_DEBUG=0`. Usa Python 3.12.

- Comando de compilación: `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
- Comando de inicio: `python manage.py migrate --noinput && python manage.py crear_roles && gunicorn pota.wsgi:application --bind 0.0.0.0:$PORT`.
- Ruta de salud: `/health/`.
- Crea las cuentas de demostración en el entorno de producción con el administrador.
- Configura el servicio para usar `main` y desactiva **Auto-Deploy** si GitHub Actions controla el despliegue.
- En **GitHub → Settings → Secrets and variables → Actions**, guarda el hook como secreto `RENDER_DEPLOY_HOOK` y la URL pública HTTPS como variable `RENDER_PUBLIC_URL`. También puedes definirlos dentro del entorno `production`.
- GitHub Actions ejecuta construcción y pruebas en SQLite y PostgreSQL, además de Bandit, pip-audit y Gitleaks. En `main`, solicita el despliegue tras pasar todas las comprobaciones. Consulta `/health/` hasta que la base de datos responda y `revision` coincida con el commit esperado. Puedes reintentar desde **Actions → Validación y despliegue → Run workflow**, seleccionando `main`.

Trabaja en `test` y abre pull requests hacia `main`. En el informe incluye el PR, los resultados de validación y el estado final en Render.

## Consulta pública y acceso

Registra dirección y coordenadas del puesto si están disponibles. Los puestos previos conservan sus datos y aparecen como «Dirección sin registrar» hasta que se complete el campo. La búsqueda por cercanía ordena primero los puestos con coordenadas y muestra distancias en línea recta.

La vigencia deriva de la fecha de vencimiento consignada por el inspector. El aviso de próximo vencimiento usa siete días. El inspector marca explícitamente las observaciones pendientes. Los registros anteriores sin vencimiento muestran «Vigencia sin registrar».

Configura `POTA_FUENTE_DATOS` cuando se confirme la entidad de origen y `POTA_CONTACTO_EMAIL` para habilitar contacto, reportes por correo y ayuda para el acceso. El enlace de recuperación remite al administrador hasta que se configure un flujo de correo. Los mapas pueden añadirse con Leaflet cuando se disponga de coordenadas verificadas y un proveedor de teselas.

La pantalla pública de acceso admite ocho intentos por usuario y origen en cada ventana de quince minutos. El despliegue de producción usa HTTPS. La verificación en dos pasos queda para una futura integración con un proveedor de identidad.

## API de búsqueda y datos de demostración

`GET /api/puestos/` recibe `q` (nombre o distrito), `ingrediente`, `estado`, `orden` y `pagina`. La búsqueda ignora mayúsculas y las tildes habituales del español. El orden predeterminado es `reciente`. Para `orden=cerca`, envía `lat` y `lon`. La respuesta contiene `resultados`, `paginacion`, `total_publicados`, `html` y `errores`. La página y la API comparten el fragmento HTML de las tarjetas. La API usa 400 para parámetros inválidos, 404 para páginas inexistentes y 405 para métodos distintos de GET.

Para probar con diez puestos e inspecciones ficticios en una base de demostración:

```sh
python manage.py migrate
python manage.py seed_puestos
python manage.py test
```

Puedes volver a ejecutar el seed. Los puestos se identifican con el prefijo «Demo ·». El comando escribe en la base configurada en `DATABASE_URL` o en SQLite si la variable no está definida.

En **Iniciar sesión → Regístrate como vendedor**, se crean cuentas con el grupo Vendedor. El administrador asigna el grupo Inspector a cuentas autorizadas.

Para cargar los puestos ficticios en el servicio de demostración de Render, ejecuta `python manage.py seed_puestos` desde el Shell del servicio, con `DATABASE_URL` configurada. Si tu plan no ofrece Shell, añade temporalmente `python manage.py seed_puestos &&` entre `python manage.py crear_roles &&` y `gunicorn` en **Start Command**. Tras el primer despliegue exitoso, restaura el comando original para que el arranque habitual no recalcule las fechas de las inspecciones ficticias. El selector de distrito de la portada se llena con los puestos publicados.

Los usuarios con sesión pueden reportar un puesto desde su ficha. El equipo revisa los reportes en el administrador de Django.

El pipeline valida los workflows con actionlint y exige un mínimo de 82 % de cobertura de líneas y ramas en ambas bases. Una prueba de arranque levanta Gunicorn con `POTA_DEBUG=0`, simula el proxy HTTPS y comprueba la portada, la API, los archivos estáticos y la cookie CSRF. Después del despliegue se repiten las comprobaciones HTTP contra Render, una vez confirmada la revisión.
