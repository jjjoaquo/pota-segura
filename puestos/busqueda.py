from django.core.paginator import Paginator
from django.db.models import F, Func, OuterRef, Q, Subquery, Value
from django.db.models.functions import Lower, Replace
from django.urls import reverse
from django.utils import timezone

from .consulta import ESTADOS, coordenadas, distancia_km, estado_inspeccion, filtro_estado, ingredientes
from .models import Inspeccion, Puesto

# Incluye las vocales acentuadas y la eñe, en ambos casos, también en SQLite.
CARACTERES = zip("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN", strict=True)
EQUIVALENCIAS = tuple(CARACTERES)
TRADUCCION = str.maketrans(dict(EQUIVALENCIAS))


class SinTildes(Func):
    arity = 1

    def as_sqlite(self, compiler, connection, **extra_context):
        expresion = self.source_expressions[0]
        for original, sustituto in EQUIVALENCIAS:
            expresion = Replace(expresion, Value(original), Value(sustituto))
        return Lower(expresion).as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler, connection, template="LOWER(TRANSLATE(%(expressions)s, 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'))",
            **extra_context,
        )


def parametros(datos):
    filtros = {
        "q": datos.get("q", "").strip(),
        "ingrediente": (datos.get("ingrediente") or datos.get("producto", "")).strip(),
        "estado": datos.get("estado", ""),
        "orden": datos.get("orden") or "reciente",
    }
    errores = {}
    for campo in ("q", "ingrediente"):
        if len(filtros[campo]) > 100:
            errores[campo] = "Escribe como máximo 100 caracteres."
        elif "\x00" in filtros[campo]:
            errores[campo] = "El texto contiene un carácter no válido."
    if filtros["estado"] and filtros["estado"] not in ESTADOS:
        errores["estado"] = "Selecciona un estado de inspección válido."
    if filtros["orden"] not in {"reciente", "cerca"}:
        errores["orden"] = "Selecciona un orden válido."
    origen = coordenadas(datos) if filtros["orden"] == "cerca" else None
    if filtros["orden"] == "cerca" and origen is None:
        errores["orden"] = "Activa tu ubicación para ordenar por cercanía."
    pagina = 1
    valor = datos.get("pagina", "1")
    if valor.isascii() and valor.isdecimal() and len(valor) <= 8 and int(valor) >= 1:
        pagina = int(valor)
    else:
        errores["pagina"] = "Indica un número de página positivo."
    return filtros, origen, pagina, errores


def puestos_publicados():
    return Puesto.objects.filter(declaracion__isnull=False)


def buscar(publicados, filtros, origen, pagina, inicial=False):
    ultima = Inspeccion.objects.filter(puesto_id=OuterRef("pk"))
    puestos = publicados.select_related("declaracion").annotate(
        ultima_visita=Subquery(ultima.values("fecha")[:1]),
        vencimiento=Subquery(ultima.values("vigente_hasta")[:1]),
        hallazgos=Subquery(ultima.values("hallazgos_pendientes")[:1]),
    )
    if filtros["q"]:
        texto = filtros["q"].translate(TRADUCCION).lower()
        puestos = puestos.alias(nombre_simple=SinTildes("nombre"), distrito_simple=SinTildes("distrito"))
        puestos = puestos.filter(Q(nombre_simple__contains=texto) | Q(distrito_simple__contains=texto))
    if filtros["ingrediente"]:
        texto = filtros["ingrediente"].translate(TRADUCCION).lower()
        puestos = puestos.alias(
            producto_simple=SinTildes("declaracion__producto"),
            ingrediente_simple=SinTildes("declaracion__ingrediente_principal"),
            otros_simples=SinTildes("declaracion__otros_ingredientes"),
        ).filter(
            Q(producto_simple__contains=texto)
            | Q(ingrediente_simple__contains=texto)
            | Q(otros_simples__contains=texto)
        )
    hoy = timezone.localdate()
    if filtros["estado"]:
        puestos = puestos.filter(filtro_estado(filtros["estado"], hoy))
    puestos = puestos.order_by(F("ultima_visita").desc(nulls_last=True), "-pk")
    if origen:
        puestos = list(puestos)
        for puesto in puestos:
            puesto.distancia = distancia_km(origen, puesto)
        puestos.sort(key=lambda puesto: (
            puesto.distancia is None, puesto.distancia if puesto.distancia is not None else 0,
        ))
    resultados = Paginator(puestos, 6 if inicial else 10).page(pagina)
    for puesto in resultados:
        puesto.ingredientes = ingredientes(puesto.declaracion)
        puesto.estado = estado_inspeccion(puesto.ultima_visita, puesto.vencimiento, puesto.hallazgos, hoy)
        puesto.icono_estado, puesto.texto_estado = ESTADOS[puesto.estado]
    return resultados


def serializar(puesto):
    distancia = getattr(puesto, "distancia", None)
    return {
        "id": puesto.pk,
        "nombre": puesto.nombre,
        "distrito": puesto.distrito,
        "direccion": puesto.direccion,
        "producto": puesto.declaracion.producto,
        "ingredientes": puesto.ingredientes,
        "ultima_inspeccion": timezone.localtime(puesto.ultima_visita).isoformat() if puesto.ultima_visita else None,
        "estado": {"codigo": puesto.estado, "icono": puesto.icono_estado, "texto": puesto.texto_estado},
        "distancia_km": round(distancia, 1) if distancia is not None else None,
        "url_detalle": reverse("ficha", args=[puesto.pk]),
    }
