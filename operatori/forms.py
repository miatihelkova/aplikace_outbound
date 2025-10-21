# operatori/forms.py

from django import forms
from django.contrib.auth import get_user_model
from contacts.models import STATUS_CHOICES
from datetime import datetime

User = get_user_model()

class CallOutcomeForm(forms.Form):
    """
    Formulář pro zadání výsledku hovoru s finální validační logikou.
    Kombinuje detailní pravidla pro statusy a flexibilní validaci data/času.
    """
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=True,
        label="Výsledek hovoru",
        initial='nedovolano',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_status'})
    )

    poznamka = forms.CharField(
        required=False,
        label="Poznámka",
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'class': 'form-control',
            'placeholder': ' '
        })
    )

    hodnota_objednavky = forms.DecimalField(
        required=False,
        label="Hodnota objednávky (Kč)",
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': ' '})
    )

    dalsi_volani_datum = forms.DateField(
        required=False,
        label="Datum dalšího volání",
        widget=forms.DateInput(
            attrs={'class': 'form-control flatpickr-date', 'placeholder': 'Vyberte datum'},
            format='%d.%m.%Y'
        ),
        input_formats=['%d.%m.%Y']
    )
    
    dalsi_volani_cas = forms.TimeField(
        required=False,
        label="Čas dalšího volání",
        widget=forms.TextInput(
            attrs={'class': 'form-control flatpickr-time', 'placeholder': 'Vyberte čas'}
        ),
        input_formats=['%H:%M']
    )

    jiny_operator = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True).order_by('username'),
        label="Předat operátorovi",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    odlozit_na_datum = forms.DateField(
        required=False,
        label="Odložit na datum",
        widget=forms.DateInput(
            attrs={'class': 'form-control flatpickr-date', 'placeholder': 'Vyberte datum'},
            format='%d.%m.%Y'
        ),
        input_formats=['%d.%m.%Y']
    )

    odlozit_na_cas = forms.TimeField(
        required=False,
        label="Odložit na čas",
        widget=forms.TextInput(
            attrs={'class': 'form-control flatpickr-time', 'placeholder': 'Vyberte čas'}
        ),
        input_formats=['%H:%M']
    )

    # Skrytá pole pro ukládání kombinovaného data a času do views.py
    dalsi_volani = forms.DateTimeField(required=False, widget=forms.HiddenInput())
    odlozit_na = forms.DateTimeField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['jiny_operator'].queryset = User.objects.filter(is_active=True).exclude(pk=user.pk).order_by('username')

    def clean(self):
        """
        Hlavní validační metoda, která kontroluje povinná pole
        na základě zvoleného statusu.
        """
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        # --- OPRAVENÁ A PŘÍSNÁ LOGIKA PRO KOMBINOVÁNÍ DATA A ČASU ---
        # Pokud je vyplněno jen jedno z dvojice (datum/čas), vždy to bude chyba.
        for prefix in ['dalsi_volani', 'odlozit_na']:
            datum = cleaned_data.get(f'{prefix}_datum')
            cas = cleaned_data.get(f'{prefix}_cas')

            if datum and cas:
                cleaned_data[prefix] = datetime.combine(datum, cas)
            elif datum or cas: # Pokud je vyplněno jen jedno z nich, je to chyba
                if not datum:
                    self.add_error(f'{prefix}_datum', 'Pokud zadáváte čas, musíte vyplnit i datum.')
                if not cas:
                    self.add_error(f'{prefix}_cas', 'Pokud zadáváte datum, musíte vyplnit i čas.')
            else:
                cleaned_data[prefix] = None

        # --- VAŠE DETAILNÍ VALIDAČNÍ LOGIKA PODLE FINÁLNÍ TABULKY ---
        if not status:
            self.add_error('status', 'Musíte vybrat výsledek hovoru.')
            return cleaned_data

        if status == 'nezajem':
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Nezájem" je poznámka povinná.')

        elif status == 'nerelevance':
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Nerelevance" je poznámka povinná.')

        elif status in ['prodej', 'vip']:
            if not cleaned_data.get('hodnota_objednavky'):
                self.add_error('hodnota_objednavky', 'Hodnota objednávky je povinná.')
            if not cleaned_data.get('dalsi_volani'):
                # Chybu přidáme k oběma polím, aby bylo jasné, co vyplnit
                self.add_error('dalsi_volani_datum', 'U prodeje musíte naplánovat další hovor (datum i čas).')
                self.add_error('dalsi_volani_cas', None) # Druhá chyba bez textu, jen pro označení pole
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'Poznámka je povinná.')

        elif status == 'volat_pozdeji':
            if not cleaned_data.get('dalsi_volani'):
                self.add_error('dalsi_volani_datum', 'U statusu "Volat později" musíte naplánovat datum i čas.')
                self.add_error('dalsi_volani_cas', None)
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Volat později" je poznámka povinná.')

        elif status == 'predat_operatorovi':
            if not cleaned_data.get('jiny_operator'):
                self.add_error('jiny_operator', 'Musíte vybrat operátora, kterému chcete kontakt předat.')
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'Při předání kontaktu je nutné vyplnit poznámku pro kontext.')
        
        return cleaned_data