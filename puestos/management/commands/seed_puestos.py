from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from puestos.models import Declaracion, Inspeccion, Puesto

DATOS = [
    ("Muelle del Callao", "Callao", "Pota", -12.056, -77.149),
    ("Sabores de la Punta", "La Punta", "Pescado", -12.072, -77.165),
    ("Costa de Miraflores", "Miraflores", "Pota", -12.121, -77.034),
    ("Mercado de Jesús María", "Jesús María", "Pejerrey", -12.079, -77.051),
    ("Rincón de Breña", "Breña", "Pota", -12.061, -77.050),
    ("Puerto de Barranco", "Barranco", "Bonito", -12.147, -77.022),
    ("Mar de Chorrillos", "Chorrillos", "Pota", -12.170, -77.021),
    ("Ruta de Surquillo", "Surquillo", "Perico", -12.115, -77.012),
    ("Ceviche de Magdalena", "Magdalena del Mar", "Pota", -12.092, -77.076),
    ("Puesto de San Miguel", "San Miguel", "Pescado", -12.077, -77.093),
]


class Command(BaseCommand):
    help = "Carga 10 puestos ficticios y sus inspecciones. Se puede ejecutar varias veces."

    @transaction.atomic
    def handle(self, *args, **options):
        vendedor = self.cuenta_demo("pota_seed_vendedor")
        inspector = self.cuenta_demo("pota_seed_inspector")
        hoy = timezone.localdate()
        for indice, (nombre, distrito, ingrediente, latitud, longitud) in enumerate(DATOS):
            puesto, _ = Puesto.objects.update_or_create(
                vendedor=vendedor, nombre=f"Demo · {nombre}",
                defaults={"distrito": distrito, "direccion": "Ubicación referencial de prueba",
                          "latitud": latitud, "longitud": longitud},
            )
            Declaracion.objects.update_or_create(
                puesto=puesto,
                defaults={"producto": f"Ceviche de {ingrediente.lower()}",
                          "ingrediente_principal": ingrediente,
                          "otros_ingredientes": "Limón, cebolla, ají"},
            )
            diferencia = (25, 4, -3, 25)[indice % 4]
            pendiente = indice % 4 == 3
            Inspeccion.objects.update_or_create(
                puesto=puesto, inspector=inspector,
                defaults={"licencia": Inspeccion.Licencia.PRESENTADA,
                          "vigente_hasta": hoy + timedelta(days=diferencia),
                          "hallazgos_pendientes": pendiente,
                          "observaciones": "Registro ficticio para pruebas del buscador."},
            )
        self.stdout.write(self.style.SUCCESS("10 puestos de demostración disponibles."))

    @staticmethod
    def cuenta_demo(nombre):
        usuarios = get_user_model().objects
        usuario = usuarios.filter(username=nombre).first()
        if usuario is None:
            return usuarios.create_user(nombre, is_active=False)
        if usuario.is_active or usuario.has_usable_password():
            raise CommandError(f"La cuenta {nombre} está en uso. No se cargaron datos.")
        return usuario
