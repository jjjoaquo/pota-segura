from django import forms

from .models import Declaracion, Inspeccion, Puesto


class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = ["nombre", "distrito", "direccion", "latitud", "longitud"]


class DeclaracionForm(forms.ModelForm):
    class Meta:
        model = Declaracion
        fields = ["producto", "ingrediente_principal", "otros_ingredientes"]


class InspeccionForm(forms.ModelForm):
    class Meta:
        model = Inspeccion
        fields = ["licencia", "observaciones", "vigente_hasta", "hallazgos_pendientes"]
        widgets = {"vigente_hasta": forms.DateInput(attrs={"type": "date"})}
        labels = {
            "observaciones": "Observaciones públicas sobre higiene y conservación",
            "vigente_hasta": "Fecha de vencimiento registrada",
            "hallazgos_pendientes": "Hay observaciones pendientes de resolver",
        }
