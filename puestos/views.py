from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.core.paginator import EmptyPage
from django.db.models import Max
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .busqueda import buscar, parametros, puestos_publicados, serializar
from .consulta import ESTADOS
from .forms import DeclaracionForm, InspeccionForm, PuestoForm
from .models import Declaracion, Inspeccion, Puesto


def contexto_resultados(request):
    filtros, origen, numero, errores = parametros(request.GET)
    publicados = puestos_publicados()
    total_publicados = publicados.count()
    busqueda = bool(filtros["q"] or filtros["distrito"] or filtros["ingrediente"] or filtros["estado"] or origen or "pagina" in request.GET)
    pagina = None
    codigo = 400 if errores else 200
    if not errores:
        try:
            pagina = buscar(publicados, filtros, origen, numero)
        except EmptyPage:
            errores = {"pagina": "La página indicada no existe."}
            codigo = 404
    parametros_url = request.GET.copy()
    parametros_url.pop("pagina", None)
    return {
        **filtros, "consulta": filtros["q"], "puestos": pagina or [], "pagina": pagina,
        "origen": origen, "busqueda": busqueda, "errores": errores,
        "total_publicados": total_publicados, "parametros_url": parametros_url.urlencode(),
    }, codigo


def buscar_api(request):
    if request.method != "GET":
        respuesta = JsonResponse({
            "resultados": [], "paginacion": None, "total_publicados": None, "html": None,
            "errores": {"metodo": "Usa GET para consultar los puestos."},
        }, status=405)
        respuesta["Allow"] = "GET"
        return respuesta
    contexto, codigo = contexto_resultados(request)
    pagina = contexto["pagina"]
    return JsonResponse({
        "resultados": [serializar(puesto) for puesto in contexto["puestos"]],
        "paginacion": {
            "pagina": pagina.number, "paginas": pagina.paginator.num_pages,
            "total": pagina.paginator.count, "por_pagina": pagina.paginator.per_page,
        } if pagina is not None else None,
        "total_publicados": contexto["total_publicados"],
        "html": render_to_string("resultados.html", contexto) if codigo == 200 else None,
        "errores": contexto["errores"],
    }, status=codigo)


def lista(request):
    contexto, codigo = contexto_resultados(request)
    publicados = puestos_publicados()
    distritos = publicados.order_by("distrito").values_list("distrito", flat=True).distinct()
    autenticado = request.user.is_authenticated
    es_inspector = autenticado and request.user.groups.filter(name="Inspector").exists()
    es_vendedor = autenticado and request.user.groups.filter(name="Vendedor").exists()
    return render(request, "lista.html", {
        **contexto, "estados": ESTADOS, "distritos": list(distritos),
        "propios": Puesto.objects.filter(vendedor=request.user) if es_vendedor else [],
        "pendientes": Puesto.objects.filter(declaracion__isnull=True) if es_inspector else [],
        "es_inspector": es_inspector, "es_vendedor": es_vendedor,
        "total_inspeccionados": publicados.filter(inspecciones__isnull=False).distinct().count(),
        "ultima_actualizacion": publicados.aggregate(fecha=Max("inspecciones__fecha"))["fecha"],
        "fuente": getattr(settings, "POTA_FUENTE_DATOS", ""),
    }, status=codigo)


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
