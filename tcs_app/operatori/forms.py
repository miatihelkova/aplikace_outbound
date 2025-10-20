# operatori/forms.py

from django import forms
from contacts.models import Historie, STATUS_CHOICES

class HistorieForm(forms.ModelForm):
    # Mírně upravíme pole "status", aby mělo na začátku prázdnou volbu
    # a donutilo tak operátora aktivně vybrat výsledek.
    status = forms.ChoiceField(
        choices=[('', '---------')] + STATUS_CHOICES,
        required=True,
        label="Výsledek hovoru",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Historie
        # Pole, která chceme ve formuláři zobrazit
        fields = ['status', 'poznamka', 'naplanovany_hovor']
        
        # Zde definujeme, jak mají jednotlivá políčka vypadat (HTML widgety)
        widgets = {
            'poznamka': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Zadejte podrobnosti k hovoru...'
            }),
            'naplanovany_hovor': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local', 
                    'class': 'form-control'
                }
            ),
        }
        
        # Přejmenujeme popisky polí pro lepší srozumitelnost
        labels = {
            'poznamka': 'Poznámka',
            'naplanovany_hovor': 'Naplánovat další hovor na'
        }