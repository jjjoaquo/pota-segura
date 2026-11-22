from django.contrib import admin

from .models import Reporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ("puesto", "motivo", "fecha", "revisado")
    list_filter = ("revisado", "motivo")
    search_fields = ("puesto__nombre", "puesto__distrito", "descripcion")
    list_select_related = ("puesto",)
    ordering = ("-fecha",)
    readonly_fields = ("puesto", "autor", "motivo", "descripcion", "fecha")

    def has_add_permission(self, request):
        return False
