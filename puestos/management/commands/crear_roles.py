from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea los grupos Vendedor e Inspector."

    def handle(self, *args, **options):
        for nombre in ("Vendedor", "Inspector"):
            Group.objects.get_or_create(name=nombre)
        self.stdout.write("Roles disponibles: Vendedor e Inspector")
