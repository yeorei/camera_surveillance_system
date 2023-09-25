from django import forms
from .models import UserProfile

class UserForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = 'email', 'camera', 'path'

        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'camera': forms.NumberInput(attrs={'class': 'form-control'}),
            'path': forms.Select(attrs={'class': 'form-control'})
        }