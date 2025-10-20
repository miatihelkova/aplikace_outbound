# operatori/urls.py

from django.urls import path
from . import views

app_name = 'operatori'  # Tímto oficiálně říkáme, že jmenný prostor je 'operatori'

urlpatterns = [
    # ZDE JE OPRAVA: Přidáváme name="operator_dashboard"
    path("", views.operator_dashboard, name="operator_dashboard"),
    
    # A rovnou přidáme i ostatní URL, které budeme potřebovat
    path("kontakty/", views.dalsi_kontakt, name="dalsi_kontakt"),
    path("ukoly/", views.ukoly, name="ukoly"),
    path("vip-kontakty/", views.vip_kontakty, name="vip_kontakty"),
    path("prodeje/", views.prodeje, name="prodeje"),
]