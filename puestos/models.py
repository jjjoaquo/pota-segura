from django.conf import settings
from django.db import models


class Puesto(models.Model):
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=100)
    distrito = models.CharField(max_length=80)


class Declaracion(models.Model):
    puesto = models.OneToOneField(Puesto, on_delete=models.CASCADE)
    producto = models.CharField(max_length=100)
    ingrediente_principal = models.CharField(max_length=100)
    otros_ingredientes = models.TextField(blank=True, max_length=500)


class Inspeccion(models.Model):
    class Licencia(models.TextChoices):
        PRESENTADA = "presentada", "Presentada"
        NO_PRESENTADA = "no_presentada", "No presentada"

    puesto = models.ForeignKey(Puesto, related_name="inspecciones", on_delete=models.CASCADE)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    licencia = models.CharField(max_length=20, choices=Licencia.choices)
    observaciones = models.TextField(max_length=1000)

    class Meta:
        ordering = ["-fecha", "-pk"]
