from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def home_redirect(request):
    # ADMIN (správce) → používáme is_staff
    if request.user.is_staff:
        return redirect("sprava_dashboard")
    # Jinak OPERÁTOR
    return redirect("operatori_dashboard")

from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sprava/", include("sprava.urls")),
    path("operatori/", include("operatori.urls")),
    path("", home_redirect, name="home"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]