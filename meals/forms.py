"""meals/forms.py"""

from django import forms
from .models import MenuConfig, MealPrice


class MenuConfigForm(forms.ModelForm):
    class Meta:
        model = MenuConfig
        fields = ['effective_date', 'meal_session', 'has_veg', 'has_nonveg',
                  'veg_items', 'nonveg_items', 'description']
        widgets = {
            'effective_date': forms.DateInput(attrs={'type': 'date'}),
            'veg_items':      forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Dal Makhani, Jeera Rice, Roti, Salad'}),
            'nonveg_items':   forms.Textarea(attrs={'rows': 2, 'placeholder': 'e.g. Chicken Curry, Rice, Roti, Raita'}),
            'description':    forms.Textarea(attrs={'rows': 2}),
        }


class MealPriceForm(forms.ModelForm):
    class Meta:
        model = MealPrice
        fields = ['meal_type', 'meal_session', 'price', 'effective_from']
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
        }