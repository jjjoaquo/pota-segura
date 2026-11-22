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
- Desactiva el despliegue automático si GitHub Actions controlará el despliegue. Guarda la URL del hook como secreto `RENDER_DEPLOY_HOOK`. Comprueba en Render que el despliegue termina y verifica la URL HTTPS.

Trabaja en `test` y abre pull requests hacia `main`. En el informe incluye el PR, los resultados de validación y el estado final en Render.

## Consulta pública y acceso

Registra dirección y coordenadas del puesto si están disponibles. Los puestos previos conservan sus datos y aparecen como «Dirección sin registrar» hasta que se complete el campo. La búsqueda por cercanía ordena primero los puestos con coordenadas y muestra distancias en línea recta.

La vigencia deriva de la fecha de vencimiento consignada por el inspector. El aviso de próximo vencimiento usa siete días. El inspector marca explícitamente las observaciones pendientes. Los registros anteriores sin vencimiento muestran «Vigencia sin registrar».

Configura `POTA_FUENTE_DATOS` cuando se confirme la entidad de origen y `POTA_CONTACTO_EMAIL` para habilitar contacto, reportes por correo y ayuda para el acceso. El enlace de recuperación remite al administrador hasta que se configure un flujo de correo. Los mapas pueden añadirse con Leaflet cuando se disponga de coordenadas verificadas y un proveedor de teselas.

La pantalla pública de acceso admite ocho intentos por usuario y origen en cada ventana de quince minutos. El despliegue de producción usa HTTPS. La verificación en dos pasos queda para una futura integración con un proveedor de identidad.
