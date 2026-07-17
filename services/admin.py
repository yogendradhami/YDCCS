from django.contrib import admin
<<<<<<< HEAD

# Register your models here.
=======
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'is_active')
        }),
        ('Content', {
            'fields': ('description', 'overview', 'hero_image')
        }),
        ('Service Details', {
            'fields': ('included', 'packages'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
>>>>>>> 5815f15 (Initial project commit)
