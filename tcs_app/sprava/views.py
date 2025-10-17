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
from contacts.models import Kontakt, Historie, Vratka
from django.db.models import Count, Max, Q
from django.core.paginator import Paginator
from .models import CustomUser
from datetime import date, timedelta

from .forms import KontaktEditForm

from django.utils import timezone
from decimal import Decimal
import pandas as pd
import traceback

from .forms import KontaktEditForm, VratkaForm, UserCreationForm, UserEditForm

class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV soubor")


# =============================================================================
# POMOCNÉ FUNKCE
# =============================================================================

def is_admin(user):
    return user.is_authenticated and user.is_staff

def norm_phone(s: str) -> str:
    if not s: return ""
    return re.sub(r"[^\d+]", "", s.strip())

def norm_text(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

# =============================================================================
# HLAVNÍ STRÁNKA (DASHBOARD)
# =============================================================================

@login_required
@user_passes_test(is_admin)
def sprava_dashboard(request):
    """
    Zobrazí hlavní uvítací stránku (dashboard).
    """
    context = {'page_title': 'Hlavní přehled'}
    return render(request, 'sprava/sprava_dashboard.html', context)

# =============================================================================
# SEKCE: DATABÁZE
# =============================================================================

@login_required
@user_passes_test(is_admin)
def sprava_databaze_overview(request):
    """
    Zobrazí přehled (overview) pro sekci Databáze s klíčovými statistikami.
    """
    all_contacts = Kontakt.objects.all()
    total_contacts = all_contacts.count()
    active_contacts = all_contacts.filter(aktivni=True).count()
    inactive_contacts = total_contacts - active_contacts
    vip_contacts = all_contacts.filter(vip=True).count()
    active_without_history = Kontakt.objects.annotate(call_count=Count('historie')).filter(aktivni=True, call_count=0).count()
    last_return_import = Vratka.objects.order_by('-datum_importu').first()
    last_contact_import = Kontakt.objects.order_by('-id').first()

    context = {
        'page_title': 'Přehled databáze',
        'total_contacts': total_contacts,
        'active_contacts': active_contacts,
        'inactive_contacts': inactive_contacts,
        'vip_contacts': vip_contacts,
        'active_without_history': active_without_history,
        'last_return_import_date': last_return_import.datum_importu if last_return_import else None,
        'last_contact_import_date': last_contact_import.updated_at if last_contact_import else None,
    }
    return render(request, 'sprava/sprava_databaze_overview.html', context)

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
            decoded_file = TextIOWrapper(csv_file, encoding="utf-8", errors='replace')
            reader = csv.DictReader(decoded_file)
            
            try:
                rows = list(reader)
            except csv.Error as e:
                messages.error(request, f"Chyba při čtení CSV souboru: {e}")
                return redirect("sprava:sprava_upload_contacts")

            created_count = 0
            updated_count = 0
            skipped_duplicates = 0
            
            all_info_2 = {norm_text(r.get("info_2", "")) for r in rows if r.get("info_2")}
            all_telefon1 = {norm_phone(r.get("Telefon1", "")) for r in rows if r.get("Telefon1")}

            existing_by_info_2 = {k.info_2: k for k in Kontakt.objects.filter(info_2__in=all_info_2)}
            existing_by_telefon1 = {k.telefon1: k for k in Kontakt.objects.filter(telefon1__in=all_telefon1)}
            
            contacts_to_create = []
            seen_keys = set()

            with transaction.atomic():
                for raw_row in rows:
                    row = {k: fix_chars(v) for k, v in raw_row.items()}
                    telefon1 = norm_phone(row.get("Telefon1") or "")
                    info_2 = norm_text(row.get("info_2") or "")
                    key = (telefon1 or "", info_2 or "")
                    if not any(key) or key in seen_keys:
                        if any(key):
                            skipped_duplicates += 1
                        continue
                    seen_keys.add(key)

                    existing_kontakt = None
                    if info_2:
                        existing_kontakt = existing_by_info_2.get(info_2)
                    if not existing_kontakt and telefon1:
                        existing_kontakt = existing_by_telefon1.get(telefon1)

                    if existing_kontakt:
                        new_info3 = norm_text(row.get("info_3") or "")
                        if existing_kontakt.info_3 != new_info3:
                            existing_kontakt.info_3 = new_info3
                            existing_kontakt.save(update_fields=["info_3"])
                            updated_count += 1
                    else:
                        datum_str = norm_text(row.get("Geburtsdatum") or "")
                        geburtsdatum = None
                        if datum_str:
                            try:
                                geburtsdatum = datetime.strptime(datum_str, "%d-%m-%Y").date()
                            except ValueError:
                                geburtsdatum = None
                        
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

                if contacts_to_create:
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
    query = request.GET.get('q', '').strip()
    filter_operator_id = request.GET.get('operator')
    filter_aktivni = request.GET.get('aktivni')
    filter_history = request.GET.get('history')
    filter_last_call_from = request.GET.get('last_call_from')
    filter_last_call_to = request.GET.get('last_call_to')
    filter_customer_type = request.GET.get('customer_type')

    qs = (
        Kontakt.objects
        .select_related('assigned_operator')
        .annotate(
            call_count=Count('historie', distinct=True),
            last_call=Max('historie__datum_cas'),
        )
        .order_by('-id')
    )

    if query:
        qs = qs.filter(
            Q(vorname__icontains=query) | Q(nachname__icontains=query) |
            Q(info_2__icontains=query) | Q(telefon1__icontains=query)
        )
    if filter_operator_id:
        qs = qs.filter(assigned_operator_id=filter_operator_id)
    
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

    operators = CustomUser.objects.filter(is_staff=True).order_by('username')
    recency_options = list(Kontakt.objects.exclude(recency__isnull=True).exclude(recency__exact='').values_list('recency', flat=True).distinct().order_by('recency'))
    customer_type_options = ['vip'] + recency_options

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
    vratky = Vratka.objects.filter(kontakt=kontakt).order_by('-datum_vratky')  
  
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
        'vratky': vratky,   
    }  
    return render(request, 'sprava/kontakt_detail.html', context)

@login_required  
@user_passes_test(is_admin) 
def sprava_vratek(request):  
    summary = None  
    if request.method == 'POST':  
        form = VratkaForm(request.POST, request.FILES)  
        if form.is_valid():  
            excel_file = form.cleaned_data['file']  
              
            if excel_file.size > 10 * 1024 * 1024:  
                messages.error(request, "Soubor je příliš velký (max 10 MB).")  
                return redirect('sprava:sprava_vratek') 
  
            try:  
                messages.info(request, "Soubor byl přijat a zpracovává se. To může chvíli trvat, prosím vyčkejte.")  
  
                xls = pd.ExcelFile(excel_file)  
                sheet_name = xls.sheet_names[0]  
                  
                header_row = -1  
                for i in range(10):  
                    try:  
                        test_df = pd.read_excel(xls, sheet_name=sheet_name, header=i, nrows=1)
                        test_df.columns = test_df.columns.str.strip() 
                        if 'Acct No.' in test_df.columns and 'Return Date' in test_df.columns:  
                            header_row = i  
                            break  
                    except Exception:  
                        continue  
                  
                if header_row == -1:  
                    messages.error(request, "Nepodařilo se najít hlavičku v souboru. Ujistěte se, že soubor obsahuje sloupce 'Acct No.' a 'Return Date'.")  
                    return redirect('sprava:sprava_vratek') 
  
                df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row, dtype={'Acct No.': str})  
                df.columns = df.columns.str.strip()
  
                column_map = {  
                    'Agent No.': 'Agent', 'Acct No.': 'Kd_Nr', 'Inv. No.': 'Rg_Nr', 'Inv Date': 'Rg_Datum',  
                    'Inv Amount': 'Rg_Betrag', 'Return Date': 'Datum_Retoure', 'Return Type': 'Retour_Typ', 'Return Amount': 'Betrag_Retoure'  
                }  
                df_columns = {col: column_map[col] for col in column_map if col in df.columns}  
                df.rename(columns=df_columns, inplace=True)  
  
                summary = {"total_rows": len(df), "processed": 0, "updated": 0, "skipped": 0, "errors": 0, "error_details": []}  
  
                for index, row in df.iterrows():  
                    try:  
                        if pd.isna(row['Kd_Nr']) or pd.isna(row['Datum_Retoure']):  
                            summary['skipped'] += 1  
                            continue  
  
                        customer_id = str(row['Kd_Nr']).strip()  
                        invoice_id = str(row['Rg_Nr']).strip() if pd.notna(row['Rg_Nr']) else None  
                        return_date, invoice_date = None, None  
                        return_amount, invoice_amount = Decimal('0.00'), Decimal('0.00')  
  
                        if pd.notna(row['Datum_Retoure']): return_date = pd.to_datetime(str(int(row['Datum_Retoure'])), format='%Y%m%d').date()  
                        if pd.notna(row['Rg_Datum']): invoice_date = pd.to_datetime(str(int(row['Rg_Datum'])), format='%Y%m%d').date()  
                        if pd.notna(row['Betrag_Retoure']): return_amount = Decimal(str(row['Betrag_Retoure']).replace(',', '.'))  
                        if pd.notna(row['Rg_Betrag']): invoice_amount = Decimal(str(row['Rg_Betrag']).replace(',', '.'))  
  
                        kontakt, created = Kontakt.objects.get_or_create(info_2=customer_id, defaults={'nachname': 'Zákazník z vratky', 'vorname': '', 'aktivni': True}) 
  
                        Vratka.objects.update_or_create(  
                            kontakt=kontakt, cislo_faktury=invoice_id, datum_vratky=return_date,  
                            defaults={  
                                'duvod': row.get('Retour_Typ'), 'castka_vratky': return_amount, 'agent': row.get('Agent'),  
                                'datum_faktury': invoice_date, 'castka_faktury': invoice_amount, 'datum_importu': timezone.now()  
                            }  
                        )  
                        summary['updated'] += 1  
                        summary['processed'] += 1  
  
                    except Exception as e:  
                        summary['errors'] += 1  
                        summary['error_details'].append({"row": index + header_row + 2, "error": str(e)})  
  
                messages.success(request, "Soubor byl úspěšně zpracován.")  
  
            except Exception as e:  
                messages.error(request, f"Nastala kritická chyba při zpracování souboru: {e}. Zkontrolujte formát souboru a zkuste to znovu.")  
                return redirect('sprava:sprava_vratek')
        else:  
            messages.error(request, "Formulář obsahuje chyby. Prosím, nahrajte platný .xlsx soubor.")  
            return redirect('sprava:sprava_vratek')
  
    form = VratkaForm()  
    vratky = Vratka.objects.select_related('kontakt').order_by('-datum_importu')[:100]  
    context = {'form': form, 'vratky': vratky, 'summary': summary}  
    return render(request, 'sprava/sprava_vratek.html', context)

# =============================================================================
# SEKCE: OSTATNÍ (PLACEHOLDERY)
# =============================================================================

@login_required  
@user_passes_test(is_admin)  
def sprava_reporty_overview(request):  
    context = {'page_title': 'Reporty'}  
    return render(request, 'sprava/_placeholder.html', context)  
  
@login_required  
@user_passes_test(is_admin)  
def sprava_podklady_overview(request):  
    context = {'page_title': 'Podklady'}  
    return render(request, 'sprava/_placeholder.html', context)  
  
@login_required  
@user_passes_test(is_admin)  
def sprava_aktivity_overview(request):  
    context = {'page_title': 'Přehled aktivit'}  
    return render(request, 'sprava/_placeholder.html', context)  
  
@login_required  
@user_passes_test(is_admin)  
def sprava_uzivatele_overview(request):  
    users = CustomUser.objects.all().order_by('last_name')
    context = {
        'page_title': 'Správa uživatelů',
        'users': users,
    }  
    return render(request, 'sprava/sprava_uzivatele_list.html', context)

@login_required
@user_passes_test(is_admin)
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Uživatel byl úspěšně vytvořen.')
            return redirect('sprava:sprava_uzivatele_overview')
    else:
        form = UserCreationForm()
    
    context = {
        'page_title': 'Vytvořit nového uživatele',
        'form': form
    }
    return render(request, 'sprava/sprava_user_form.html', context)

@login_required  
@user_passes_test(is_admin)  
def user_edit_view(request, user_id):  
    user = get_object_or_404(CustomUser, pk=user_id)  
    if request.method == 'POST':  
        form = UserEditForm(request.POST, instance=user)  
        if form.is_valid():  
            form.save()  
            messages.success(request, f'Uživatel "{user.username}" byl úspěšně upraven.')  
            return redirect('sprava:sprava_uzivatele_overview')  
    else:  
        form = UserEditForm(instance=user)  
      
    context = {  
        'page_title': f'Upravit uživatele: {user.username}',  
        'form': form  
    }  
    return render(request, 'sprava/sprava_user_form.html', context)