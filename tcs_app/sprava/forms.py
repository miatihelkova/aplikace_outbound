# sprava/forms.py

from django import forms
from contacts.models import Kontakt
from .models import CustomUser

# --- Formuláře pro kontakty a vratky (beze změny) ---
class ContactsUploadForm(forms.Form):
    file = forms.FileField(label="CSV soubor s kontakty")

class KontaktEditForm(forms.ModelForm):
    class Meta:
        model = Kontakt
        fields = [
            'vorname', 'nachname', 'telefon1', 'telefon2',
            'strasse', 'plz', 'ort', 'recency', 'vip', 'aktivni',
            'assigned_operator'
        ]
        widgets = {
            'vorname': forms.TextInput(attrs={'class': 'form-control'}),
            'nachname': forms.TextInput(attrs={'class': 'form-control'}),
            'telefon1': forms.TextInput(attrs={'class': 'form-control'}),
            'telefon2': forms.TextInput(attrs={'class': 'form-control'}),
            'strasse': forms.TextInput(attrs={'class': 'form-control'}),
            'plz': forms.TextInput(attrs={'class': 'form-control'}),
            'ort': forms.TextInput(attrs={'class': 'form-control'}),
            'recency': forms.TextInput(attrs={'class': 'form-control'}),
            'vip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'aktivni': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assigned_operator': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_operator'].queryset = CustomUser.objects.filter(
            is_staff=True
        ).order_by('username')
        self.fields['assigned_operator'].label = "Přiřazený operátor"
        self.fields['assigned_operator'].required = False

class VratkaForm(forms.Form):
    file = forms.FileField(
        label="Vyberte .xlsx soubor pro import vratek",
        help_text="Nahrávejte pouze soubory ve formátu .xlsx.",
        widget=forms.ClearableFileInput(attrs={'accept': '.xlsx', 'class': 'form-control'})
    )

# =============================================================================
# Formuláře pro UŽIVATELE
# =============================================================================

# --- Formulář pro VYTVOŘENÍ uživatele (s úpravou formátu data) ---
class UserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Heslo")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potvrzení hesla")
    
    # ZMĚNA: Definujeme pole pro datum s novým formátem
    datum_narozeni = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'],
        required=False
    )
    svatek = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'],
        required=False
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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# --- NOVÝ formulář pro ÚPRAVU uživatele ---
class UserEditForm(forms.ModelForm):
    # Hesla jsou zde nepovinná - mění se jen pokud jsou vyplněná
    password = forms.CharField(widget=forms.PasswordInput, label="Nové heslo (nechte prázdné, pokud neměníte)", required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Potvrzení nového hesla", required=False)

    # ZMĚNA: Definujeme pole pro datum s novým formátem
    datum_narozeni = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'],
        required=False
    )
    svatek = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'text', 'class': 'form-control', 'placeholder': 'DD.MM.RRRR'}),
        input_formats=['%d.%m.%Y'],
        required=False
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

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user