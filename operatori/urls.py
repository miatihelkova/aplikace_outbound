# operatori/urls.py
from django.urls import path
from . import views

app_name = 'operatori'

urlpatterns = [
    # PŘIDÁNO: Tento řádek nastaví, že adresa /operatori/ rovnou spustí hledání dalšího kontaktu.
    path('', views.dalsi_kontakt, name='index'),

    path('dashboard/', views.operator_dashboard, name='operator_dashboard'),
    
    # Tato URL slouží jako "hledač". Najde kontakt a přesměruje.
    path('dalsi_kontakt/', views.dalsi_kontakt, name='dalsi_kontakt'),
    
    # Tato URL zobrazí konkrétní kontakt. Umožní obnovení stránky (F5).
    path('kontakt/<int:kontakt_id>/', views.zobraz_kontakt, name='zobraz_kontakt'),
    
    # Tato URL zpracuje uložení výsledku pro konkrétní kontakt.
    path('uloz_hovor/<int:kontakt_id>/', views.uloz_hovor, name='uloz_hovor'),
    
    path('ukoly/', views.ukoly, name='ukoly'),
    path('vip-kontakty/', views.vip_kontakty, name='vip_kontakty'),
    path('prodeje/', views.prodeje, name='prodeje'),
]