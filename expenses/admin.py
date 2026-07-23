from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("date", "category", "amount", "paid_by")
    list_filter = ("category",)
    search_fields = ("description", "notes")
    ordering = ("-date",)
