from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Declaracion, Inspeccion, Puesto


class BusquedaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("persona-prueba")
        cls.puesto = cls.publicar("Rincón de Pota", "Jesús María")
        cls.publicar("Puerto de pescado", "Callao", "Bonito")
        Puesto.objects.create(vendedor=cls.usuario, nombre="Borrador", distrito="Jesús María")
        hoy = timezone.localdate()
        for dias in (-2, 3):
            Inspeccion.objects.create(
                puesto=cls.puesto, inspector=cls.usuario, vigente_hasta=hoy + timedelta(days=dias),
                licencia=Inspeccion.Licencia.PRESENTADA, observaciones="Visita de prueba",
            )

    @classmethod
    def publicar(cls, nombre, distrito, principal="Pota"):
        puesto = Puesto.objects.create(vendedor=cls.usuario, nombre=nombre, distrito=distrito)
        Declaracion.objects.create(
            puesto=puesto, producto=f"Ceviche de {principal}", ingrediente_principal=principal,
            otros_ingredientes="Ají, limón",
        )
        return puesto

    def consultar(self, **filtros):
        respuesta = self.client.get(reverse("buscar_api"), filtros)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def test_publicados_y_ultima_inspeccion_sin_n_mas_uno(self):
        with self.assertNumQueries(3):
            datos = self.consultar()
        self.assertEqual(datos["total_publicados"], 2)
        self.assertEqual(datos["paginacion"]["total"], 2)
        self.assertEqual(datos["resultados"][0]["estado"]["codigo"], "por-vencer")
        self.assertIsNotNone(datos["resultados"][0]["ultima_inspeccion"])
        self.assertIsNone(datos["resultados"][1]["ultima_inspeccion"])

    def test_filtros_combinados_con_mayusculas_y_tildes(self):
        datos = self.consultar(q="JESUS MARIA", ingrediente="AJI", estado="por-vencer")
        self.assertEqual([x["nombre"] for x in datos["resultados"]], ["Rincón de Pota"])
        self.assertEqual(self.consultar(q="rincón")["paginacion"]["total"], 1)
        self.assertEqual(self.consultar(q="RINCON")["paginacion"]["total"], 1)

    def test_diferencia_base_sin_publicaciones_de_busqueda_sin_coincidencias(self):
        datos = self.consultar(q="Cusco")
        self.assertEqual(datos["resultados"], [])
        self.assertEqual(datos["paginacion"]["total"], 0)
        self.assertIn("Sin resultados.", datos["html"])
        Declaracion.objects.all().delete()
        datos = self.consultar(q="Cusco")
        self.assertEqual(datos["total_publicados"], 0)
        self.assertIn("Aún no hay puestos publicados.", datos["html"])
        self.assertNotIn("Sin resultados.", datos["html"])

    def test_paginacion_conserva_filtros(self):
        for i in range(10):
            self.publicar(f"Puesto {i}", "Jesús María")
        primera = self.consultar(q="Jesus Maria")
        siguiente = self.consultar(q="Jesus Maria", pagina="2")
        self.assertEqual(len(primera["resultados"]), 10)
        self.assertEqual(len(siguiente["resultados"]), 1)
        self.assertNotIn(siguiente["resultados"][0]["id"], [x["id"] for x in primera["resultados"]])
        self.assertIn("q=Jesus+Maria&amp;pagina=2", primera["html"])
        sin_filtros = self.consultar()
        self.assertEqual(sin_filtros["paginacion"]["por_pagina"], self.consultar(pagina="2")["paginacion"]["por_pagina"])

    def test_parametros_invalidos_y_pagina_inexistente(self):
        url = reverse("buscar_api")
        respuesta = self.client.get(url, {"estado": "otro", "pagina": "-2", "orden": "cerca"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(set(respuesta.json()["errores"]), {"estado", "pagina", "orden"})
        self.assertEqual(self.client.get(url, {"pagina": "100"}).status_code, 404)
        self.assertEqual(self.client.post(url).status_code, 405)

    def test_seed_repetible_con_estados_variados(self):
        for _ in range(2):
            call_command("seed_puestos", stdout=StringIO())
        self.assertEqual(Puesto.objects.filter(nombre__startswith="Demo ·").count(), 10)
        datos = self.consultar(q="Demo")
        self.assertEqual(datos["paginacion"]["total"], 10)
        self.assertEqual(
            {puesto["estado"]["codigo"] for puesto in datos["resultados"]},
            {"vigente", "por-vencer", "vencida", "observaciones"},
        )
