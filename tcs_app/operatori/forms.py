# operatori/forms.py

from django import forms
from django.contrib.auth import get_user_model
from contacts.models import STATUS_CHOICES
from datetime import datetime

User = get_user_model()

class CallOutcomeForm(forms.Form):
    """
    Formulář pro zadání výsledku hovoru s novou validační logikou.
    """
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=True,
        label="Výsledek hovoru",
        initial='nedovolano',
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_status'})
    )

    poznamka = forms.CharField(
        required=False, # Povinnost se řeší v clean() metodě
        label="Poznámka",
        widget=forms.Textarea(attrs={
            'rows': 4, 
            'class': 'form-control',
            'placeholder': ' '
        })
    )

    hodnota_objednavky = forms.DecimalField(
        required=False, # Povinnost se řeší v clean() metodě
        label="Hodnota objednávky (Kč)",
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': ' '})
    )

    dalsi_volani_datum = forms.DateField(
        required=False, # Povinnost se řeší v clean() metodě
        label="Datum dalšího volání",
        widget=forms.DateInput(
            attrs={'class': 'form-control flatpickr-date', 'placeholder': 'Vyberte datum'},
            format='%d.%m.%Y'
        ),
        input_formats=['%d.%m.%Y']
    )
    
    dalsi_volani_cas = forms.TimeField(
        required=False, # Povinnost se řeší v clean() metodě
        label="Čas dalšího volání",
        initial='09:00',
        widget=forms.TextInput(
            attrs={'class': 'form-control flatpickr-time', 'placeholder': 'Vyberte čas'}
        ),
        input_formats=['%H:%M']
    )

    jiny_operator = forms.ModelChoiceField(
        required=False, # Povinnost se řeší v clean() metodě
        queryset=User.objects.filter(is_active=True).order_by('username'),
        label="Předat operátorovi",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    odlozit_na_datum = forms.DateField(
        required=False, # Pro 'Nedovoláno' je toto pole nepovinné
        label="Odložit na datum",
        widget=forms.DateInput(
            attrs={'class': 'form-control flatpickr-date', 'placeholder': 'Vyberte datum'},
            format='%d.%m.%Y'
        ),
        input_formats=['%d.%m.%Y']
    )

    odlozit_na_cas = forms.TimeField(
        required=False, # Pro 'Nedovoláno' je toto pole nepovinné
        label="Odložit na čas",
        initial='09:00',
        widget=forms.TextInput(
            attrs={'class': 'form-control flatpickr-time', 'placeholder': 'Vyberte čas'}
        ),
        input_formats=['%H:%M']
    )

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

        # --- Kombinace data a času (zůstává) ---
        # Tato logika zajistí, že pokud je vyplněno datum, musí být i čas a naopak.
        for prefix in ['dalsi_volani', 'odlozit_na']:
            datum = cleaned_data.get(f'{prefix}_datum')
            cas = cleaned_data.get(f'{prefix}_cas')

            if datum and cas:
                cleaned_data[prefix] = datetime.combine(datum, cas)
            elif datum or cas:
                if not datum:
                    self.add_error(f'{prefix}_datum', 'Pokud zadáváte čas, musíte vyplnit i datum.')
                if not cas:
                    self.add_error(f'{prefix}_cas', 'Pokud zadáváte datum, musíte vyplnit i čas.')
            else:
                cleaned_data[prefix] = None

        # --- NOVÁ VALIDAČNÍ LOGIKA PODLE FINÁLNÍ TABULKY ---

        if status == 'nezajem':
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Nezájem" je poznámka povinná.')

        elif status == 'nerelevance':
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Nerelevance" je poznámka povinná.')

        elif status == 'prodej':
            if not cleaned_data.get('hodnota_objednavky'):
                self.add_error('hodnota_objednavky', 'U statusu "Prodej" je hodnota objednávky povinná.')
            if not cleaned_data.get('dalsi_volani'):
                self.add_error('dalsi_volani_datum', 'U statusu "Prodej" musíte naplánovat další hovor.')
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Prodej" je poznámka povinná.')

        elif status == 'vip':
            if not cleaned_data.get('hodnota_objednavky'):
                self.add_error('hodnota_objednavky', 'U statusu "Přidáno do VIP" je hodnota objednávky povinná.')
            if not cleaned_data.get('dalsi_volani'):
                self.add_error('dalsi_volani_datum', 'U statusu "Přidáno do VIP" musíte naplánovat další hovor.')
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Přidáno do VIP" je poznámka povinná.')

        elif status == 'volat_pozdeji':
            if not cleaned_data.get('dalsi_volani'):
                self.add_error('dalsi_volani_datum', 'U statusu "Volat později" musíte naplánovat datum i čas.')
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'U statusu "Volat později" je poznámka povinná.')

        elif status == 'predat_operatorovi':
            if not cleaned_data.get('jiny_operator'):
                self.add_error('jiny_operator', 'Musíte vybrat operátora, kterému chcete kontakt předat.')
            if not cleaned_data.get('poznamka'):
                self.add_error('poznamka', 'Při předání kontaktu je nutné vyplnit poznámku pro kontext.')

        return cleaned_data