# sprava/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from contacts.models import Kontakt
from .models import CustomUser

# =============================================================================
# ZÁKLADNÍ FORMULÁŘ PRO NAHRÁVÁNÍ SOUBORŮ (PRO ZNOVUPOUŽITÍ)
# =============================================================================

class BaseUploadForm(forms.Form):
    file = forms.FileField(label="Vyberte soubor")

    def __init__(self, *args, **kwargs):
        self.allowed_extensions = kwargs.pop('allowed_extensions', [])
        self.max_size_mb = kwargs.pop('max_size_mb', 10)
        super().__init__(*args, **kwargs)
        
        allowed_str = ", ".join([f".{ext}" for ext in self.allowed_extensions])
        self.fields['file'].help_text = f"Povolené typy souborů: {allowed_str}. Max. velikost: {self.max_size_mb} MB."
        self.fields['file'].widget.attrs.update({
            'class': 'form-control',
            'accept': allowed_str
        })

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if not uploaded_file:
            raise ValidationError("Nebyl vybrán žádný soubor.")

        if uploaded_file.size > self.max_size_mb * 1024 * 1024:
            raise ValidationError(f"Soubor je příliš velký (maximum je {self.max_size_mb} MB).")

        extension = uploaded_file.name.split('.')[-1].lower()
        if self.allowed_extensions and extension not in self.allowed_extensions:
            allowed_str = ", ".join(self.allowed_extensions)
            raise ValidationError(f"Nepovolený typ souboru. Povolené typy jsou: {allowed_str}.")

        return uploaded_file

# =============================================================================
# KONKRÉTNÍ FORMULÁŘE PRO IMPORT (DĚDÍ Z BASE)
# =============================================================================

class ContactsUploadForm(BaseUploadForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, allowed_extensions=['csv'], max_size_mb=20)
        self.fields['file'].label = "CSV soubor s kontakty"


class VratkaForm(BaseUploadForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, allowed_extensions=['xlsx'], max_size_mb=10)
        self.fields['file'].label = "XLSX soubor s vratkami"

# =============================================================================
# FORMULÁŘE PRO SPRÁVU UŽIVATELŮ A KONTAKTŮ
# =============================================================================

class KontaktEditForm(forms.ModelForm):
    class Meta:
        model = Kontakt
        # --- OPRAVA: Použity správné názvy polí z modelu Kontakt ---
        fields = [
            'ansprache', 'titel', 'vorname', 'nachname', 'geburtsdatum',
            'telefon1', 'telefon2',
            'strasse', 'plz', 'ort',
            'info_1', 'info_3', # info_2 je odebráno, protože nemá být editovatelné
            'recency', 'assigned_operator',
            'aktivni', 'trvale_blokovan', 'vip'
        ]
        widgets = {
            # Textová pole
            'ansprache': forms.TextInput(attrs={'class': 'form-control'}),
            'titel': forms.TextInput(attrs={'class': 'form-control'}),
            'vorname': forms.TextInput(attrs={'class': 'form-control'}),
            'nachname': forms.TextInput(attrs={'class': 'form-control'}),
            'telefon1': forms.TextInput(attrs={'class': 'form-control'}),
            'telefon2': forms.TextInput(attrs={'class': 'form-control'}),
            'strasse': forms.TextInput(attrs={'class': 'form-control'}),
            'plz': forms.TextInput(attrs={'class': 'form-control'}),
            'ort': forms.TextInput(attrs={'class': 'form-control'}),
            'info_1': forms.TextInput(attrs={'class': 'form-control'}),
            'info_3': forms.TextInput(attrs={'class': 'form-control'}),
            'recency': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Speciální pole
            'geburtsdatum': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'assigned_operator': forms.Select(attrs={'class': 'form-select'}),
            
            # Přepínače
            'aktivni': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'trvale_blokovan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nastavení pro pole "Přiřazený operátor"
        self.fields['assigned_operator'].queryset = CustomUser.objects.filter(
            is_active=True
        ).order_by('username')
        self.fields['assigned_operator'].required = False
        
        # Přejmenování popisků pro lepší srozumitelnost
        self.fields['info_1'].label = "DBK"
        self.fields['info_3'].label = "Přednostní číslo"
        self.fields['recency'].label = "Typ zákazníka"
        self.fields['vorname'].label = "Jméno"
        self.fields['nachname'].label = "Příjmení"
        self.fields['geburtsdatum'].label = "Datum narození"
        self.fields['ansprache'].label = "Oslovení"
        self.fields['titel'].label = "Titul"
        self.fields['strasse'].label = "Ulice a č.p."
        self.fields['plz'].label = "PSČ"
        self.fields['ort'].label = "Město"


class UserBaseForm(forms.ModelForm):
    datum_narozeni = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control datepicker', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'], required=False
    )
    svatek = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control datepicker', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'], required=False
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'username', 'email', 
            'kod_operatora', 'telefonni_cislo', 'uvazek_hodiny',
            'datum_narozeni', 'svatek', 'is_staff'
        ]
        labels = { 'is_staff': 'Má práva administrátora?' }

    def clean_password_confirm(self):
        password = self.cleaned_data.get("password")
        password_confirm = self.cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Hesla se neshodují.")
        return password_confirm


class UserCreationForm(UserBaseForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Heslo", required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potvrzení hesla", required=True)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password', error)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserEditForm(UserBaseForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Nové heslo (nechte prázdné, pokud neměníte)", required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potvrzení nového hesla", required=False)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error('password', error)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user