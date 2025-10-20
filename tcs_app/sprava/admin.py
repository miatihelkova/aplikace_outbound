# sprava/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from simple_history.admin import SimpleHistoryAdmin 

class CustomUserAdmin(SimpleHistoryAdmin): 
    fieldsets = UserAdmin.fieldsets + (
        ('Další informace', {
            'fields': ('kod_operatora', 'telefonni_cislo', 'uvazek_hodiny', 'datum_narozeni', 'svatek'),
        }),
    )
    

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Další informace', {
            'fields': ('first_name', 'last_name', 'email', 'kod_operatora', 'telefonni_cislo', 'uvazek_hodiny', 'datum_narozeni', 'svatek'),
        }),
    )
    
    # Zobrazení sloupců v seznamu uživatelů
    list_display = ('username', 'first_name', 'last_name', 'kod_operatora', 'is_staff')
    
    # Možnost vyhledávání
    search_fields = ('username', 'first_name', 'last_name', 'kod_operatora')

admin.site.register(CustomUser, CustomUserAdmin)