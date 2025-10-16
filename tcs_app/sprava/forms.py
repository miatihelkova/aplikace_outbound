from django import forms
from contacts.models import Kontakt
from django.contrib.auth.models import User

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
        self.fields['assigned_operator'].queryset = User.objects.filter(
            is_staff=True
        ).order_by('username')
        self.fields['assigned_operator'].label = "Přiřazený operátor"
        self.fields['assigned_operator'].required = False