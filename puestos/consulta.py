from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
import re

from django.db.models import Q

ESTADOS = {
    "vigente": ("✓", "Inspección vigente"),
    "por-vencer": ("◷", "Inspección por vencer"),
    "vencida": ("!", "Inspección vencida"),
    "observaciones": ("!", "Con observaciones pendientes"),
    "sin-vigencia": ("–", "Vigencia sin registrar"),
    "sin-inspeccion": ("–", "Sin inspección registrada"),
}


def estado_inspeccion(fecha, vencimiento, hallazgos, hoy):
    if fecha is None:
        return "sin-inspeccion"
    if hallazgos:
        return "observaciones"
    if vencimiento is None:
        return "sin-vigencia"
    if vencimiento < hoy:
        return "vencida"
    if vencimiento <= hoy + timedelta(days=7):
        return "por-vencer"
    return "vigente"


def filtro_estado(estado, hoy):
    aviso = hoy + timedelta(days=7)
    sin_hallazgos = Q(ultima_visita__isnull=False, hallazgos=False)
    return {
        "sin-inspeccion": Q(ultima_visita__isnull=True),
        "observaciones": Q(hallazgos=True),
        "sin-vigencia": sin_hallazgos & Q(vencimiento__isnull=True),
        "vencida": sin_hallazgos & Q(vencimiento__lt=hoy),
        "por-vencer": sin_hallazgos & Q(vencimiento__range=(hoy, aviso)),
        "vigente": sin_hallazgos & Q(vencimiento__gt=aviso),
    }[estado]


def coordenadas(datos):
    try:
        latitud, longitud = float(datos.get("lat", "")), float(datos.get("lon", ""))
    except (ValueError, TypeError):
        return None
    if -90 <= latitud <= 90 and -180 <= longitud <= 180:
        return latitud, longitud
    return None


def distancia_km(origen, puesto):
    if puesto.latitud is None or puesto.longitud is None:
        return None
    lat_a, lon_a = map(radians, origen)
    lat_b, lon_b = map(radians, (puesto.latitud, puesto.longitud))
    a = sin((lat_b - lat_a) / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin((lon_b - lon_a) / 2) ** 2
    return 6371 * 2 * asin(sqrt(min(1.0, a)))


def ingredientes(declaracion):
    nombres = [declaracion.ingrediente_principal, *re.split(r"[,;\n]+", declaracion.otros_ingredientes)]
    return list(dict.fromkeys(nombre.strip() for nombre in nombres if nombre.strip()))
