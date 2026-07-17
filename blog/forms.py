from django import forms
from .models import BlogPost


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "slug", "excerpt", "content", "category", "featured_image", "published", "published_at"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
            "excerpt": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 10}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "featured_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
        }
