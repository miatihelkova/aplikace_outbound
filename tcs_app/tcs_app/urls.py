# tcs_app/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout

@login_required
def home_redirect(request):
    # ADMIN (správce) → používáme is_staff
    if request.user.is_staff:
        return redirect("sprava:sprava_dashboard")
    
    # Jinak OPERÁTOR - ZDE JE OPRAVA PŘEKLEPU
    return redirect("operatori:operator_dashboard")

def custom_logout_view(request):
    logout(request)
    return redirect('login')

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # ZDE JE OPRAVA - přidáváme namespace i pro sprava
    path("sprava/", include(("sprava.urls", "sprava"), namespace="sprava")),
    path("operatori/", include(("operatori.urls", "operatori"), namespace="operatori")),
    
    path("", home_redirect, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", custom_logout_view, name="logout"),
]