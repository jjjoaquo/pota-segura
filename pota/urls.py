from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path

from puestos import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("", views.lista, name="lista"),
    path("puestos/nuevo/", views.registrar, name="registrar"),
    path("puestos/<int:pk>/", views.ficha, name="ficha"),
    path("puestos/<int:pk>/declaracion/", views.declarar, name="declarar"),
    path("puestos/<int:pk>/inspeccion/", views.inspeccionar, name="inspeccionar"),
    path("puestos/<int:pk>/historial/", views.historial, name="historial"),
    path("health/", views.salud, name="salud"),
]
