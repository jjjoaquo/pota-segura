from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Declaracion, Inspeccion, Puesto


class FlujoPuestosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        vendedor = Group.objects.create(name="Vendedor")
        inspector = Group.objects.create(name="Inspector")
        cls.titular = User.objects.create_user("titular", password="clave-para-pruebas")
        cls.otro = User.objects.create_user("otro")
        cls.inspector = User.objects.create_user("inspector")
        vendedor.user_set.add(cls.titular, cls.otro)
        inspector.user_set.add(cls.inspector)
        cls.puesto = Puesto.objects.create(vendedor=cls.titular, nombre="Costa", distrito="Callao")

    def test_login_valido_e_invalido(self):
        self.assertEqual(self.client.post(reverse("login"), {
            "username": "titular", "password": "incorrecta",
        }).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post(reverse("login"), {
            "username": "titular", "password": "clave-para-pruebas",
        }), reverse("lista"))

    def test_puesto_pertenece_al_vendedor_autenticado(self):
        self.client.force_login(self.titular)
        self.client.post(reverse("registrar"), {"nombre": "Puerto", "distrito": "La Punta"})
        self.assertEqual(Puesto.objects.get(nombre="Puerto").vendedor, self.titular)

    def test_otro_vendedor_no_puede_declarar(self):
        self.client.force_login(self.otro)
        respuesta = self.client.post(reverse("declarar", args=[self.puesto.pk]), {
            "producto": "Ceviche de pota", "ingrediente_principal": "Pota",
        })
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Declaracion.objects.exists())

    def test_vendedor_no_puede_inspeccionar(self):
        self.client.force_login(self.titular)
        respuesta = self.client.post(reverse("inspeccionar", args=[self.puesto.pk]), {
            "licencia": "presentada", "observaciones": "Cadena de frío registrada",
        })
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Inspeccion.objects.exists())

    def test_ficha_publica_muestra_solo_la_ultima_visita(self):
        Declaracion.objects.create(
            puesto=self.puesto, producto="Ceviche de pota", ingrediente_principal="Pota",
        )
        url = reverse("ficha", args=[self.puesto.pk])
        self.assertContains(self.client.get(url), "Sin inspección registrada")
        self.client.force_login(self.inspector)
        for observacion in ["Visita anterior", "Visita reciente"]:
            self.assertRedirects(self.client.post(reverse("inspeccionar", args=[self.puesto.pk]), {
                "licencia": "presentada", "observaciones": observacion,
            }), url)
        self.client.logout()
        respuesta = self.client.get(url)
        self.assertContains(respuesta, "Visita reciente")
        self.assertNotContains(respuesta, "Visita anterior")
        self.assertContains(self.client.get(reverse("lista"), {
            "q": "Callao", "producto": "Ceviche de pota",
        }), "Costa")

    def test_consulta_inicial_y_filtros_de_inspeccion(self):
        from datetime import timedelta

        from django.utils import timezone

        url = reverse("lista")
        self.assertContains(self.client.get(url), "Busca por distrito o nombre para empezar")
        self.assertNotContains(self.client.get(url), "Sin resultados.")
        self.assertContains(self.client.get(url, {"q": "Cusco"}), "Aún no hay puestos publicados.")
        Declaracion.objects.create(
            puesto=self.puesto, producto="Ceviche", ingrediente_principal="Pota",
        )
        Inspeccion.objects.create(
            puesto=self.puesto, inspector=self.inspector, licencia="presentada",
            observaciones="Visita registrada", vigente_hasta=timezone.localdate() + timedelta(days=5),
        )
        self.assertContains(self.client.get(url, {
            "ingrediente": "pota", "estado": "por-vencer",
        }), "Ver detalle de Costa")
        self.assertNotContains(self.client.get(url, {
            "estado": "vigente",
        }), "Ver detalle de Costa")

    def test_limite_de_intentos_del_acceso(self):
        from unittest.mock import patch

        from django.utils import timezone

        url = reverse("login")
        self.assertNotContains(self.client.get(url), "Usuario o contraseña incorrectos")
        datos = {"username": "titular", "password": "incorrecta"}
        with patch("puestos.acceso.timezone.now", return_value=timezone.now()):
            for _ in range(8):
                self.assertContains(self.client.post(url, datos), "Usuario o contraseña incorrectos")
            respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn("Retry-After", respuesta.headers)
