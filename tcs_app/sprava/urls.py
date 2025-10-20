# sprava/urls.py
from django.urls import path
from . import views

app_name = 'sprava'

urlpatterns = [
    # Hlavní stránka aplikace 
    path('', views.sprava_dashboard, name='sprava_dashboard'),

    # --- SEKCE DATABÁZE ---  
    path('databaze/', views.sprava_databaze_overview, name='databaze_overview'),  
    path('contacts/', views.contacts_list, name='contacts_list'),  
    path('kontakt/<int:kontakt_id>/', views.kontakt_detail, name='kontakt_detail'),  
    path('upload/', views.upload_contacts, name='upload_contacts'),  
    path('vratky/', views.sprava_vratek, name='vratky'),  
  
    # --- OSTATNÍ SEKCE ---  
    path('reporty/', views.sprava_reporty_overview, name='reporty_overview'),  
    path('podklady/', views.sprava_podklady_overview, name='podklady_overview'),  
    path('aktivity/', views.sprava_aktivity_overview, name='aktivity_overview'),  
      
    # --- SPRÁVA UŽIVATELŮ ---  
    path('uzivatele/', views.sprava_uzivatele_overview, name='sprava_uzivatele_overview'),    
    path('uzivatele/vytvorit/', views.user_create_view, name='user_create'),  
    path('uzivatele/upravit/<int:user_id>/', views.user_edit_view, name='user_edit'),  
    path('uzivatele/smazat/<int:user_id>/', views.user_delete_view, name='user_delete'),  
]