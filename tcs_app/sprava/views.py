from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django import forms
from io import TextIOWrapper
import csv
from datetime import datetime
import re

# Upravený import modelů - přibyl model Historie
from contacts.models import Kontakt, Historie
from django.db.models import Count, Max, Q
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from datetime import date, timedelta

from .forms import KontaktEditForm


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV soubor")


def dashboard(request):
    return HttpResponse(
        '<h1>Správa – funguje</h1>'
        '<ul>'
        '<li><a href="/sprava/upload-contacts/">Nahrát kontakty (CSV)</a></li>'
        '<li><a href="/sprava/contacts-list/">Zobrazit seznam kontaktů</a></li>'
        '<li><a href="/sprava/returns/import/">Nahrát vratky (CSV/XLSX)</a></li>'
        '</ul>'
    )


def is_admin(user):
    return user.is_authenticated and user.is_staff


# Normalizace dat
def norm_phone(s: str) -> str:
    """
    Ponechá '+' a číslice, odstraní mezery, pomlčky, závorky apod.
    """
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"[^\d+]", "", s)
    return s


def norm_text(s: str) -> str:
    return s.strip() if isinstance(s, str) else s


@login_required
@user_passes_test(is_admin)
def upload_contacts(request):
    def fix_chars(text):
        if not isinstance(text, str):
            return text
        char_map = {
            'Å': 'Č', 'å': 'č', '²': 'ď', 'Þ': 'Ř', 'þ': 'ř', '¯': 'Š', 'æ': 'š',
            'ù': 'ť', '}': 'ü', 'è': 'ů', '½': 'Ž', '¶': 'ž', '\xa0': 'ě',
            '»': 'ň', '¦': 'ö',
        }
        for wrong, correct in char_map.items():
            text = text.replace(wrong, correct)
        return text

    if request.method == "POST":
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            # Používáme 'replace' místo 'ignore' pro lepší diagnostiku chyb kódování
            decoded_file = TextIOWrapper(csv_file, encoding="utf-8", errors='replace')
            reader = csv.DictReader(decoded_file)
            
            # Načteme celé CSV do paměti pro efektivnější zpracování
            try:
                rows = list(reader)
            except csv.Error as e:
                messages.error(request, f"Chyba při čtení CSV souboru: {e}")
                return redirect("sprava:sprava_upload_contacts")

            created_count = 0
            updated_count = 0
            skipped_duplicates = 0
            
            # --- OPTIMALIZACE: Načtení dat předem ---
            # 1. Získáme všechny unikátní klíče (info_2 a telefon1) z CSV
            all_info_2 = {norm_text(r.get("info_2", "")) for r in rows if r.get("info_2")}
            all_telefon1 = {norm_phone(r.get("Telefon1", "")) for r in rows if r.get("Telefon1")}

            # 2. Načteme všechny relevantní existující kontakty z DB pomocí dvou dotazů
            existing_by_info_2 = {k.info_2: k for k in Kontakt.objects.filter(info_2__in=all_info_2)}
            existing_by_telefon1 = {k.telefon1: k for k in Kontakt.objects.filter(telefon1__in=all_telefon1)}
            
            contacts_to_create = []
            seen_keys = set()

            with transaction.atomic():
                for raw_row in rows:
                    row = {k: fix_chars(v) for k, v in raw_row.items()}

                    telefon1 = norm_phone(row.get("Telefon1") or "")
                    info_2 = norm_text(row.get("info_2") or "")

                    # Deduplikace v rámci jednoho CSV
                    key = (telefon1 or "", info_2 or "")
                    if not any(key) or key in seen_keys:
                        if any(key):
                            skipped_duplicates += 1
                        continue
                    seen_keys.add(key)

                    # Najdi existující kontakt – teď už jen v paměti (slovnících)
                    existing_kontakt = None
                    if info_2:
                        existing_kontakt = existing_by_info_2.get(info_2)
                    if not existing_kontakt and telefon1:
                        existing_kontakt = existing_by_telefon1.get(telefon1)

                    if existing_kontakt:
                        # Aktualizace
                        new_info3 = norm_text(row.get("info_3") or "")
                        if existing_kontakt.info_3 != new_info3:
                            existing_kontakt.info_3 = new_info3
                            existing_kontakt.save(update_fields=["info_3"])
                            updated_count += 1
                    else:
                        # Příprava pro vytvoření nového kontaktu
                        datum_str = norm_text(row.get("Geburtsdatum") or "")
                        geburtsdatum = None
                        if datum_str:
                            try:
                                geburtsdatum = datetime.strptime(datum_str, "%d-%m-%Y").date()
                            except ValueError:
                                geburtsdatum = None
                        
                        # Přidáme nový kontakt do seznamu pro hromadné vytvoření
                        contacts_to_create.append(Kontakt(
                            info_2=info_2,
                            info_3=norm_text(row.get("info_3") or ""),
                            ansprache=norm_text(row.get("Ansprache") or ""),
                            titel=norm_text(row.get("Titel") or ""),
                            vorname=norm_text(row.get("Vorname") or ""),
                            nachname=norm_text(row.get("Nachname") or ""),
                            dlbs=norm_text(row.get("dlbs") or ""),
                            info_1=norm_text(row.get("info_1") or ""),
                            telefon1=telefon1,
                            telefon2=norm_phone(row.get("Telefon2") or ""),
                            geburtsdatum=geburtsdatum,
                            datum_letztkontakt=norm_text(row.get("Datum Letztkontakt") or ""),
                            tlm_kampagne_2_zielprodukt=norm_text(row.get("TLM-Kampagne 2 - Zielprodukt") or ""),
                            strasse=norm_text(row.get("Strasse") or ""),
                            ort=norm_text(row.get("Ort") or ""),
                            plz=norm_text(row.get("Plz") or ""),
                            recency=norm_text(row.get("Recency") or ""),
                            vip=False,
                            aktivni=True,
                        ))

                # Hromadné vytvoření všech nových kontaktů jedním dotazem
                if contacts_to_create:
                    # ignore_conflicts=True přeskočí vkládání řádků, které by porušily unique omezení
                    # (např. pokud by dva řádky v CSV měly stejné info_2, ale my to neodchytili)
                    # POZN: Pro plnou podporu je vyžadována databáze PostgreSQL.
                    Kontakt.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
                    created_count = len(contacts_to_create)

            messages.success(request, f"Import dokončen! Vytvořeno: {created_count} kontaktů, Aktualizováno: {updated_count} kontaktů.")
            if skipped_duplicates:
                messages.info(request, f"Přeskočeno duplicit v CSV: {skipped_duplicates}")
            return redirect("sprava:sprava_upload_contacts")
    else:
        form = CSVImportForm()

    return render(request, "sprava/upload_contacts.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def contacts_list(request):
    # Získáme všechny parametry z URL adresy
    query = request.GET.get('q', '').strip()
    filter_operator_id = request.GET.get('operator')
    filter_aktivni = request.GET.get('aktivni')
    filter_history = request.GET.get('history')
    filter_last_call_from = request.GET.get('last_call_from')
    filter_last_call_to = request.GET.get('last_call_to')
    # Nový sjednocený parametr pro typ zákazníka
    filter_customer_type = request.GET.get('customer_type')

    # Základní QuerySet
    qs = (
        Kontakt.objects
        .select_related('assigned_operator')
        .annotate(
            call_count=Count('historie', distinct=True),
            last_call=Max('historie__datum_cas'),
        )
        .order_by('-id')
    )

    # --- APLIKACE FILTRŮ ---

    if query:
        qs = qs.filter(
            Q(vorname__icontains=query) | Q(nachname__icontains=query) |
            Q(info_2__icontains=query) | Q(telefon1__icontains=query)
        )
    if filter_operator_id:
        qs = qs.filter(assigned_operator_id=filter_operator_id)
    
    # Nová logika pro sjednocený filtr "Typ zákazníka"
    if filter_customer_type == 'vip':
        qs = qs.filter(vip=True)
    elif filter_customer_type:
        qs = qs.filter(recency=filter_customer_type)

    if filter_aktivni == 'true':
        qs = qs.filter(aktivni=True)
    elif filter_aktivni == 'false':
        qs = qs.filter(aktivni=False)
    if filter_history == 'yes':
        qs = qs.filter(call_count__gt=0)
    elif filter_history == 'no':
        qs = qs.filter(call_count=0)
    try:
        if filter_last_call_from:
            date_from = datetime.strptime(filter_last_call_from, '%Y-%m-%d').date()
            qs = qs.filter(last_call__date__gte=date_from)
        if filter_last_call_to:
            date_to = datetime.strptime(filter_last_call_to, '%Y-%m-%d').date()
            qs = qs.filter(last_call__date__lte=date_to)
    except (ValueError, TypeError):
        pass

    # --- PŘÍPRAVA DAT PRO ŠABLONU ---
    operators = User.objects.filter(is_staff=True).order_by('username')
    
    # Vytvoříme seznam pro nový sjednocený filtr
    recency_options = list(Kontakt.objects.exclude(recency__isnull=True).exclude(recency__exact='').values_list('recency', flat=True).distinct().order_by('recency'))
    customer_type_options = ['vip'] + recency_options # Přidáme 'vip' na začátek

    paginator = Paginator(qs, 50)
    page = request.GET.get("page")
    contacts = paginator.get_page(page)
    
    context = {
        "contacts": contacts,
        "operators": operators,
        "customer_type_options": customer_type_options,
    }
    return render(request, "sprava/contacts_list.html", context)

@login_required
@user_passes_test(is_admin)
def kontakt_detail(request, kontakt_id):
    kontakt = get_object_or_404(Kontakt, pk=kontakt_id)
    historie = Historie.objects.filter(kontakt=kontakt).select_related('operator').order_by('-datum_cas')

    if request.method == 'POST':
        form = KontaktEditForm(request.POST, instance=kontakt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Údaje o kontaktu byly úspěšně aktualizovány.')
            return redirect('sprava:kontakt_detail', kontakt_id=kontakt.id)
    else:
        form = KontaktEditForm(instance=kontakt)

    context = {
        'kontakt': kontakt,
        'historie': historie,
        'form': form,
    }
    return render(request, 'sprava/kontakt_detail.html', context)