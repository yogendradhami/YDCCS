from django.shortcuts import render
from django.http import Http404
from blog.models import BlogPost


def blog_detail(request, blog_slug):
    """Override-friendly blog_detail: prefer BlogPost model, fall back to static template."""
    post = BlogPost.objects.filter(slug=blog_slug, published=True).first()
    if post:
        return render(request, "pages/blog_post_detail.html", {"post": post})

    # Fallback - attempt static template
    from django.template import TemplateDoesNotExist
    template_name = f"pages/blog_posts/{blog_slug}.html"
    try:
        return render(request, template_name, {})
    except TemplateDoesNotExist:
        raise Http404("Blog post not found")
