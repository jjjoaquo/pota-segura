from django import forms

from .models import Declaracion, Inspeccion, Puesto


class PuestoForm(forms.ModelForm):
    class Meta:
        model = Puesto
        fields = ["nombre", "distrito"]


class DeclaracionForm(forms.ModelForm):
    class Meta:
        model = Declaracion
        fields = ["producto", "ingrediente_principal", "otros_ingredientes"]


class InspeccionForm(forms.ModelForm):
    class Meta:
        model = Inspeccion
        fields = ["licencia", "observaciones"]
        labels = {"observaciones": "Observaciones públicas sobre higiene y conservación"}
