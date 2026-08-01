from django.contrib import admin
from .models import FAQQuestion

# Register your models here.


@admin.register(FAQQuestion)
class FAQQuestionAdmin(admin.ModelAdmin):
	list_display = ("id", "question", "name", "email", "is_published", "created_at")
	list_filter = ("is_published", "created_at")
	search_fields = ("question", "answer", "name", "email")
	readonly_fields = ("created_at", "answered_at")
