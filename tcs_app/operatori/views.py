# operatori/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.db.models.functions import Right
from contacts.models import Kontakt, Historie, TypAkce
from .forms import CallOutcomeForm
from datetime import date, timedelta, datetime, time

# --- POMOCNÁ FUNKCE (beze změny) ---
def get_next_monday():
    today = timezone.now().date()
    days_until_monday = 7 - today.weekday()
    return today + timedelta(days=days_until_monday)

# --- POHLED PRO UKLÁDÁNÍ VÝSLEDKU HOVORU (OPRAVENO) ---
@login_required
@require_POST
def uloz_hovor(request, kontakt_id):
    kontakt = get_object_or_404(Kontakt, id=kontakt_id)
    operator = request.user
    form = CallOutcomeForm(request.POST, user=operator)

    if form.is_valid():
        data = form.cleaned_data
        status = data['status']
        now = timezone.now()
        
        dalsi_volani = data.get('dalsi_volani')
        if dalsi_volani:
            dalsi_volani = timezone.make_aware(dalsi_volani)

        odlozit_na = data.get('odlozit_na')
        if odlozit_na:
            odlozit_na = timezone.make_aware(odlozit_na)

        historie = Historie(
            kontakt=kontakt,
            operator=operator,
            status=status,
            poznamka=data.get('poznamka', '')
        )

        # Vaše logika ukládání (beze změny)
        if status == 'nezajem':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            kontakt.deaktivovan_do = now.date() + timedelta(days=90)
            kontakt.aktivni = False
            kontakt.assigned_operator = None
        elif status == 'nerelevance':
            historie.typ_akce = TypAkce.INTERNI_AKCE
            kontakt.deaktivovan_do = get_next_monday()
            kontakt.aktivni = False
            kontakt.assigned_operator = None
        elif status == 'neexistujici':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            kontakt.aktivni = False
            kontakt.trvale_blokovan = True
            kontakt.assigned_operator = None
        elif status == 'prodej':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            historie.hodnota_objednavky = data['hodnota_objednavky']
            kontakt.assigned_operator = operator
            kontakt.aktivni = True
        elif status == 'vip':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            historie.hodnota_objednavky = data['hodnota_objednavky']
            kontakt.vip = True
            kontakt.vip_pridano = now
            kontakt.assigned_operator = operator
            kontakt.aktivni = True
        elif status == 'nedovolano':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            if odlozit_na:
                historie.naplanovany_hovor = odlozit_na
                kontakt.assigned_operator = operator
                kontakt.aktivni = True
            else:
                kontakt.deaktivovan_do = get_next_monday()
                kontakt.aktivni = False
                kontakt.assigned_operator = None
        elif status == 'volat_pozdeji':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            kontakt.assigned_operator = operator
            kontakt.aktivni = True
        elif status == 'nemluveno':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            kontakt.deaktivovan_do = get_next_monday()
            kontakt.aktivni = False
            kontakt.assigned_operator = None
        elif status == 'predat_operatorovi':
            historie.typ_akce = TypAkce.INTERNI_AKCE
            kontakt.assigned_operator = data['jiny_operator']
            kontakt.aktivni = True
            if odlozit_na:
                historie.naplanovany_hovor = odlozit_na

        historie.save()
        kontakt.save()
        
        messages.success(request, f"Výsledek '{historie.get_status_display()}' byl úspěšně uložen.")
        return redirect('operatori:dalsi_kontakt')

    else:
        # OPRAVA ZDE: Pokud formulář není validní, musíme ho zobrazit znovu se všemi daty a chybami.
        # Místo přesměrování znovu renderujeme šablonu s původním kontaktem a nevalidním formulářem.
        messages.error(request, "Formulář obsahuje chyby. Prosím, opravte je a zkuste to znovu.")
        
        # Musíme znovu načíst veškerý kontext pro šablonu
        historie_hovoru = kontakt.historie.all().order_by('-datum_cas')
        historie_vratek = kontakt.vratky.all().order_by('-datum_vratky')
        vsechny_kampane = Kontakt.objects.values_list('tlm_kampagne_2_zielprodukt', flat=True).distinct().order_by('tlm_kampagne_2_zielprodukt')
        prednostni_cisla_qs = Kontakt.objects.annotate(last_two=Right('info_3', 2)).values_list('last_two', flat=True).distinct().order_by('last_two')
        
        context = {
            'kontakt': kontakt,
            'form': form, # Předáme nevalidní formulář, aby se zobrazily chyby
            'historie_hovoru': historie_hovoru,
            'historie_vratek': historie_vratek,
            'vsechny_kampane': [k for k in vsechny_kampane if k],
            'prednostni_cisla': [pc for pc in prednostni_cisla_qs if pc],
        }
        return render(request, 'operatori/dalsi_kontakt.html', context)

# --- POHLED PRO ZOBRAZENÍ KONKRÉTNÍHO KONTAKTU ---
@login_required
def zobraz_kontakt(request, kontakt_id):
    kontakt = get_object_or_404(Kontakt, id=kontakt_id)
    
    # Zpracování POST pro filtry (přesunuto sem, aby fungovalo na stránce s kontaktem)
    if request.method == 'POST':
        if 'set_filters' in request.POST:
            for key in list(request.session.keys()):
                if key.startswith('filter_'):
                    del request.session[key]
            
            filter_type = request.POST.get('filter_type')
            if filter_type == 'info_3':
                values = request.POST.getlist('info_3_values')
                if values: request.session['filter_info_3'] = values
            elif filter_type == 'kampan':
                value = request.POST.get('kampan_value')
                if value: request.session['filter_kampan'] = value
            elif filter_type == 'vratky':
                request.session['filter_vratky'] = 'true'
            
            return redirect('operatori:dalsi_kontakt')

        elif 'reset_filters' in request.POST:
            for key in list(request.session.keys()):
                if key.startswith('filter_'):
                    del request.session[key]
            return redirect('operatori:dalsi_kontakt')

    # Příprava kontextu pro šablonu
    form = CallOutcomeForm(user=request.user)
    historie_hovoru = kontakt.historie.all().order_by('-datum_cas')
    historie_vratek = kontakt.vratky.all().order_by('-datum_vratky')

    kontakt.ma_narozeniny_brzy = False
    if kontakt.geburtsdatum:
        today = date.today()
        narozeniny_letos = kontakt.geburtsdatum.replace(year=today.year)
        if narozeniny_letos < today:
            narozeniny_letos = narozeniny_letos.replace(year=today.year + 1)
        rozdil_dnu = (narozeniny_letos - today).days
        if 0 <= rozdil_dnu <= 14:
            kontakt.ma_narozeniny_brzy = True

    vsechny_kampane = Kontakt.objects.values_list('tlm_kampagne_2_zielprodukt', flat=True).distinct().order_by('tlm_kampagne_2_zielprodukt')
    prednostni_cisla_qs = Kontakt.objects.annotate(last_two=Right('info_3', 2)).values_list('last_two', flat=True).distinct().order_by('last_two')
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
        'historie_hovoru': historie_hovoru,
        'historie_vratek': historie_vratek,
        'vsechny_kampane': [k for k in vsechny_kampane if k],
        'prednostni_cisla': prednostni_cisla,
        'aktivni_filtry': aktivni_filtry,
        'aktivni_filtry_text': aktivni_filtry_text,
        'aktivni_filtr_typ': aktivni_filtr_typ,
    }
    return render(request, 'operatori/dalsi_kontakt.html', context)

# --- POHLED PRO NALEZENÍ DALŠÍHO KONTAKTU ---
@login_required
def dalsi_kontakt(request):
    base_queryset = Kontakt.objects.all()
    
    kampan = request.session.get('filter_kampan')
    info_3_list = request.session.get('filter_info_3')
    vratky = request.session.get('filter_vratky')

    if kampan:
        base_queryset = base_queryset.filter(tlm_kampagne_2_zielprodukt=kampan)
    elif info_3_list:
        base_queryset = base_queryset.annotate(last_two_info3=Right('info_3', 2)).filter(last_two_info3__in=info_3_list)
    elif vratky:
        base_queryset = base_queryset.filter(vratky__isnull=False).distinct()

    kontakt = base_queryset.filter(aktivni=True).first()

    if kontakt:
        return redirect('operatori:zobraz_kontakt', kontakt_id=kontakt.id)
    else:
        # OPRAVA ZDE: Pokud není nalezen kontakt, musíme do šablony poslat data pro filtry.
        messages.warning(request, "Nebyly nalezeny žádné další kontakty odpovídající filtru.")
        vsechny_kampane = Kontakt.objects.values_list('tlm_kampagne_2_zielprodukt', flat=True).distinct().order_by('tlm_kampagne_2_zielprodukt')
        prednostni_cisla_qs = Kontakt.objects.annotate(last_two=Right('info_3', 2)).values_list('last_two', flat=True).distinct().order_by('last_two')
        context = {
            'kontakt': None,
            'vsechny_kampane': [k for k in vsechny_kampane if k],
            'prednostni_cisla': [pc for pc in prednostni_cisla_qs if pc],
            'aktivni_filtry': {
                'kampan': request.session.get('filter_kampan'),
                'info_3': request.session.get('filter_info_3', []),
                'vratky': request.session.get('filter_vratky'),
            }
        }
        return render(request, 'operatori/dalsi_kontakt.html', context)

# --- OSTATNÍ POHLEDY (beze změny) ---
@login_required  
def operator_dashboard(request):  
    context = {}  
    return render(request, 'operatori/operator_dashboard.html', context)

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