from django.contrib import admin
<<<<<<< HEAD
=======
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "published", "published_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "excerpt", "content")
    list_filter = ("published", "category")
from django.contrib import admin
>>>>>>> 5815f15 (Initial project commit)

# Register your models here.
