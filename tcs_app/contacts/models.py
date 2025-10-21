# contacts/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import datetime # Důležitý import

STATUS_CHOICES = [
    ('nedovolano', 'Nedovoláno'),
    ('nezajem', 'Nezájem'),
    ('neexistujici', 'Neexistující číslo/blokace'),
    ('nemluveno', 'Nemluveno s KO'),
    ('nerelevance', 'Nerelevance'),
    ('prodej', 'Prodej'),
    ('vip', 'Přidáno do VIP'),
    ('volat_pozdeji', 'Volat později'),
    ('predat_operatorovi', 'Předat na jiného operátora'),
]

# --- PŘIDÁNO (pro statistiky) ---
class TypAkce(models.TextChoices):
    SPOJENY_HOVOR = 'SPOJENY', 'Spojený hovor'
    NESPOJENY_HOVOR = 'NESPOJENY', 'Nespojený hovor'
    INTERNI_AKCE = 'INTERNI', 'Interní akce'
# --- KONEC PŘIDÁNÍ ---


class Kontakt(models.Model):
    # ... všechna pole zůstávají stejná ...
    info_2 = models.CharField(max_length=50, blank=True,  null=True, db_index=True, unique=True, verbose_name="Zákaznické číslo")
    info_3 = models.CharField(max_length=50, blank=True, default='', db_index=True, verbose_name="Přednostní číslo")
    ansprache = models.CharField(max_length=20, blank=True, default='', verbose_name="Oslovení (Pohlaví)")
    titel = models.CharField(max_length=20, blank=True, default='', verbose_name="Titul")
    vorname = models.CharField(max_length=100, blank=True, default='', verbose_name="Jméno")
    nachname = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name="Příjmení")
    dlbs = models.CharField(max_length=50, blank=True, default='', verbose_name="Poslední objednávka")
    info_1 = models.CharField(max_length=50, blank=True, default='', verbose_name="DBK")
    telefon1 = models.CharField(max_length=30, blank=True, default='', db_index=True, verbose_name="Telefon 1")
    telefon2 = models.CharField(max_length=30, blank=True, default='', verbose_name="Telefon 2")
    geburtsdatum = models.DateField(null=True, blank=True, verbose_name="Datum narození")
    datum_letztkontakt = models.CharField(max_length=20, blank=True, default='', verbose_name="Poslední kontakt")
    tlm_kampagne_2_zielprodukt = models.CharField(max_length=100, blank=True, default='', verbose_name="Kampaň")
    strasse = models.CharField(max_length=100, blank=True, default='', verbose_name="Ulice")
    ort = models.CharField(max_length=100, blank=True, default='', verbose_name="Město")
    plz = models.CharField(max_length=20, blank=True, default='', verbose_name="Poštovní směrovací číslo")
    recency = models.CharField(max_length=20, blank=True, default='', verbose_name="Typ zákazníka")
    vip = models.BooleanField(default=False, verbose_name="VIP kontakt")
    vip_pridano = models.DateTimeField(null=True, blank=True, verbose_name="Do VIP přidáno dne")
    vip_poznamka = models.TextField(blank=True, default='', verbose_name="Interní poznámka k VIP")
    trvale_blokovan = models.BooleanField(default=False, verbose_name="Trvale blokovaný kontakt")
    nedovolano_pocet = models.PositiveIntegerField(default=0, verbose_name="Počet pokusů Nedovoláno")
    
    # --- PŘIDÁNO (pro novou logiku statusů) ---
    nedovolano_v_rade = models.PositiveIntegerField(default=0, verbose_name="Počet 'Nedovoláno' v řadě")
    # --- KONEC PŘIDÁNÍ ---

    odlozeny_nedovolano_pokusy = models.PositiveIntegerField(default=0, verbose_name="Počet pokusů Nedovoláno (odložené)")
    blokace_do = models.DateTimeField(null=True, blank=True, verbose_name="Blokace do")
    aktivni = models.BooleanField(default=True, verbose_name="Aktivní kontakt")
    assigned_operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_contacts",
        verbose_name="Přiřazený operátor",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Poslední aktualizace")
    datum_prirazeni = models.DateTimeField(  
        null=True,  
        blank=True,  
        verbose_name="Datum posledního přiřazení"  
    )
    
    # === ZDE JE PŘIDANÉ NOVÉ POLE ===
    deaktivovan_do = models.DateField(null=True, blank=True, verbose_name="Deaktivován do")
    # =================================

    def __str__(self):
        full_name = f"{self.vorname} {self.nachname}".strip()
        return f"{full_name} ({self.info_2 or 'bez čísla'})"

    @property
    def vek(self):
        if not self.geburtsdatum:
            return None
        today = timezone.now().date()
        return today.year - self.geburtsdatum.year - ((today.month, today.day) < (self.geburtsdatum.month, self.geburtsdatum.day))

    def _format_date_string(self, date_string):
        if not date_string:
            return "-"
        formats_to_try = ['%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']
        for fmt in formats_to_try:
            try:
                date_part = date_string.split(' ')[0]
                date_obj = datetime.strptime(date_part, fmt).date()
                return date_obj.strftime('%d.%m.%Y')
            except (ValueError, IndexError):
                continue
        return date_string

    @property
    def posledni_objednavka_format(self):
        return self._format_date_string(self.dlbs)

    @property
    def posledni_kontakt_format(self):
        return self._format_date_string(self.datum_letztkontakt)

    class Meta:
        verbose_name = "Kontakt"
        verbose_name_plural = "Kontakty"


class Historie(models.Model):  
    kontakt = models.ForeignKey(Kontakt, on_delete=models.CASCADE, related_name='historie')  
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)  
    datum_cas = models.DateTimeField(auto_now_add=True)  
      
    # --- PŘIDÁNO (pro statistiky) ---
    typ_akce = models.CharField(
        max_length=20,
        choices=TypAkce.choices,
        verbose_name="Typ akce",
        null=True, 
        blank=True
    )
    # --- KONEC PŘIDÁNÍ ---

    status = models.CharField(  
        max_length=20,   
        choices=STATUS_CHOICES,   
        verbose_name="Status hovoru",  
        blank=True,
        default=''  
    )  
    poznamka = models.TextField(verbose_name="Poznámka k hovoru")  
    naplanovany_hovor = models.DateTimeField(  
        null=True,   
        blank=True,   
        verbose_name="Datum naplánovaného hovoru"  
    )
    
    # --- PŘIDÁNO (pro status Prodej/VIP) ---
    hodnota_objednavky = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Hodnota objednávky"
    )
    # --- KONEC PŘIDÁNÍ ---

# ... zbytek souboru (Korespondence, DopisovaSablona, atd.) zůstává stejný ...
class Korespondence(models.Model):
    kontakt = models.ForeignKey(Kontakt, on_delete=models.CASCADE, related_name="korespondence")
    datum = models.DateTimeField(auto_now_add=True, verbose_name="Datum vytvoření")
    predmet = models.CharField(max_length=200, verbose_name="Předmět dopisu")
    soubor = models.FileField(upload_to='dokumenty/', verbose_name="Soubor dopisu")
    poznamka = models.TextField(blank=True, verbose_name="Poznámka")

    def __str__(self):
        return f"{self.kontakt} - {self.predmet} ({self.datum.strftime('%d.%m.%Y')})"

    class Meta:
        verbose_name = "Korespondence"
        verbose_name_plural = "Korespondence"
        ordering = ['-datum']


class DopisovaSablona(models.Model):
    nazev = models.CharField(max_length=100, verbose_name="Název šablony")
    predmet = models.CharField(max_length=200, verbose_name="Předmět dopisu")
    text_muz = models.TextField(blank=True, default='', verbose_name="Text pro muže", help_text="Text dopisu pro muže")
    text_zena = models.TextField(blank=True, default='', verbose_name="Text pro ženy", help_text="Text dopisu pro ženy")
    editovatelna = models.BooleanField(default=False, verbose_name="Editovatelná operátorem", help_text="Může operátor upravit text?")

    def __str__(self):
        return self.nazev

    class Meta:
        verbose_name = "Dopisová šablona"
        verbose_name_plural = "Dopisové šablony"


class UserDopisovaSablona(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Uživatel (operátor)")
    base_sablona = models.ForeignKey(DopisovaSablona, on_delete=models.CASCADE, verbose_name="Základní šablona")
    text_muz = models.TextField(blank=True, default='', verbose_name="Uživatelský text pro muže")
    text_zena = models.TextField(blank=True, default='', verbose_name="Uživatelský text pro ženy")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Datum poslední úpravy")

    class Meta:
        verbose_name = "Uživatelská dopisová šablona"
        verbose_name_plural = "Uživatelské dopisové šablony"
        unique_together = ('user', 'base_sablona')

    def __str__(self):
        return f"{self.user.username} - {self.base_sablona.nazev}"


class ProduktovaNabidka(models.Model):
    nazev = models.CharField(max_length=200, verbose_name="Název nabídky")
    text = models.TextField(verbose_name="Text nabídky")
    obrazek = models.ImageField(upload_to='nabidky/', verbose_name="Obrázek produktu", blank=True, null=True)

    def __str__(self):
        return self.nazev

    class Meta:
        verbose_name = "Produktová nabídka"
        verbose_name_plural = "Produktové nabídky"


class OperatorAction(models.Model):
    OPERATOR_WORK = 'operator_work'
    VIP_INTERFACE = 'vip_interface'
    CALL_HANDLING = 'call_handling'
    OTHER = 'other'
    ACTION_CHOICES = [
        (OPERATOR_WORK, 'Běžná práce'),
        (VIP_INTERFACE, 'VIP Interface'),
        (CALL_HANDLING, 'Call Handling'),
        (OTHER, 'Other'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='operator_actions', verbose_name='Operátor')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='Typ akce')
    start_time = models.DateTimeField(default=timezone.now, verbose_name='Čas začátku')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Čas ukončení')
    contact = models.ForeignKey(Kontakt, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Kontakt')

    class Meta:
        verbose_name = 'Akce operátora'
        verbose_name_plural = 'Akce operátorů'

    def __str__(self):
        return f'{self.user.username} - {self.get_action_type_display()} - {self.start_time.strftime("%d.%m.%Y %H:%M")}'

    @property
    def duration(self):
        if self.end_time:
            return self.end_time - self.start_time
        return None


class Vratka(models.Model):
    kontakt = models.ForeignKey(Kontakt, on_delete=models.CASCADE, related_name='vratky', verbose_name="Kontakt")
    datum_vratky = models.DateField(verbose_name="Datum vrácení")
    duvod = models.CharField(max_length=255, verbose_name="Důvod vrácení", blank=True, default='')
    datum_importu = models.DateTimeField(auto_now_add=True, verbose_name="Datum importu")
    agent = models.CharField(max_length=100, blank=True, default='', verbose_name="Agent")
    cislo_faktury = models.CharField(max_length=100, blank=True, default='', verbose_name="Číslo faktury")
    datum_faktury = models.DateField(blank=True, null=True, verbose_name="Datum faktury")
    castka_faktury = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Částka faktury")
    castka_vratky = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Částka vratky")

    class Meta:
        verbose_name = "Vratka"
        verbose_name_plural = "Vratky"
        ordering = ['-datum_vratky']

    def __str__(self):
        datum_str = self.datum_vratky.strftime('%d.%m.%Y') if self.datum_vratky else "N/A"
        return f"Vratka pro {self.kontakt} ze dne {datum_str}"