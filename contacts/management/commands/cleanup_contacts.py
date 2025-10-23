# contacts/management/commands/cleanup_contacts.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from contacts.models import Kontakt
from datetime import timedelta

class Command(BaseCommand):
    help = 'Provádí pravidelnou údržbu kontaktů: deaktivuje po 7x nedovoláno a odebírá přiřazení po 90 dnech od prodeje.'

    def handle(self, *args, **options):
        now = timezone.now()
        ninety_days_ago = now - timedelta(days=90)

        self.stdout.write('Spouštím pravidelnou údržbu kontaktů...')

        # 1. Deaktivace kontaktů s 7 a více "nedovoláno" v řadě
        deactivated_count = Kontakt.objects.filter(
            nedovolano_v_rade__gte=7,
            aktivni=True
        ).update(aktivni=False)

        self.stdout.write(self.style.SUCCESS(f'Deaktivováno {deactivated_count} kontaktů kvůli 7x nedovoláno.'))

        # 2. Odebrání přiřazení u kontaktů, kde prodej je starší než 90 dní
        unassigned_count = Kontakt.objects.filter(
            datum_posledniho_prodeje__isnull=False,
            datum_posledniho_prodeje__lte=ninety_days_ago,
            assigned_operator__isnull=False
        ).update(assigned_operator=None)

        self.stdout.write(self.style.SUCCESS(f'Odebráno přiřazení u {unassigned_count} kontaktů po 90 dnech od prodeje.'))

        self.stdout.write(self.style.SUCCESS('Pravidelná údržba kontaktů byla úspěšně dokončena.'))