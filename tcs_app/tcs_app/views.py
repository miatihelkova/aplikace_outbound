from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse

def custom_login_view(request):
    # Pokud je uživatel již přihlášen, rovnou ho přesměrujeme
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect(reverse('sprava:sprava_dashboard')) # Název URL pro admin dashboard
        else:
            return redirect(reverse('operatori:operator_dashboard')) # Název URL pro operátor dashboard

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Zde je klíčová logika přesměrování po úspěšném přihlášení
            if user.is_staff:
                return redirect(reverse('sprava:sprava_dashboard'))
            else:
                return redirect(reverse('operatori:operator_dashboard'))
    else:
        form = AuthenticationForm()

    # Pro GET požadavek (první zobrazení stránky) použijeme vaši šablonu
    return render(request, 'registration/login.html', {'form': form})