from datetime import datetime, timezone as utc
from hashlib import sha256

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.db.models import F
from django.utils import timezone

from .models import IntentosAcceso


class FormularioAcceso(AuthenticationForm):
    recordarme = forms.BooleanField(required=False, label="Recordarme")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Escribe tu usuario", "autocomplete": "username",
        })
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update({
            "placeholder": "Escribe tu contraseña", "autocomplete": "current-password",
            "aria-describedby": "ayuda-contrasena",
        })


class Acceso(LoginView):
    template_name = "login.html"
    authentication_form = FormularioAcceso

    def post(self, request, *args, **kwargs):
        ahora = timezone.now()
        duracion = 15 * 60
        ventana = int(ahora.timestamp()) // duracion
        vence = datetime.fromtimestamp((ventana + 1) * duracion, tz=utc.utc)
        usuario = request.POST.get("username", "").strip().casefold()[:150]
        origen = request.META.get("REMOTE_ADDR", "")
        identificador = sha256(f"{ventana}:{origen}:{usuario}".encode()).hexdigest()
        IntentosAcceso.objects.filter(vence__lte=ahora).delete()
        IntentosAcceso.objects.get_or_create(identificador=identificador, defaults={"vence": vence})
        permitido = IntentosAcceso.objects.filter(
            identificador=identificador, cantidad__lt=8,
        ).update(cantidad=F("cantidad") + 1)
        if not permitido:
            self.extra_context = {"limite_alcanzado": True}
            return self.render_to_response(
                self.get_context_data(form=self.get_form()), status=429,
                headers={"Retry-After": str(int((vence - ahora).total_seconds()) + 1)},
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        self.request.session.set_expiry(None if form.cleaned_data["recordarme"] else 0)
        return respuesta
