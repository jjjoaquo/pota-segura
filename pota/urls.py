from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path

from puestos import views
from puestos.acceso import Acceso, crear_cuenta

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", Acceso.as_view(), name="login"),
    path("registro/", crear_cuenta, name="crear_cuenta"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("", views.lista, name="lista"),
    path("api/puestos/", views.buscar_api, name="buscar_api"),
    path("puestos/nuevo/", views.registrar, name="registrar"),
    path("puestos/<int:pk>/", views.ficha, name="ficha"),
    path("puestos/<int:pk>/declaracion/", views.declarar, name="declarar"),
    path("puestos/<int:pk>/inspeccion/", views.inspeccionar, name="inspeccionar"),
    path("puestos/<int:pk>/historial/", views.historial, name="historial"),
    path("informacion/<slug:tema>/", views.informacion, name="informacion"),
    path("puestos/<int:pk>/reportar/", views.reportar_puesto, name="reportar_puesto"),
    path("health/", views.salud, name="salud"),
]
