# Unified Gallery System - Quick Reference

## 🎯 At a Glance

**What:** Automatic gallery system that collects images from all sources  
**Where:** `/gallery/` (public), `/dashboard/gallery/` (staff), `/admin/gallery/` (admin)  
**Features:** Auto-sync from job photos, advanced filtering, delete management  
**Status:** ✅ Production Ready  

---

## 📍 URL Map

| URL | Purpose | Access |
|-----|---------|--------|
| `/gallery/` | Public gallery with filters | Everyone |
| `/gallery/?service=...&source=...` | Filtered gallery | Everyone |
| `/gallery/<id>/delete/` | AJAX delete endpoint | Staff only |
| `/dashboard/gallery/` | Gallery manager | Staff only |
| `/dashboard/gallery/add/` | Add image manually | Staff only |
| `/dashboard/gallery/<id>/edit/` | Edit image | Staff only |
| `/dashboard/gallery/<id>/delete/` | Delete (with confirmation) | Staff only |
| `/admin/gallery/galleryitem/` | Admin interface | Admins only |

---

## 🖼️ Image Sources

| Source | Auto-Sync? | Where It Comes From |
|--------|-----------|-------------------|
| **admin** | ❌ Manual | Django admin upload |
| **job_photo** | ✅ Automatic | Booking job photos |
| **customer** | ❌ Manual | (Extensible) Customer form |
| **employee** | ❌ Manual | (Extensible) Employee upload |
| **booking** | ❌ Manual | (Extensible) Booking form |
| **manual** | ❌ Manual | Dashboard add form |

---

## 📊 Data Model

```
GalleryItem
├── title (CharField)
├── service_type (Choice)
├── suburb (CharField)
├── featured (Boolean) ← Controls visibility
├── source (Choice) ← Where it came from
├── before_image (Optional)
├── after_image (Optional)
├── image (Optional) ← Single image
├── description (TextField)
├── job_photo (ForeignKey) ← Link to JobPhoto
├── created_at (DateTime)
└── updated_at (DateTime)

Signal: JobPhoto created/deleted → GalleryItem auto-synced
```

---

## 💻 Code Files

### Core Logic
- `gallery/models.py` - Enhanced GalleryItem model
- `gallery/views.py` - Gallery page + filters + delete
- `gallery/signals.py` - Auto-sync from JobPhotos
- `gallery/admin.py` - Enhanced admin interface
- `gallery/apps.py` - Signal registration

### Templates
- `templates/gallery/gallery.html` - Public gallery (beautiful!)
- `templates/dashboard/gallery/dashboard_gallery_list.html` - Dashboard
- `templates/dashboard/gallery/dashboard_gallery_form.html` - Form (existing)

### Database
- `gallery/migrations/0002_auto_gallery_unified.py` - Migration (applied ✅)

---

## 🚀 Common Tasks

### Task: View Gallery
```
User → Visit /gallery/ → See all images
→ Use filters (service/source) → View full-size → Done ✅
```

### Task: Add Image (Admin)
```
Admin → /dashboard/gallery/add/ → Upload image
→ Fill title, service, suburb → Save → Image on /gallery/ ✅
```

### Task: Auto-Sync Job Photo
```
Employee completes booking → Upload job photos
→ Signal triggered automatically → GalleryItem created
→ Image on /gallery/ immediately ✅
```

### Task: Delete Image
**Option 1 (Public):** Staff clicks delete button → Confirms → AJAX delete ✅  
**Option 2 (Dashboard):** Staff clicks delete → Confirms → Redirects ✅  
**Option 3 (Admin):** Admin clicks delete → Confirms → Django delete ✅

---

## 🎨 Frontend

### Gallery Page (`/gallery/`)
```
┌─────────────────────────────────────┐
│  Hero Section (Gradient)            │
│  "Before & After Gallery"           │
│  [Get Quote] [Visit Resources]      │
└─────────────────────────────────────┘

┌─ Statistics ────────────────────────┐
│ [500+ Photos] [8 Services] [6 Sources]
└────────────────────────────────────┘

┌─ Filters ──────────────────────────┐
│ Service: [All ▼]  Source: [All ▼]  │
│ [Reset Filters]                    │
└────────────────────────────────────┘

┌────┬────┬────┐
│    │    │    │  ← Image Grid (responsive)
│    │    │    │     - Hover: scale + shadow
├────┼────┼────┤    - Badge: source colored
│    │    │    │     - Card: before/after
│    │    │    │     - Actions: View/Delete
└────┴────┴────┘

[Modal: Full-size image viewer]
```

### Dashboard Gallery (`/dashboard/gallery/`)
```
┌─────────────────────────────────────┐
│ [+ Add] [View Public] [← Dashboard] │
└─────────────────────────────────────┘

┌─ Stats ─────────────────────────────┐
│ [500 Photos] [8 Service Types] [6 Sources]
└────────────────────────────────────┘

┌────┬────┬────┐
│ 📷 │ 📷 │ 📷 │  ← Beautiful grid
│ ✏️ 🗑️ │ ✏️ 🗑️ │     - Thumbs
├────┼────┼────┤    - Metadata
│ 📷 │ 📷 │ 📷 │     - Edit/Delete
│ ✏️ 🗑️ │ ✏️ 🗑️ │
└────┴────┴────┘
```

---

## 🔐 Security

| Feature | Implementation |
|---------|----------------|
| Delete Protection | Only staff/superuser |
| CSRF Protection | Django middleware |
| Database FK | Cascade delete |
| Signal Safety | Try/except handling |

---

## ⚡ Performance

- **Lazy loading:** Images load on scroll
- **Responsive:** Mobile-first design
- **Grid layout:** CSS Grid for efficiency
- **Indexed fields:** source, featured, created_at
- **Select related:** Admin loads related objects

---

## 🐛 Debug Checklist

Images not showing?
- [ ] Is `featured=True`?
- [ ] Do files exist in `media/` folder?
- [ ] Is `MEDIA_URL` configured?
- [ ] Check browser console for 404s

Auto-sync not working?
- [ ] Is `gallery.signals` imported in `apps.py`?
- [ ] Did migration apply? (`manage.py migrate gallery`)
- [ ] Is `photo_type` 'before' or 'after'?
- [ ] Check database for records

Delete not working?
- [ ] Is user staff? (`user.is_staff=True`)
- [ ] CSRF token included in AJAX?
- [ ] Browser console errors?
- [ ] Is database writable?

---

## 📚 Documentation Files

- `GALLERY_UNIFIED_SYSTEM.md` - Complete documentation
- `GALLERY_IMPLEMENTATION.md` - Implementation details
- `gallery/models.py` - Code comments
- `gallery/signals.py` - Signal documentation
- `gallery/admin.py` - Admin configuration

---

## 🎯 Future Enhancements

Priority 1 (Easy):
- [ ] Pagination for large galleries
- [ ] Search functionality (title/suburb)
- [ ] Export to CSV (admin)
- [ ] Bulk upload

Priority 2 (Medium):
- [ ] Before/after slider (interactive)
- [ ] Image tags/categories
- [ ] Gallery analytics
- [ ] Social sharing

Priority 3 (Advanced):
- [ ] AI image tagging
- [ ] Customer testimonial linking
- [ ] Image editing tools
- [ ] Watermarking

---

## 📞 Support

**Issue Type** → **Solution**

Django Error?
→ Run `./venv/bin/python manage.py check`

Images missing?
→ Check `featured=True` and media files exist

Auto-sync failing?
→ Verify signals registered in apps.py

Delete not working?
→ Check user.is_staff and CSRF token

Performance slow?
→ Resize images, enable caching

---

## ✅ Deployment Checklist

Before going live:
- [ ] Run migrations: `manage.py migrate gallery`
- [ ] Collect static: `manage.py collectstatic`
- [ ] Test gallery page: `/gallery/`
- [ ] Test dashboard: `/dashboard/gallery/`
- [ ] Test admin: `/admin/gallery/`
- [ ] Test delete buttons (all 3 interfaces)
- [ ] Test filters (service + source)
- [ ] Test responsive design (mobile)
- [ ] Test auto-sync (create job photo)
- [ ] Verify media storage working
- [ ] Set DEBUG=False and test
- [ ] Monitor 404s for missing images

---

## 🎉 Quick Start

1. **View:** Visit `/gallery/` to see the beauty
2. **Add:** Go to `/dashboard/gallery/add/` to upload
3. **Manage:** Dashboard at `/dashboard/gallery/`
4. **Admin:** Advanced control at `/admin/gallery/`
5. **Auto:** Job photos auto-sync → just upload!

**Ready?** You're all set! 🚀

---

**Version:** 1.0  
**Date:** July 24, 2026  
**Status:** ✅ Production Ready  
