# Unified Gallery System Documentation

## Overview

The unified gallery system automatically collects and displays images from all sources across the YD Commercial Cleaning platform:
- **Admin uploads** (manual gallery additions)
- **Job photos** (from booking completions)
- **Customer uploads** (from booking forms)
- **Employee uploads** (from job documentation)
- **Booking forms** (automated submissions)

All images display on the public `/gallery/` page with advanced filtering, before/after comparisons, and staff-only deletion capabilities.

---

## Architecture

### Models

#### GalleryItem (Enhanced)
```python
class GalleryItem(models.Model):
    # Identification
    title              # Image title
    service_type       # Service category (from choices)
    suburb             # Location
    
    # Images (supports before/after OR single image)
    before_image       # Before photo (optional)
    after_image        # After photo (optional)
    image              # Generic single image (optional)
    
    # Meta
    description        # Image description
    featured           # Display on public gallery
    source             # Where image came from (admin, job_photo, customer, etc.)
    job_photo          # Link to original JobPhoto if applicable
    created_at         # Upload timestamp
    updated_at         # Last modified timestamp
    
    @property
    primary_image      # Returns the best available image for display
```

**Source Types:**
- `admin` - Manually uploaded from Django admin
- `job_photo` - Automatically from JobPhoto model (booking completion)
- `customer` - Customer uploaded from booking form
- `employee` - Employee uploaded during job documentation
- `booking` - From booking form submission
- `manual` - Manual upload from dashboard

### Signals

**Auto-sync from JobPhotos:**
- When a `JobPhoto` is created → Auto-creates linked `GalleryItem`
- When a `JobPhoto` is deleted → Auto-removes linked `GalleryItem`
- Link preserved via `job_photo` ForeignKey for reference and deletion

---

## Features

### 1. Public Gallery Page (`/gallery/`)

**Features:**
- ✅ Grid layout with before/after comparison cards
- ✅ Service type filtering (dropdown)
- ✅ Source filtering (admin, job photos, etc.)
- ✅ Image modal viewer for full-size viewing
- ✅ Staff/admin delete buttons (protected endpoint)
- ✅ Gallery statistics (total images, service types)
- ✅ Responsive design (mobile-friendly)
- ✅ Auto-playing before/after swipe on hover

**URL:** `/gallery/`
**Template:** `templates/gallery/gallery.html`

### 2. Dashboard Gallery Manager (`/dashboard/gallery/`)

**Features:**
- 📊 All images in card grid with thumbnails
- 🏷️ Source badges (color-coded)
- ⏰ Creation dates and metadata
- ✏️ Edit functionality (admin panel)
- 🗑️ Delete functionality with confirmation
- 📈 Statistics dashboard
- 🔗 Links to linked job photos

**URL:** `/dashboard/gallery/`
**Template:** `templates/dashboard/gallery/dashboard_gallery_list.html`

### 3. Admin Panel Integration

**Enhanced Features:**
- 📷 Full gallery preview (before/after/single)
- 🔗 Link to source JobPhoto
- 📝 Comprehensive form with fieldsets
- ✅ Readonly fields for metadata
- 🎨 Beautiful inline image previews
- 🗑️ Quick delete button
- 🔒 Readonly source field if linked to job photo

**Accessible via:** Django Admin `/admin/gallery/galleryitem/`

---

## Data Flow

### Automatic Image Linking (Job Photos)

```
Booking Completed
     ↓
JobPhoto Created (before/after photos)
     ↓
Signal Triggered: auto_add_job_photo_to_gallery()
     ↓
GalleryItem Created with:
   - image = JobPhoto.image
   - source = 'job_photo'
   - job_photo_id = JobPhoto.id (FK)
   - featured = True (auto-display)
     ↓
Image appears on public /gallery/ immediately
     ↓
Staff can edit/delete from admin or dashboard
```

### Manual Upload (Admin)

```
Admin logs into Django Admin
     ↓
Creates new GalleryItem:
   - Upload before/after OR single image
   - Enter title, service, location
   - Set featured = True/False
     ↓
Gallery item displays on /gallery/ if featured
```

---

## Usage Guide

### For Users (Public)

1. **View Gallery:** Visit `/gallery/` to see all cleaning results
2. **Filter Images:** 
   - Select service type to filter (e.g., "Office Cleaning")
   - Select source to filter (e.g., "Job Photos")
   - Click reset to clear filters
3. **View Full-size:** Click "👁️ View" button to open image modal
4. **Before/After:** Scroll down to see before/after comparison if available

### For Admins (Dashboard)

1. **Access Dashboard:** `/dashboard/gallery/`
2. **View All Images:** See grid of all images with source badges
3. **Edit:** Click "✏️ Edit" to modify title, description, featured status
4. **Delete:** Click "🗑️ Delete" to remove (with confirmation)
5. **Admin Panel:** Access `/admin/gallery/galleryitem/` for advanced management

### For Admin (Django Admin)

1. **Add Item:** `/admin/gallery/galleryitem/add/`
   - Upload before/after images OR single image
   - Fill title, service, suburb, description
   - Save and publish
   
2. **Edit Item:** Click item in list view
   - Modify any field
   - See full image preview
   - Edit or delete

3. **Source Field:**
   - Auto-set when linked to JobPhoto (readonly)
   - Editable for manual uploads

---

## API Endpoints

### Public Endpoints

**GET** `/gallery/`
- Display gallery page
- Query params:
  - `service` - Filter by service type
  - `source` - Filter by source
- Returns: `gallery.html` with filtered items

**GET** `/gallery/<int:item_id>/delete/` (POST only)
- Delete gallery item (staff/admin only)
- Returns: JSON `{success: true/false, message: "..."}`
- Requires: CSRF token, staff permissions

### Dashboard Endpoints

**GET/POST** `/dashboard/gallery/` - List gallery items
**GET/POST** `/dashboard/gallery/add/` - Add manual item
**GET/POST** `/dashboard/gallery/<int:item_id>/edit/` - Edit item
**GET/POST** `/dashboard/gallery/<int:item_id>/delete/` - Delete item

---

## Templates

### Public Gallery (`templates/gallery/gallery.html`)
- Hero section with title & CTA
- Filter controls (service, source)
- Gallery grid (3-column responsive)
- Image cards with:
  - Thumbnail
  - Service badge
  - Source badge (color-coded)
  - Description
  - Before/after mini-cards
  - Action buttons
- Modal image viewer
- Statistics dashboard

### Dashboard Gallery (`templates/dashboard/gallery/dashboard_gallery_list.html`)
- Header with quick actions
- Statistics cards
- Gallery grid (4-column responsive)
- Image cards with:
  - Thumbnail
  - Source badge
  - Title & service
  - Description
  - Metadata (location, date, linked job)
  - Edit/Delete buttons

### Admin (`gallery/admin.py`)
- Beautiful inline image previews
- Organized fieldsets
- Readonly metadata
- Quick action buttons

---

## Database Schema

### GalleryItem Fields

| Field | Type | Description |
|-------|------|-------------|
| id | Primary Key | Auto-generated |
| title | CharField(150) | Image title |
| service_type | CharField(100) | Service category |
| suburb | CharField(100) | Location (optional) |
| before_image | ImageField | Before photo (optional) |
| after_image | ImageField | After photo (optional) |
| image | ImageField | Generic image (optional) |
| description | TextField | Description (optional) |
| featured | BooleanField | Display status |
| source | CharField(20) | Upload source |
| job_photo | ForeignKey | Link to JobPhoto (optional) |
| created_at | DateTime | Created timestamp |
| updated_at | DateTime | Updated timestamp |

### Migrations

- `0001_initial.py` - Original model
- `0002_auto_gallery_unified.py` - Enhanced model with new fields

---

## Configuration

### Settings (`ydcleaning/settings.py`)

```python
# Ensure gallery app is in INSTALLED_APPS
INSTALLED_APPS = [
    # ...
    'gallery',
    # ...
]

# Image upload settings
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# File storage (supports local or Cloudinary)
# LOCAL: Default FileSystemStorage
# CLOUDINARY: Set DEFAULT_FILE_STORAGE to cloudinary_storage
```

### URLs (`gallery/urls.py`)

```python
urlpatterns = [
    path("gallery/", gallery_page, name="gallery"),
    path("gallery/<int:item_id>/delete/", delete_gallery_item_ajax, name="delete_gallery_item_ajax"),
]
```

---

## Styling & Customization

### CSS Classes

**Public Gallery:**
- `.gallery-hero` - Hero section
- `.gallery-grid` - Main grid container
- `.gallery-card` - Individual image card
- `.gallery-image` - Image element
- `.source-badge` - Source indicator
- `.before-after-grid` - Before/after comparison

**Dashboard:**
- `.dashboard-gallery-grid` - Main grid
- `.dashboard-gallery-card` - Image card
- `.gallery-source-badge` - Source badge
- `.stat-card` - Statistics cards

### Colors

**Source Badges:**
- `admin` - #667eea (Purple)
- `job_photo` - #4CAF50 (Green)
- `customer` - #2196F3 (Blue)
- `employee` - #FF9800 (Orange)
- `booking` - #9C27B0 (Deep Purple)

---

## Troubleshooting

### Images Not Appearing

1. ✅ Check `featured=True` on GalleryItem
2. ✅ Verify `before_image.url`, `after_image.url`, or `image.url` is set
3. ✅ Check file permissions in `media/` directory
4. ✅ Verify `MEDIA_ROOT` and `MEDIA_URL` in settings

### Auto-sync Not Working

1. ✅ Ensure `gallery.signals` is imported in `gallery/apps.py`
2. ✅ Check `JobPhoto` model has `image` field
3. ✅ Verify `photo_type` is 'before' or 'after'
4. ✅ Check database for `gallery_galleryitem` table

### Delete Not Working

1. ✅ Verify user is `staff=True` or `superuser=True`
2. ✅ Check CSRF token in AJAX request
3. ✅ Verify endpoint URL is correct
4. ✅ Check browser console for JavaScript errors

---

## Performance Optimization

### Database Queries

- Use `select_related('job_photo')` for admin
- Use `prefetch_related()` for related bookings
- Index `source`, `featured`, `created_at` fields

### Image Optimization

- Resize large images before upload
- Use WebP format for smaller file sizes
- Lazy load images on public gallery page
- Use responsive image srcset

### Caching

```python
# Cache gallery items for 1 hour
@cache_page(60 * 60)
def gallery_page(request):
    # ...
```

---

## Security

### Staff-Only Deletion

```python
# In views.py
if not (request.user.is_staff or request.user.is_superuser):
    return JsonResponse({"success": False, "message": "Permission denied"}, status=403)
```

### CSRF Protection

- All DELETE requests require CSRF token
- Implemented in AJAX with `getCookie('csrftoken')`
- Django middleware validates automatically

---

## Future Enhancements

- [ ] Bulk upload functionality
- [ ] Before/after slider (JavaScript component)
- [ ] Image tags/categories
- [ ] Customer testimonials linked to gallery
- [ ] Social sharing integration
- [ ] Lightbox gallery mode
- [ ] Pagination for large galleries
- [ ] Advanced image editing in admin
- [ ] Image SEO metadata (alt text, descriptions)
- [ ] Gallery analytics (views, engagement)

---

## Support

For issues or questions:
1. Check this documentation
2. Review code comments in `gallery/`
3. Check Django admin error messages
4. Review browser console for JavaScript errors
5. Check server logs for Python exceptions

---

**Last Updated:** July 24, 2026
**Version:** 1.0
**Status:** Production Ready ✅
