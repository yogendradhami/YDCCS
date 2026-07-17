# Blog & Image Management - Usage Guide

## Quick Start

### Access Blog Management
```
Dashboard URL: http://localhost:8000/dashboard/blog/
Admin URL: http://localhost:8000/admin/blog/blogpost/
```

### Access Image Management
```
Dashboard URL: http://localhost:8000/dashboard/site-images/
Admin URL: http://localhost:8000/admin/dashboard/siteimage/
```

---

## Blog Post API

### Create a BlogPost
```python
from blog.models import BlogPost
from datetime import datetime

post = BlogPost.objects.create(
    title="My Blog Post Title",
    slug="my-blog-post-title",  # Must be unique
    excerpt="Brief description of the post",
    content="Full blog content goes here...",
    category="Featured",
    published=True,
    published_at=datetime.now()
)
```

### Query Blog Posts
```python
# Get all published posts
posts = BlogPost.objects.filter(published=True)

# Get posts by category
featured = BlogPost.objects.filter(category="Featured")

# Get recent posts
recent = BlogPost.objects.filter(published=True).order_by('-published_at')[:5]

# Get single post by slug
post = BlogPost.objects.get(slug='my-blog-post-title')
```

### Update a BlogPost
```python
post = BlogPost.objects.get(slug='my-blog-post-title')
post.title = "Updated Title"
post.content = "Updated content..."
post.published = True
post.save()
```

### Delete a BlogPost
```python
post = BlogPost.objects.get(slug='my-blog-post-title')
post.delete()
```

---

## Site Image API

### Upload a SiteImage
```python
from dashboard.models import SiteImage
from django.core.files import File

# Option 1: From file object
with open('path/to/image.jpg', 'rb') as f:
    image = SiteImage.objects.create(
        title="Hero Banner 2024",
        category="hero",
        image=File(f)
    )

# Option 2: Using Django FileField directly
from django.core.files.base import ContentFile
image = SiteImage.objects.create(
    title="Team Photo",
    category="team",
    image=ContentFile(file_content, name='photo.jpg')
)
```

### Query SiteImages
```python
# Get all images
images = SiteImage.objects.all()

# Get images by category
hero_images = SiteImage.objects.filter(category="hero")
blog_images = SiteImage.objects.filter(category="blog")

# Get latest uploads
latest = SiteImage.objects.all().order_by('-id')[:10]
```

### Update a SiteImage
```python
image = SiteImage.objects.get(id=1)
image.title = "New Title"
image.category = "team"
image.save()
```

### Delete a SiteImage
```python
image = SiteImage.objects.get(id=1)
image.delete()
# File is automatically deleted from static/uploads/
```

---

## Dashboard Usage

### Adding a Blog Post via Dashboard
1. Navigate to `/dashboard/blog/`
2. Click "Add New Blog Post"
3. Fill in form:
   - **Title:** Post title (e.g., "Spring Cleaning Tips")
   - **Slug:** URL slug (auto-generated from title)
   - **Excerpt:** 1-2 sentence summary
   - **Content:** Full blog post content (use textarea)
   - **Category:** Select from Featured, Residential, Commercial, Tips & Guides, Seasonal
   - **Featured Image:** Upload JPG/PNG
   - **Publish:** Toggle to publish immediately or keep as draft
4. Click "Save"
5. Post appears on `/blog/` if published

### Editing a Blog Post
1. Navigate to `/dashboard/blog/`
2. Find post in list, click "Edit"
3. Modify any fields
4. Click "Save"
5. Changes reflect immediately on front-end

### Deleting a Blog Post
1. Navigate to `/dashboard/blog/`
2. Find post, click "Delete"
3. Confirm deletion
4. Post removed from database and front-end

### Managing Site Images
1. Navigate to `/dashboard/site-images/`
2. **Add new:** Click "Upload Image"
   - Title: Descriptive name
   - Category: hero, blog, service, company, team, or other
   - Image: Select file
3. **Edit:** Click "Edit" on existing image
4. **Delete:** Click "Delete" and confirm
5. Images automatically organized in `static/uploads/<category>/`

---

## Template Usage

### Display Blog List
```django
{% for post in posts %}
    <article class="blog-post">
        <h2>{{ post.title }}</h2>
        <time>{{ post.published_at|date:"F j, Y" }}</time>
        <p class="excerpt">{{ post.excerpt }}</p>
        <a href="{% url 'blog_detail' post.slug %}">Read More</a>
    </article>
{% endfor %}
```

### Display Single Blog Post
```django
<article class="blog-detail">
    <h1>{{ post.title }}</h1>
    {% if post.featured_image %}
        <img src="{{ post.featured_image.url }}" alt="{{ post.title }}">
    {% endif %}
    <p class="meta">{{ post.published_at|date:"F j, Y" }} | {{ post.category }}</p>
    <div class="content">{{ post.content|linebreaks }}</div>
</article>
```

### Display Site Images
```django
{% for image in site_images %}
    <div class="image-item" data-category="{{ image.category }}">
        <img src="{{ image.image.url }}" alt="{{ image.title }}">
        <p>{{ image.title }}</p>
    </div>
{% endfor %}
```

---

## Django Admin Usage

### BlogPost Admin
1. Navigate to `/admin/blog/blogpost/`
2. View all blog posts with title, slug, published status, and date
3. Click post to edit
4. Edit fields:
   - Basic: title, slug, excerpt, content, category
   - Media: featured_image (click to upload)
   - Publishing: published (checkbox), published_at (datetime)
5. Save changes

### SiteImage Admin
1. Navigate to `/admin/dashboard/siteimage/`
2. View all uploaded images with title and category
3. Click image to edit
4. Edit fields:
   - title: Descriptive name
   - category: Category dropdown
   - image: File upload with thumbnail preview
5. Save changes

---

## URL Reference

### Public URLs
| URL | View | Purpose |
|-----|------|---------|
| `/blog/` | `core.views.blog` | Blog listing page |
| `/blog/<slug>/` | `core.views.blog_detail` | Individual blog post |

### Dashboard URLs
| URL | View | Purpose |
|-----|------|---------|
| `/dashboard/blog/` | `dashboard.views.blog_post_list` | Manage all blog posts |
| `/dashboard/blog/add/` | `dashboard.views.add_blog_post` | Create new post |
| `/dashboard/blog/<id>/edit/` | `dashboard.views.edit_blog_post` | Edit existing post |
| `/dashboard/blog/<id>/delete/` | `dashboard.views.delete_blog_post` | Delete post |
| `/dashboard/site-images/` | `dashboard.views.site_images_list` | Manage all images |
| `/dashboard/site-images/add/` | `dashboard.views.add_site_image` | Upload new image |
| `/dashboard/site-images/<id>/edit/` | `dashboard.views.edit_site_image` | Edit image info |
| `/dashboard/site-images/<id>/delete/` | `dashboard.views.delete_site_image` | Delete image |

---

## File Storage

### Upload Directory Structure
```
static/
└── uploads/
    ├── hero/              # Homepage hero images
    ├── blog/              # Blog featured images  
    ├── service/           # Service category images
    ├── company/           # Company/branding images
    ├── team/              # Team member photos
    └── other/             # Miscellaneous images
```

### Accessing Uploaded Files
```django
{# In templates #}
{{ image.image.url }}
{# Outputs: /static/uploads/hero/filename.jpg #}
```

```python
# In Python code
image_url = image.image.url
image_path = image.image.path
```

---

## Troubleshooting

### Image Upload Not Working
1. Ensure `static/uploads/` directory exists and is writable
2. Run: `mkdir -p static/uploads && chmod 755 static/uploads`
3. Check file permissions on Django process

### Blog Post Not Appearing
1. Verify `published=True` is set
2. Check `published_at` date is not in future
3. Verify blog list template is rendering `posts` context variable

### Migration Issues
```bash
# Reset migrations (careful - deletes data!)
python manage.py migrate blog zero
python manage.py migrate blog

# Or create fresh migration
python manage.py makemigrations blog
python manage.py migrate
```

### Template Not Found Error
Ensure `blog_post_detail.html` exists at:
```
templates/pages/blog_post_detail.html
```

---

## SEO Considerations

### Blog Post SEO
- Use descriptive, keyword-rich **titles** (60 chars)
- Create compelling **excerpts** (155-160 chars)
- Use unique, slug-formatted **URLs**
- Include **featured images** (improves engagement)
- Structure **content** with headers (h2, h3)

### Meta Tags (if needed)
Add to blog detail template:
```django
{% block extra_head %}
    <meta name="description" content="{{ post.excerpt }}">
    <meta name="keywords" content="{{ post.category }}">
    <meta property="og:title" content="{{ post.title }}">
    <meta property="og:image" content="{{ post.featured_image.url }}">
{% endblock %}
```

---

## Performance Notes

### Query Optimization
```python
# Avoid N+1 queries - use select_related/prefetch_related if adding ForeignKeys
posts = BlogPost.objects.filter(published=True).select_related('author')
```

### Image Optimization
- Recommended image sizes for blog: 1200x600px (2:1 ratio)
- Use JPG for photos, PNG for graphics
- Compress images before uploading
- Consider CDN for large deployments

### Caching (Optional)
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def blog_list(request):
    posts = BlogPost.objects.filter(published=True).order_by('-published_at')
    return render(request, 'pages/blog.html', {'posts': posts})
```

---

## Model Reference

### BlogPost Fields
```python
title              CharField(max_length=255)          # Post title
slug               SlugField(unique=True)             # URL slug
excerpt            TextField()                        # Brief summary
content            TextField()                        # Full content
featured_image     ImageField()                       # Featured image
category           CharField(choices=...)             # Post category
published          BooleanField(default=False)        # Publish status
published_at       DateTimeField()                    # Publish date
created_at         DateTimeField(auto_now_add=True)  # Creation date
updated_at         DateTimeField(auto_now=True)      # Last update
```

### SiteImage Fields
```python
title              CharField(max_length=255)         # Image title
category           CharField(choices=...)            # Category
image              ImageField()                      # Image file
created_at         DateTimeField(auto_now_add=True)  # Upload date
```

---

## Support

For issues or questions:
1. Check Django logs: `python manage.py runserver`
2. Run system check: `python manage.py check`
3. Review admin interface for data integrity
4. Verify file permissions on `static/uploads/`

