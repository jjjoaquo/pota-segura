from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import F, Max, OuterRef, Q, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .consulta import ESTADOS, coordenadas, distancia_km, estado_inspeccion, filtro_estado, ingredientes
from .forms import DeclaracionForm, InspeccionForm, PuestoForm
from .models import Declaracion, Inspeccion, Puesto


def lista(request):
    publicados = Puesto.objects.filter(declaracion__isnull=False)
    ultima = Inspeccion.objects.filter(puesto_id=OuterRef("pk"))
    puestos = publicados.select_related("declaracion").annotate(
        ultima_visita=Subquery(ultima.values("fecha")[:1]),
        vencimiento=Subquery(ultima.values("vigente_hasta")[:1]),
        hallazgos=Subquery(ultima.values("hallazgos_pendientes")[:1]),
    )
    consulta = request.GET.get("q", "").strip()
    ingrediente = (request.GET.get("ingrediente") or request.GET.get("producto", "")).strip()
    estado = request.GET.get("estado", "")
    orden = request.GET.get("orden", "")
    origen = coordenadas(request.GET) if orden == "cerca" else None
    if consulta:
        puestos = puestos.filter(Q(nombre__icontains=consulta) | Q(distrito__icontains=consulta))
    if ingrediente:
        puestos = puestos.filter(
            Q(declaracion__producto__icontains=ingrediente)
            | Q(declaracion__ingrediente_principal__icontains=ingrediente)
            | Q(declaracion__otros_ingredientes__icontains=ingrediente)
        )
    if estado in ESTADOS:
        puestos = puestos.filter(filtro_estado(estado))
    puestos = puestos.order_by(F("ultima_visita").desc(nulls_last=True), "-pk")
    if origen:
        puestos = list(puestos)
        for puesto in puestos:
            puesto.distancia = distancia_km(origen, puesto)
        puestos.sort(key=lambda puesto: (
            puesto.distancia is None, puesto.distancia if puesto.distancia is not None else 0,
        ))
    busqueda = bool(consulta or ingrediente or estado in ESTADOS or orden == "cerca")
    if not busqueda:
        puestos = puestos[:6]
    hoy = timezone.localdate()
    for puesto in puestos:
        puesto.ingredientes = ingredientes(puesto.declaracion)
        puesto.estado = estado_inspeccion(puesto.ultima_visita, puesto.vencimiento, puesto.hallazgos, hoy)
        puesto.icono_estado, puesto.texto_estado = ESTADOS[puesto.estado]
    distritos = publicados.order_by("distrito").values_list("distrito", flat=True).distinct()
    autenticado = request.user.is_authenticated
    es_inspector = autenticado and request.user.groups.filter(name="Inspector").exists()
    es_vendedor = autenticado and request.user.groups.filter(name="Vendedor").exists()
    return render(request, "lista.html", {
        "puestos": puestos, "consulta": consulta, "ingrediente": ingrediente,
        "estados": ESTADOS, "estado": estado, "orden": orden, "origen": origen,
        "busqueda": busqueda, "distritos": list(distritos),
        "propios": Puesto.objects.filter(vendedor=request.user) if es_vendedor else [],
        "pendientes": Puesto.objects.filter(declaracion__isnull=True) if es_inspector else [],
        "es_inspector": es_inspector, "es_vendedor": es_vendedor,
        "total_inspeccionados": publicados.filter(inspecciones__isnull=False).distinct().count(),
        "ultima_actualizacion": publicados.aggregate(fecha=Max("inspecciones__fecha"))["fecha"],
        "fuente": getattr(settings, "POTA_FUENTE_DATOS", ""),
    })


def ficha(request, pk):
    puesto = get_object_or_404(Puesto.objects.select_related("declaracion"), pk=pk)
    usuario = request.user
    titular = usuario.is_authenticated and puesto.vendedor_id == usuario.pk
    inspector = usuario.is_authenticated and usuario.groups.filter(name="Inspector").exists()
    if not (titular or inspector or hasattr(puesto, "declaracion")):
        raise Http404
    return render(request, "ficha.html", {
        "puesto": puesto, "titular": titular, "inspector": inspector,
        "visita": puesto.inspecciones.first(),
    })


@login_required
def registrar(request):
    if not request.user.groups.filter(name="Vendedor").exists():
        raise PermissionDenied
    form = PuestoForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        puesto = form.save(commit=False)
        puesto.vendedor = request.user
        puesto.save()
        return redirect("ficha", pk=puesto.pk)
    return render(request, "form.html", {"form": form, "titulo": "Registrar puesto"})


@login_required
def declarar(request, pk):
    puesto = get_object_or_404(Puesto, pk=pk)
    if puesto.vendedor_id != request.user.pk or not request.user.groups.filter(name="Vendedor").exists():
        raise PermissionDenied
    actual = Declaracion.objects.filter(puesto=puesto).first()
    form = DeclaracionForm(request.POST if request.method == "POST" else None, instance=actual)
    if form.is_valid():
        Declaracion.objects.update_or_create(puesto=puesto, defaults=form.cleaned_data)
        return redirect("ficha", pk=pk)
    return render(request, "form.html", {"form": form, "titulo": "Declarar producto"})


@login_required
def inspeccionar(request, pk):
    if not request.user.groups.filter(name="Inspector").exists():
        raise PermissionDenied
    puesto = get_object_or_404(Puesto, pk=pk)
    form = InspeccionForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        Inspeccion.objects.create(puesto=puesto, inspector=request.user, **form.cleaned_data)
        return redirect("ficha", pk=pk)
    return render(request, "form.html", {"form": form, "titulo": "Registrar inspección"})


@login_required
def historial(request, pk):
    if not request.user.groups.filter(name="Inspector").exists():
        raise PermissionDenied
    puesto = get_object_or_404(Puesto, pk=pk)
    return render(request, "historial.html", {"puesto": puesto, "visitas": puesto.inspecciones.all()})


def salud(request):
    connection.ensure_connection()
    return JsonResponse({"estado": "ok"})


def informacion(request, tema):
    titulos = {
        "contacto": "Contacto", "aviso": "Aviso legal", "privacidad": "Política de privacidad",
        "reportar": "Reportar un puesto", "ayuda-de-acceso": "¿Olvidaste tu contraseña?",
    }
    if tema not in titulos:
        raise Http404
    return render(request, "informacion.html", {
        "tema": tema, "titulo": titulos[tema], "contacto": getattr(settings, "POTA_CONTACTO_EMAIL", ""),
    })
