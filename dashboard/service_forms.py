"""
Service Management Forms for Dashboard
File: dashboard/service_forms.py
Purpose: Forms for managing services through the dashboard
"""

from django import forms
from services.models import Service
import json


class ServiceForm(forms.ModelForm):
    """Form for creating/editing services with JSON field support"""
    
    included_items = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter each included item on a new line'
        }),
        help_text='Enter each item on a new line (e.g., Daily cleaning\nWeekly scheduling)',
        required=False
    )
    
    packages_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Enter JSON format packages'
        }),
        help_text='Enter packages as JSON: [{"name": "Package 1", "price": "$100", "description": "Description"}]',
        required=False
    )
    
    class Meta:
        model = Service
        fields = ['name', 'slug', 'description', 'overview', 'hero_image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (e.g., commercial-cleaning)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description'}),
            'overview': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Longer overview for detail pages'}),
            'hero_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_included_items(self):
        """Convert textarea to JSON list"""
        data = self.cleaned_data.get('included_items', '')
        if data:
            items = [item.strip() for item in data.split('\n') if item.strip()]
            return items
        return []
    
    def clean_packages_json(self):
        """Validate JSON format"""
        data = self.cleaned_data.get('packages_json', '')
        if data:
            try:
                packages = json.loads(data)
                if not isinstance(packages, list):
                    raise ValueError('Packages must be a JSON array')
                return packages
            except json.JSONDecodeError as e:
                raise forms.ValidationError(f'Invalid JSON format: {str(e)}')
        return []
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.included = self.cleaned_data.get('included_items', [])
        instance.packages = self.cleaned_data.get('packages_json', [])
        if commit:
            instance.save()
        return instance
