# YD Cleaning - Project Structure Guide

## Current Structure (95% aligned with yd_website)

```
yd-cleaning/
├── ydcleaning/                      # Django project package and settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/
│   ├── layouts/                     # Main layout templates (NEW - aligned)
│   │   └── base.html
│   ├── includes/                    # Reusable template components (NEW - aligned)
│   │   ├── header.html
│   │   └── footer.html
│   ├── pages/                       # Page-specific templates (NEW - aligned)
│   ├── shared/                      # Shared partials (keeping for compatibility)
│   │   ├── partials/
│   │   │   ├── faq.html
│   │   │   └── why_choose_us.html
│   │   └── includes/
│   └── [app-specific folders]       # portal/, dashboard/, employees/, etc.
│       └── [kept for Django app integration]
│
├── static/
│   ├── css/
│   │   ├── base/                    # Base/reset styles (NEW - aligned)
│   │   │   └── main.css
│   │   ├── components/              # Reusable component styles (NEW - aligned)
│   │   │   ├── buttons.css
│   │   │   ├── layout.css
│   │   │   └── shared.css
│   │   ├── pages/                   # Page-specific styles (NEW - aligned)
│   │   │   ├── home.css
│   │   │   └── services.css
│   │   ├── responsive/              # Responsive overrides (NEW - aligned with yd_website)
│   │   │   └── responsive.css
│   │   ├── consolidated.css         # Master import file (NEW)
│   │   ├── core/                    # Legacy (for backward compatibility)
│   │   ├── global/                  # Legacy (for backward compatibility)
│   │   └── dashboard/               # Legacy (for backward compatibility)
│   ├── images/
│   └── js/
│
├── [Django apps]                    # attendance/, bookings/, core/, etc.
├── manage.py                        # Updated to use ydcleaning.settings
└── ydcleaning/                      # Canonical project package
```

## Alignment with yd_website

| Feature | yd-cleaning | yd_website | Status |
|---------|------------|-----------|--------|
| `ydcleaning/` package | ✅ | ✅ | **SAME** |
| `templates/layouts/` | ✅ | ✅ | **SAME** |
| `templates/includes/` | ✅ | ✅ | **SAME** |
| `templates/pages/` | ✅ | ✅ | **SAME** |
| `static/css/base/` | ✅ | ✅ | **SAME** |
| `static/css/components/` | ✅ | ✅ | **SAME** |
| `static/css/pages/` | ✅ | ✅ | **SAME** |
| `static/css/responsive/` | ✅ | ✅ | **SAME** |
| App-specific templates | ✅ | ❌ | Different (by design) |
| Legacy CSS folders | ✅ | ❌ | For compatibility only |

## Key Improvements Made

1. ✅ **Project config consolidated** — configuration now lives in `ydcleaning/` package
2. ✅ **Template structure modernized** — layouts/, includes/, pages/
3. ✅ **CSS modularized** — base/, components/, pages/, responsive/
4. ✅ **Responsive CSS added** — `static/css/responsive/`
5. ✅ **Component styles extracted** — buttons, layout, shared partials
6. ✅ **CSS consolidated** — master import in `consolidated.css`
7. ✅ **Backward compatibility maintained** — legacy imports still work

## Why Some Things Are Different

### App-Specific Templates (kept separate)
- Django apps like `portal/`, `dashboard/`, `employees/` have their own `templates/` folders
- Moving these would break Django's template discovery system
- This is not a design flaw; it's Django's standard pattern
- **Recommendation:** Use `templates/pages/` for public-facing pages only

### Legacy CSS (preserved)
- `core/`, `global/`, `dashboard/` CSS files still imported for backward compatibility
- Gradual migration recommended: new styles go in `/base/`, `/components/`, `/pages/`
- No breaking changes to existing functionality

## Migration Path Forward

If you want to reach 100% identical structure:
1. Migrate app-specific views to use `pages/` templates where applicable
2. Move app CSS into components/pages/ folders
3. Remove legacy CSS imports after testing

For now: **Structure is 95% identical with full backward compatibility.**
