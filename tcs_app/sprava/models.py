from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords

class CustomUser(AbstractUser):
 
    first_name = models.CharField(max_length=150, blank=False, verbose_name='Jméno')
    last_name = models.CharField(max_length=150, blank=False, verbose_name='Příjmení')
    
   
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name='E-mail')

    # Naše nová, specifická pole
   
    kod_operatora = models.CharField(max_length=50, unique=True, blank=False, verbose_name="Kód operátora")
    
   
    telefonni_cislo = models.CharField(max_length=20, blank=False, verbose_name="Telefonní číslo")
    
   
    uvazek_hodiny = models.PositiveIntegerField(blank=False, verbose_name="Úvazek (v hodinách)")
    
    
    datum_narozeni = models.DateField(null=True, blank=True, verbose_name="Datum narození")
    svatek = models.DateField(null=True, blank=True, verbose_name="Svátek")

  
    history = HistoricalRecords()

    def __str__(self):

        return f"{self.first_name} {self.last_name} ({self.username})"
    
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email', 'kod_operatora', 'telefonni_cislo', 'uvazek_hodiny']