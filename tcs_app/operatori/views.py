# operatori/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Subquery, OuterRef, Exists, F
from django.db.models.functions import Right
from contacts.models import Kontakt, Historie
from .forms import HistorieForm

@login_required  
def operator_dashboard(request):  
    context = {}  
    return render(request, 'operatori/operator_dashboard.html', context)

@login_required
def dalsi_kontakt(request):
    operator = request.user
    now = timezone.now()
    kontakt = None
    form = HistorieForm()

    if request.method == 'POST':
        if 'save_call' in request.POST:
            form = HistorieForm(request.POST)
            if form.is_valid():
                kontakt_id = request.POST.get('kontakt_id')
                try:
                    kontakt_k_ulozeni = Kontakt.objects.get(id=kontakt_id)
                    novy_zaznam = form.save(commit=False)
                    novy_zaznam.operator = operator
                    novy_zaznam.kontakt = kontakt_k_ulozeni
                    novy_zaznam.save()
                    return redirect('operatori:dalsi_kontakt')
                except Kontakt.DoesNotExist:
                    pass

        elif 'set_filters' in request.POST:
            for key in list(request.session.keys()):
                if key.startswith('filter_'):
                    del request.session[key]
            
            filter_type = request.POST.get('filter_type')
            
            if filter_type == 'info_3':
                values = request.POST.getlist('info_3_values')
                if values:
                    request.session['filter_info_3'] = values
            elif filter_type == 'kampan':
                value = request.POST.get('kampan_value')
                if value:
                    request.session['filter_kampan'] = value
            # ZMĚNA: Logika pro vratky je nyní jednodušší
            elif filter_type == 'vratky':
                # Filtr se aktivuje pouhým výběrem radio buttonu.
                # Uložíme si jednoduchou hodnotu 'true' jako potvrzení.
                request.session['filter_vratky'] = 'true'
            
            return redirect('operatori:dalsi_kontakt')

        elif 'reset_filters' in request.POST:
            for key in list(request.session.keys()):
                if key.startswith('filter_'):
                    del request.session[key]
            return redirect('operatori:dalsi_kontakt')

        elif 'get_next' in request.POST:
            base_queryset = Kontakt.objects.all()
            
            kampan = request.session.get('filter_kampan')
            info_3_list = request.session.get('filter_info_3')
            vratky = request.session.get('filter_vratky')

            if kampan:
                base_queryset = base_queryset.filter(tlm_kampagne_2_zielprodukt=kampan)
            elif info_3_list:
                base_queryset = base_queryset.annotate(
                    last_two_info3=Right('info_3', 2)
                ).filter(last_two_info3__in=info_3_list)
            elif vratky:
                base_queryset = base_queryset.filter(vratky__isnull=False).distinct()

            # --- ZDE PATŘÍ VAŠE PLNÁ LOGIKA VÝBĚRU KONTAKTU (PRIORITY 1, 2, 3) ---
            kontakt = base_queryset.filter(aktivni=True).first()

    # --- PŘÍPRAVA KONTEXTU (beze změny) ---
    vsechny_kampane = Kontakt.objects.values_list('tlm_kampagne_2_zielprodukt', flat=True).distinct().order_by('tlm_kampagne_2_zielprodukt')
    
    prednostni_cisla_qs = Kontakt.objects.annotate(
        last_two=Right('info_3', 2)
    ).values_list('last_two', flat=True).distinct().order_by('last_two')
    prednostni_cisla = [pc for pc in prednostni_cisla_qs if pc]

    aktivni_filtry_text = ""
    aktivni_filtr_typ = ""
    
    aktivni_filtry = {
        'kampan': request.session.get('filter_kampan'),
        'info_3': request.session.get('filter_info_3', []),
        'vratky': request.session.get('filter_vratky'),
    }

    if aktivni_filtry['info_3']:
        aktivni_filtry_text = f"Přednostní čísla: {', '.join(aktivni_filtry['info_3'])}"
        aktivni_filtr_typ = "info_3"
    elif aktivni_filtry['vratky']:
        aktivni_filtry_text = "Pouze vratky"
        aktivni_filtr_typ = "vratky"
    elif aktivni_filtry['kampan']:
        aktivni_filtry_text = f"Kampaň: {aktivni_filtry['kampan']}"
        aktivni_filtr_typ = "kampan"

    context = {
        'kontakt': kontakt,
        'form': form,
        'vsechny_kampane': [k for k in vsechny_kampane if k],
        'prednostni_cisla': prednostni_cisla,
        'aktivni_filtry': aktivni_filtry,
        'aktivni_filtry_text': aktivni_filtry_text,
        'aktivni_filtr_typ': aktivni_filtr_typ,
    }
    return render(request, 'operatori/dalsi_kontakt.html', context)

# ... zbytek souboru (ukoly, vip_kontakty, prodeje) ...
@login_required
def ukoly(request):
    context = {}
    return render(request, 'operatori/ukoly.html', context)

@login_required
def vip_kontakty(request):
    context = {}
    return render(request, 'operatori/vip_kontakty.html', context)

@login_required  
def prodeje(request):  
    context = {}  
    return render(request, 'operatori/prodeje.html', context)