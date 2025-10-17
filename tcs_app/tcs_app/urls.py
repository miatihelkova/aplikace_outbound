from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout # <-- PŘIDÁNO

@login_required
def home_redirect(request):
    # ADMIN (správce) → používáme is_staff
    if request.user.is_staff:
        return redirect("sprava:sprava_dashboard")
    # Jinak OPERÁTOR
    return redirect("operatori_dashboard")

# NOVÁ FUNKCE PRO ODHLÁŠENÍ
def custom_logout_view(request):
    logout(request)
    return redirect('login')

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sprava/", include("sprava.urls")),
    path("operatori/", include("operatori.urls")),
    path("", home_redirect, name="home"),
    
    # Používáme upravenou cestu k šabloně
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    
    # ZMĚNA ZDE: Použijeme naši novou, spolehlivou funkci
    path("logout/", custom_logout_view, name="logout"),
]