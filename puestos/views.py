from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeclaracionForm, InspeccionForm, PuestoForm
from .models import Declaracion, Inspeccion, Puesto


def lista(request):
    puestos = Puesto.objects.filter(declaracion__isnull=False).select_related("declaracion")
    consulta = request.GET.get("q", "").strip()
    producto = request.GET.get("producto", "").strip()
    if consulta:
        puestos = puestos.filter(Q(nombre__icontains=consulta) | Q(distrito__icontains=consulta))
    if producto:
        puestos = puestos.filter(declaracion__producto__iexact=producto)
    productos = Declaracion.objects.order_by("producto").values_list("producto", flat=True).distinct()
    propios = Puesto.objects.filter(vendedor=request.user) if request.user.is_authenticated else []
    es_inspector = request.user.is_authenticated and request.user.groups.filter(name="Inspector").exists()
    return render(request, "lista.html", {
        "puestos": puestos.order_by("nombre", "pk"), "productos": productos,
        "propios": propios, "consulta": consulta, "producto": producto,
        "pendientes": Puesto.objects.filter(declaracion__isnull=True) if es_inspector else [],
        "es_inspector": es_inspector,
        "es_vendedor": request.user.groups.filter(name="Vendedor").exists() if request.user.is_authenticated else False,
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
