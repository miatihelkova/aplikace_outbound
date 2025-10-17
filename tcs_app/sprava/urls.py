# sprava/urls.py
from django.urls import path
from . import views

app_name = 'sprava'

urlpatterns = [
    # Hlavní stránka aplikace (přivítací)
    path('', views.sprava_dashboard, name='sprava_dashboard'),

    # --- SEKCE DATABÁZE ---
    # Přehled statistik databáze
    path('databaze/', views.sprava_databaze_overview, name='sprava_databaze_overview'),
    # Seznam všech kontaktů s filtry
    path('contacts/', views.contacts_list, name='contacts_list'),
    # Detail konkrétního kontaktu
    path('kontakt/<int:kontakt_id>/', views.kontakt_detail, name='kontakt_detail'),
    # Formulář pro nahrání CSV souboru s kontakty
    path('upload/', views.upload_contacts, name='sprava_upload_contacts'),
    # Správa vratek
    path('vratky/', views.sprava_vratek, name='sprava_vratek'),

    # --- OSTATNÍ SEKCE ---
    # Přehled reportů
    path('reporty/', views.sprava_reporty_overview, name='sprava_reporty_overview'),
    # Přehled podkladů
    path('podklady/', views.sprava_podklady_overview, name='sprava_podklady_overview'),
    # Přehled aktivit
    path('aktivity/', views.sprava_aktivity_overview, name='sprava_aktivity_overview'),
    # Přehled uživatelů  
    path('uzivatele/', views.sprava_uzivatele_overview, name='sprava_uzivatele_overview'),  
    # Formulář pro vytvoření nového uživatele
    path('uzivatele/vytvorit/', views.user_create_view, name='user_create'),
    # Formulář pro úpravu existujícího uživatele
    path('uzivatele/upravit/<int:user_id>/', views.user_edit_view, name='user_edit'),
]