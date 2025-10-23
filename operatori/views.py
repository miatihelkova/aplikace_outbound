# operatori/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F, Subquery, OuterRef, Value
from django.db.models.fields import CharField
from django.db.models.functions import Right, Cast
from contacts.models import Kontakt, Historie, TypAkce
from .forms import CallOutcomeForm
from datetime import date, timedelta, datetime, time

# --- POMOCNÁ FUNKCE (beze změny) ---
def get_next_monday():
    today = timezone.now().date()
    days_until_monday = 7 - today.weekday()
    return today + timedelta(days=days_until_monday)

# --- POHLED PRO UKLÁDÁNÍ VÝSLEDKU HOVORU (z kroku 3) ---
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

        # 1. Okamžitě uvolníme dočasný zámek kontaktu
        kontakt.locked_by = None
        kontakt.locked_at = None

        # 2. Ve výchozím stavu se po uložení operátor odebere
        kontakt.assigned_operator = None

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

        if status == 'nezajem':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            kontakt.deaktivovan_do = now.date() + timedelta(days=90)
            kontakt.aktivni = False
            kontakt.nedovolano_v_rade = 0
        elif status == 'nerelevance':
            historie.typ_akce = TypAkce.INTERNI_AKCE
            kontakt.deaktivovan_do = get_next_monday()
            kontakt.aktivni = False
            kontakt.nedovolano_v_rade = 0
        elif status == 'neexistujici':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            kontakt.aktivni = False
            kontakt.trvale_blokovan = True
            kontakt.nedovolano_v_rade = 0
        elif status == 'prodej':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            historie.hodnota_objednavky = data['hodnota_objednavky']
            kontakt.assigned_operator = operator
            kontakt.datum_posledniho_prodeje = now
            kontakt.aktivni = True
            kontakt.nedovolano_v_rade = 0
        elif status == 'vip':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            historie.hodnota_objednavky = data['hodnota_objednavky']
            kontakt.vip = True
            kontakt.vip_pridano = now
            kontakt.assigned_operator = operator
            kontakt.aktivni = True
            kontakt.nedovolano_v_rade = 0
        elif status == 'nedovolano':
            historie.typ_akce = TypAkce.NESPOJENY_HOVOR
            kontakt.nedovolano_v_rade += 1
            if kontakt.nedovolano_v_rade >= 7:
                kontakt.aktivni = False

            if odlozit_na:
                historie.naplanovany_hovor = odlozit_na
                kontakt.assigned_operator = operator
                kontakt.aktivni = True
            elif not kontakt.aktivni:
                pass
            else:
                kontakt.deaktivovan_do = get_next_monday()
                kontakt.aktivni = False
        elif status == 'volat_pozdeji':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            historie.naplanovany_hovor = dalsi_volani
            kontakt.assigned_operator = operator
            kontakt.aktivni = True
            kontakt.nedovolano_v_rade = 0
        elif status == 'nemluveno':
            historie.typ_akce = TypAkce.SPOJENY_HOVOR
            kontakt.deaktivovan_do = get_next_monday()
            kontakt.aktivni = False
            kontakt.nedovolano_v_rade = 0
        elif status == 'predat_operatorovi':
            historie.typ_akce = TypAkce.INTERNI_AKCE
            kontakt.assigned_operator = data['jiny_operator']
            kontakt.aktivni = True
            if odlozit_na:
                historie.naplanovany_hovor = odlozit_na
            kontakt.nedovolano_v_rade = 0

        historie.save()
        kontakt.save()
        
        messages.success(request, f"Výsledek '{historie.get_status_display()}' byl úspěšně uložen.")
        return redirect('operatori:dalsi_kontakt')

    else:
        messages.error(request, "Formulář obsahuje chyby. Prosím, opravte je a zkuste to znovu.")
        
        historie_hovoru = kontakt.historie.all().order_by('-datum_cas')
        historie_vratek = kontakt.vratky.all().order_by('-datum_vratky')
        vsechny_kampane = Kontakt.objects.values_list('tlm_kampagne_2_zielprodukt', flat=True).distinct().order_by('tlm_kampagne_2_zielprodukt')
        prednostni_cisla_qs = Kontakt.objects.annotate(last_two=Right('info_3', 2)).values_list('last_two', flat=True).distinct().order_by('last_two')
        
        context = {
            'kontakt': kontakt,
            'form': form,
            'historie_hovoru': historie_hovoru,
            'historie_vratek': historie_vratek,
            'vsechny_kampane': [k for k in vsechny_kampane if k],
            'prednostni_cisla': [pc for pc in prednostni_cisla_qs if pc],
        }
        return render(request, 'operatori/dalsi_kontakt.html', context)

# --- POHLED PRO ZOBRAZENÍ KONKRÉTNÍHO KONTAKTU (beze změny) ---
@login_required
def zobraz_kontakt(request, kontakt_id):
    kontakt = get_object_or_404(Kontakt, id=kontakt_id)
    
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

# --- POHLED PRO NALEZENÍ DALŠÍHO KONTAKTU (KOMPLETNĚ PŘEPSÁNO) ---
@login_required
def dalsi_kontakt(request):
    operator = request.user
    now = timezone.now()
    lock_timeout = now - timedelta(minutes=60)
    kontakt = None

    # Uvolníme všechny zámky starší než 60 minut
    Kontakt.objects.filter(locked_at__lt=lock_timeout).update(locked_by=None, locked_at=None)
    # Uvolníme zámek, který mohl zůstat aktuálnímu operátorovi z minula
    Kontakt.objects.filter(locked_by=operator).update(locked_by=None, locked_at=None)

    # Subquery pro nalezení posledního naplánovaného hovoru
    latest_scheduled_call_subquery = Historie.objects.filter(
        kontakt=OuterRef('pk'),
        naplanovany_hovor__isnull=False
    ).order_by('-naplanovany_hovor').values('naplanovany_hovor')[:1]

    # Subquery pro nalezení data posledního hovoru
    latest_history_date_subquery = Historie.objects.filter(
        kontakt=OuterRef('pk')
    ).order_by('-datum_cas').values('datum_cas')[:1]

    # --- Priorita 1: Odložené kontakty ---
    # Hledáme kontakty přiřazené operátorovi, jejichž poslední naplánovaný hovor už měl proběhnout
    p1_queryset = Kontakt.objects.annotate(
        latest_scheduled_call=Subquery(latest_scheduled_call_subquery)
    ).filter(
        assigned_operator=operator,
        latest_scheduled_call__lte=now
    ).order_by('latest_scheduled_call')

    with transaction.atomic():
        kontakt = p1_queryset.select_for_update(skip_locked=True).first()

    # --- Priorita 2: VIP kontakty ---
    if not kontakt:
        # Hledáme VIP kontakty přiřazené operátorovi, které nemají naplánovaný žádný budoucí hovor
        p2_queryset = Kontakt.objects.annotate(
            latest_history_date=Subquery(latest_history_date_subquery)
        ).filter(
            vip=True,
            assigned_operator=operator
        ).exclude(
            historie__naplanovany_hovor__gt=now
        ).order_by('latest_history_date') # Nejstarší poslední hovor první

        with transaction.atomic():
            kontakt = p2_queryset.select_for_update(skip_locked=True).first()

    # --- Priorita 3: Běžné kontakty ---
    if not kontakt:
        # Získáme seznam všech dat importu, seřazený od nejnovějšího
        import_dates = Kontakt.objects.filter(
            aktivni=True, datum_importu__isnull=False
        ).values_list('datum_importu', flat=True).distinct().order_by('-datum_importu')

        # Procházíme data importu od nejnovějšího
        for import_date in import_dates:
            # Základní sada kontaktů pro tento import
            base_p3_queryset = Kontakt.objects.filter(
                aktivni=True,
                trvale_blokovan=False,
                datum_importu=import_date,
                assigned_operator__isnull=True
            ).exclude(
                historie__naplanovany_hovor__gt=now
            ).annotate(
                dbk_int=Cast(
                    # Nahradíme čárku tečkou pro správné přetypování a ošetříme prázdné hodnoty
                    F('info_1'), 
                    output_field=CharField()
                )
            )

            # Aplikace filtrů ze session
            kampan = request.session.get('filter_kampan')
            info_3_list = request.session.get('filter_info_3')
            vratky = request.session.get('filter_vratky')

            if kampan:
                base_p3_queryset = base_p3_queryset.filter(tlm_kampagne_2_zielprodukt=kampan)
            elif info_3_list:
                base_p3_queryset = base_p3_queryset.annotate(last_two_info3=Right('info_3', 2)).filter(last_two_info3__in=info_3_list)
            elif vratky:
                base_p3_queryset = base_p3_queryset.filter(vratky__isnull=False).distinct()

            # Řazení podle DBK (info_1) - sestupně, NULL na konci
            # Poznámka: Přetypování na číslo je složité, pokud DBK obsahuje i text.
            # Prozatím řadíme jako text. Pro přesné číselné řazení by bylo potřeba vyčistit data.
            ordered_p3_queryset = base_p3_queryset.order_by(F('dbk_int').desc(nulls_last=True))

            # Pokusíme se najít kontakt v každé pod-prioritě
            queries_to_try = [
                # 3a: Bez historie hovorů
                ordered_p3_queryset.filter(historie__isnull=True),
                # 3b: S prodejem v historii
                ordered_p3_queryset.filter(historie__status='prodej').distinct(),
                # 3c: Poslední 3 hovory nejsou "nedovoláno" - zjednodušená logika
                # Vyloučíme ty, co mají 3 a více nedovoláno v řadě
                ordered_p3_queryset.filter(nedovolano_v_rade__lt=3),
                # 3d: Ostatní (celá sada, protože předchozí dotazy jsou podmnožiny)
                ordered_p3_queryset
            ]

            for queryset in queries_to_try:
                with transaction.atomic():
                    kontakt = queryset.select_for_update(skip_locked=True).first()
                    if kontakt:
                        break  # Našli jsme kontakt, vyskočíme z cyklu dotazů
            
            if kontakt:
                break # Našli jsme kontakt, vyskočíme z cyklu importů

    # Pokud jsme našli jakýkoliv volný kontakt (z P1, P2 nebo P3), zamkneme ho
    if kontakt:
        kontakt.locked_by = operator
        kontakt.locked_at = now
        kontakt.save(update_fields=['locked_by', 'locked_at'])
        return redirect('operatori:zobraz_kontakt', kontakt_id=kontakt.id)
    else:
        # Pokud není nalezen žádný kontakt, zobrazíme stránku s filtry
        messages.warning(request, "Nebyly nalezeny žádné další dostupné kontakty.")
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