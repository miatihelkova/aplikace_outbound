from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    # Toto rozšíří formulář pro editaci existujícího uživatele
    fieldsets = UserAdmin.fieldsets + (
        ('Další informace', {
            'fields': ('kod_operatora', 'telefonni_cislo', 'uvazek_hodiny', 'datum_narozeni', 'svatek'),
        }),
    )
    
    # Toto rozšíří formulář pro vytváření nového uživatele
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Další informace', {
            'fields': ('first_name', 'last_name', 'email', 'kod_operatora', 'telefonni_cislo', 'uvazek_hodiny', 'datum_narozeni', 'svatek'),
        }),
    )
    
    # Toto přidá sloupce do seznamu všech uživatelů v administraci
    list_display = ('username', 'first_name', 'last_name', 'kod_operatora', 'is_staff')
    
    # Přidá možnost vyhledávání
    search_fields = ('username', 'first_name', 'last_name', 'kod_operatora')

# Zaregistrujeme náš model s naší novou admin třídou
admin.site.register(CustomUser, CustomUserAdmin)