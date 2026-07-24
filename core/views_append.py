from django.shortcuts import redirect, render
from django.http import Http404
from blog.models import BlogPost


def blog_detail(request, blog_slug):
    """Override-friendly blog_detail: prefer BlogPost model, fall back to static template."""
    post = BlogPost.objects.filter(slug=blog_slug, published=True).first()
    if post:
        posts = BlogPost.objects.filter(published=True).order_by("-published_at")
        related_posts = posts.exclude(pk=post.pk)[:5]
        return render(
            request,
            "pages/blog_post_detail.html",
            {"post": post, "posts": posts, "related_posts": related_posts},
        )

    legacy_slug_map = {
        "deep-cleaning-vs-regular-cleaning-when-you-need-each": "deep-cleaning-vs-regular-cleaning",
    }
    if blog_slug in legacy_slug_map:
        return redirect(
            "blog_detail",
            blog_slug=legacy_slug_map[blog_slug],
            permanent=False,
        )

    # Fallback - attempt static template
    from django.template import TemplateDoesNotExist
    template_name = f"pages/blog_posts/{blog_slug}.html"
    try:
        return render(request, template_name, {})
    except TemplateDoesNotExist:
        raise Http404("Blog post not found")
