from django.contrib import admin
from .models import Kontakt, Korespondence, DopisovaSablona, UserDopisovaSablona, ProduktovaNabidka, OperatorAction, Vratka, Historie

# Inline modely pro zobrazení přímo v detailu Kontaktu
class HistorieInline(admin.TabularInline):
    model = Historie
    extra = 0  # Nezobrazovat prázdné řádky pro přidání
    readonly_fields = ('operator', 'datum_cas', 'poznamka') # Všechny pole jen pro čtení
    can_delete = False # Nelze mazat historii z detailu kontaktu
    verbose_name_plural = "Historie volání"

class VratkaInline(admin.TabularInline):
    model = Vratka
    extra = 0
    readonly_fields = ('datum_vratky', 'duvod', 'castka_vratky')
    can_delete = False
    verbose_name_plural = "Vratky"

# Registrace modelu Kontakt s vylepšeným zobrazením
@admin.register(Kontakt)
class KontaktAdmin(admin.ModelAdmin):
    list_display = ("id", "vorname", "nachname", "telefon1", "info_2", "recency", "vip", "aktivni", "assigned_operator")
    search_fields = ("vorname", "nachname", "telefon1", "info_2")
    list_filter = ("vip", "aktivni", "recency", "assigned_operator")
    raw_id_fields = ("assigned_operator",)
    readonly_fields = ("updated_at", "vip_pridano")

    # Uspořádání polí do sekcí pro lepší přehlednost
    fieldsets = (
        ('Základní identifikace', {
            'fields': ('info_2', 'info_3', 'info_1', 'dlbs')
        }),
        ('Osobní údaje', {
            'fields': ('ansprache', 'titel', 'vorname', 'nachname', 'geburtsdatum')
        }),
        ('Kontaktní údaje', {
            'fields': ('telefon1', 'telefon2', 'strasse', 'ort', 'plz')
        }),
        ('Stav a klasifikace', {
            'fields': ('aktivni', 'trvale_blokovan', 'blokace_do', 'recency', 'assigned_operator', 'tlm_kampagne_2_zielprodukt')
        }),
        ('VIP Status', {
            'fields': ('vip', 'vip_pridano', 'vip_poznamka')
        }),
        ('Interní počítadla (pouze pro čtení)', {
            'classes': ('collapse',), # Sekce bude ve výchozím stavu sbalená
            'fields': ('nedovolano_pocet', 'odlozeny_nedovolano_pokusy', 'updated_at'),
        }),
    )

    # Přidání inline modelů do detailu Kontaktu
    inlines = [HistorieInline, VratkaInline]

# Registrace modelu Historie pro samostatné zobrazení
@admin.register(Historie)
class HistorieAdmin(admin.ModelAdmin):
    list_display = ('kontakt', 'operator', 'datum_cas')
    list_filter = ('operator',)
    search_fields = ('kontakt__vorname', 'kontakt__nachname', 'poznamka')
    autocomplete_fields = ['kontakt', 'operator'] # Lepší výběr kontaktu a operátora


# Registrace ostatních modelů (bez speciálních úprav)
admin.site.register(Korespondence)
admin.site.register(DopisovaSablona)
admin.site.register(UserDopisovaSablona)
admin.site.register(ProduktovaNabidka)
admin.site.register(OperatorAction)
admin.site.register(Vratka)