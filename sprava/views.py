# sprava/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Max, Q
from django.core.paginator import Paginator
from django.utils import timezone
from contacts.models import Kontakt, Historie, Vratka
from .models import CustomUser
from datetime import datetime
from contacts.models import STATUS_CHOICES

from .forms import KontaktEditForm, VratkaForm, UserCreationForm, UserEditForm, ContactsUploadForm
from .importers import import_contacts_from_csv, import_vratky_from_excel

# =============================================================================
# POMOCNÉ FUNKCE
# =============================================================================

def is_admin(user):
    return user.is_authenticated and user.is_staff

# =============================================================================
# HLAVNÍ STRÁNKA (DASHBOARD) - TATO FUNKCE ZDE MUSÍ BÝT
# =============================================================================

@login_required
@user_passes_test(is_admin)
def sprava_dashboard(request):
    context = {'page_title': 'Hlavní přehled'}
    return render(request, 'sprava/sprava_dashboard.html', context)

# =============================================================================
# SEKCE: DATABÁZE
# =============================================================================

@login_required
@user_passes_test(is_admin)
def sprava_databaze_overview(request):
    all_contacts = Kontakt.objects.all()
    total_contacts = all_contacts.count()
    active_contacts = all_contacts.filter(aktivni=True).count()
    vip_contacts = all_contacts.filter(vip=True).count()
    active_without_history = Kontakt.objects.annotate(call_count=Count('historie')).filter(aktivni=True, call_count=0).count()
    last_return_import = Vratka.objects.order_by('-datum_importu').first()
    last_contact_import = Kontakt.objects.order_by('-id').first()

    context = {
        'page_title': 'Přehled databáze',
        'total_contacts': total_contacts,
        'active_contacts': active_contacts,
        'inactive_contacts': total_contacts - active_contacts,
        'vip_contacts': vip_contacts,
        'active_without_history': active_without_history,
        'last_return_import_date': last_return_import.datum_importu if last_return_import else None,
        'last_contact_import_date': last_contact_import.updated_at if last_contact_import else None,
    }
    return render(request, 'sprava/sprava_databaze_overview.html', context)

@login_required
@user_passes_test(is_admin)
def upload_contacts(request):
    if request.method == "POST":
        form = ContactsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]
            result = import_contacts_from_csv(csv_file)
            
            if result["success"]:
                success_message = (
                    f"Import dokončen! Celkem řádků v souboru: {result.get('total', 'N/A')}. "
                    f"Vytvořeno: {result['created']}, Aktualizováno: {result['updated']}. "
                    f"Přeskočeno duplicit: {result['skipped']}."
                )
                messages.success(request, success_message)
            else:
                messages.error(request, result["message"])
            
            return redirect("sprava:upload_contacts")
    else:
        form = ContactsUploadForm()

    return render(request, "sprava/upload_contacts.html", {"form": form})

@login_required
@user_passes_test(is_admin)
def sprava_vratek(request):
    if request.method == 'POST':
        form = VratkaForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = form.cleaned_data['file']
            summary = import_vratky_from_excel(excel_file)
            
            if summary["success"]:
                success_message = (
                    f"Zpracování dokončeno. Celkem řádků: {summary['total_rows']}. "
                    f"Zpracováno: {summary['processed']}, Aktualizováno: {summary['updated']}. "
                    f"Přeskočeno: {summary['skipped']}, Chyb: {summary['errors']}."
                )
                messages.success(request, success_message)
                if summary['errors'] > 0:
                    messages.warning(request, f"V souboru se vyskytly chyby. Zkontrolujte detaily v logu serveru.")
            else:
                messages.error(request, summary["message"])
        
        return redirect('sprava:vratky')

    form = VratkaForm()
    vratky_list = Vratka.objects.select_related('kontakt').order_by('-datum_importu')
    
    paginator = Paginator(vratky_list, 50)
    page_number = request.GET.get('page')
    vratky_page = paginator.get_page(page_number)

    context = {'form': form, 'vratky_page': vratky_page}
    return render(request, 'sprava/sprava_vratek.html', context)

# =============================================================================
# SEKCE: KONTAKTY
# =============================================================================

@login_required
@user_passes_test(is_admin)
def contacts_list(request):
    query = request.GET.get('q', '').strip()
    filter_operator_id = request.GET.get('operator')
    filter_stav = request.GET.get('stav')
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

    if filter_stav == 'aktivni':
        qs = qs.filter(aktivni=True)
    elif filter_stav == 'docasne_neaktivni':
        qs = qs.filter(aktivni=False, trvale_blokovan=False, deaktivovan_do__gte=timezone.now().date())
    elif filter_stav == 'trvale_neaktivni':
        qs = qs.filter(aktivni=False, trvale_blokovan=True)

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

    operators = CustomUser.objects.filter(is_active=True).order_by('username')
    recency_options = list(Kontakt.objects.exclude(recency__isnull=True).exclude(recency__exact='').values_list('recency', flat=True).distinct().order_by('recency'))
    customer_type_options = ['vip'] + recency_options

    paginator = Paginator(qs, 50)
    page = request.GET.get("page")
    contacts = paginator.get_page(page)
    
    other_params = request.GET.copy()
    if 'page' in other_params:
        del other_params['page']
    
    context = {
        "contacts": contacts,
        "operators": operators,
        "customer_type_options": customer_type_options,
        "other_params": other_params.urlencode(),
    }
    return render(request, "sprava/contacts_list.html", context)

@login_required  
@user_passes_test(is_admin)  
def kontakt_detail(request, kontakt_id):  
    kontakt = get_object_or_404(Kontakt, pk=kontakt_id)  
    historie = Historie.objects.filter(kontakt=kontakt).select_related('operator').order_by('-datum_cas')  
    vratky = Vratka.objects.filter(kontakt=kontakt).order_by('-datum_vratky')  
  
    # === ZMĚNA: PŘIDÁN VÝPOČET STATISTIK PRO POČÍTADLO ===
    status_counts = historie.values('status').annotate(count=Count('status')).order_by()
    status_display_map = dict(STATUS_CHOICES)
    status_stats = {}
    for item in status_counts:
        status_code = item['status']
        if status_code: # Ignorujeme prázdné statusy
            display_name = status_display_map.get(status_code, status_code)
            status_stats[display_name] = item['count']
    # =====================================================

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
        'status_stats': status_stats, # <-- ZMĚNA: PŘEDÁNÍ STATISTIK DO ŠABLONY
    }  
    return render(request, 'sprava/kontakt_detail.html', context)

# =============================================================================
# OSTATNÍ SEKCE
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
def sprava_historie_hovoru(request):
    historie_list = (
        Historie.objects
        .select_related('operator', 'kontakt')
        .order_by('-datum_cas')
    )

    paginator = Paginator(historie_list, 50)  # Zobrazíme 50 záznamů na stránku
    page_number = request.GET.get('page')
    historie_page = paginator.get_page(page_number)

    context = {
        'page_title': 'Historie všech hovorů',
        'historie_page': historie_page
    }
    return render(request, 'sprava/sprava_historie_hovoru.html', context)
  
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
            
            if user == request.user and not form.cleaned_data.get('is_staff'):
                messages.error(request, 'Nemůžete odebrat administrátorská práva svému vlastnímu účtu.')
            else:
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

@login_required
@user_passes_test(is_admin)
def user_delete_view(request, user_id):
    user_to_delete = get_object_or_404(CustomUser, pk=user_id)

    if user_to_delete == request.user:
        messages.error(request, 'Nemůžete smazat vlastní účet, pod kterým jste přihlášeni.')
        return redirect('sprava:sprava_uzivatele_overview')

    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f'Uživatel "{username}" byl úspěšně smazán.')
        return redirect('sprava:sprava_uzivatele_overview')

    context = {
        'page_title': 'Potvrzení smazání uživatele',
        'user_to_delete': user_to_delete
    }
    return render(request, 'sprava/sprava_user_confirm_delete.html', context)