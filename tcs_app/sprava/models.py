from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    # Pole, která jsou již v AbstractUser, ale my je chceme mít povinná
    first_name = models.CharField(max_length=150, blank=False, verbose_name='Jméno')
    last_name = models.CharField(max_length=150, blank=False, verbose_name='Příjmení')
    email = models.EmailField(blank=True, verbose_name='E-mail') # Nepovinné

    # Naše nová, specifická pole
    kod_operatora = models.CharField(max_length=50, unique=True, verbose_name="Kód operátora")
    telefonni_cislo = models.CharField(max_length=20, verbose_name="Telefonní číslo")
    uvazek_hodiny = models.PositiveIntegerField(verbose_name="Úvazek (v hodinách)")
    
    datum_narozeni = models.DateField(null=True, blank=True, verbose_name="Datum narození")
    svatek = models.DateField(null=True, blank=True, verbose_name="Svátek")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    REQUIRED_FIELDS = ['first_name', 'last_name', 'kod_operatora', 'telefonni_cislo', 'uvazek_hodiny']