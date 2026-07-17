# YD Commercial Cleaning - Navigation & URL Structure

## Main Navigation Hierarchy

```
Home (/)
├── About (/about/)
├── Pricing (/pricing/)
├── Team (/team/)
├── Services (/services/)
│   ├── House Cleaning (/services/house-cleaning-adelaide/)
│   ├── Commercial Cleaning (/services/commercial-cleaning-adelaide/)
│   ├── Office Cleaning (/services/office-cleaning/)
│   ├── Spring Cleaning (/services/spring-cleaning/)
│   ├── Oven Cleaning (/services/oven-cleaning/)
│   ├── Bathroom Cleaning (/services/bathroom-cleaning/)
│   ├── Bond Cleaning (/services/bond-cleaning/)
│   ├── Exit Cleaning (/services/exit-cleaning/)
│   ├── Carpet Cleaning (/services/carpet-cleaning/)
│   ├── Window Cleaning (/services/window-cleaning-adelaide/)
│   └── Post Construction (/services/post-construction-cleaning-adelaide/)
├── Gallery (/gallery/)
├── Contact (/contact/)
├── Resources (dropdown)
│   ├── Local Services (/local/)
│   ├── Blog (/blog/)
│   ├── Guides (/guides/)
│   ├── Case Studies (/case-studies/)
│   └── FAQ (/faq/)
└── Portals (dropdown)
    ├── Customer Portal (/portal/login/)
    ├── Employee Portal (/employee/login/)
    └── Admin Dashboard (/dashboard/)
```

## New URLs Added

### Main Pages
| URL | Page | Status |
|-----|------|--------|
| `/about/` | About Company | ✅ NEW |
| `/pricing/` | Service Pricing | ✅ NEW |
| `/team/` | Team Members | ✅ NEW |

### New Service URLs
| URL | Service | Status |
|-----|---------|--------|
| `/services/spring-cleaning/` | Spring Cleaning | ✅ NEW |
| `/services/oven-cleaning/` | Oven Cleaning | ✅ NEW |
| `/services/exit-cleaning/` | Exit Cleaning | ✅ NEW |
| `/services/carpet-cleaning/` | Carpet Cleaning | ✅ NEW |
| `/services/office-cleaning/` | Office Cleaning | ✅ NEW (Updated) |
| `/services/bathroom-cleaning/` | Bathroom Cleaning | ✅ EXISTING |
| `/services/bond-cleaning/` | Bond Cleaning | ✅ EXISTING |

## Removed from Navigation
- ❌ `/reviews/` - Reviews link removed from main menu

## Services Mega-Menu Layout

### Desktop View (11 Cards)
```
┌─────────────────────────────────────────────────────┐
│                   SERVICES DROPDOWN                  │
├──────────────┬──────────────┬──────────────┬─────────┤
│ 🏠 Home      │ 🏢 Commer-  │ 🧹 Office    │ 🌸 Spri │
│ Cleaning     │ cial Clean   │ Cleaning     │ ng Clea │
├──────────────┼──────────────┼──────────────┼─────────┤
│ 🍳 Oven      │ 🚿 Bathroom  │ 🔑 Bond      │ 🚪 Exit │
│ Cleaning     │ Cleaning     │ Cleaning     │ Clean   │
├──────────────┼──────────────┼──────────────┼─────────┤
│ 🏘️ Carpet    │ 🪟 Window    │ 🚧 Post      │         │
│ Cleaning     │ Cleaning     │ Construction │         │
├──────────────┴──────────────┴──────────────┴─────────┤
│ Get Consultation Button                              │
└──────────────────────────────────────────────────────┘
```

### Mobile View
- Dropdown toggle
- Searchable services list
- Quick access to all 11 services
- Get consultation button

## Search Index

### Indexed Pages (Searchable)
- Home
- About Us ✅ NEW
- Pricing ✅ NEW
- Team ✅ NEW
- All 19 Services ✅ (including 7 new)
- Gallery
- Contact
- Blog
- Portals

### Search Results Include

**New Pages:**
- About Us
- Pricing
- Team

**New Services:**
- Office Cleaning
- Spring Cleaning
- Oven Cleaning
- Standard Bathroom Cleaning
- Bond Cleaning
- Exit Cleaning
- Carpet Cleaning

## Page Structure

### About Page (/about/)
```
Hero Section
    ↓
Our Story Section
    ↓
Core Values (4 cards)
    ↓
Why Choose Us (6 cards)
    ↓
Customer Testimonials (3 cards)
    ↓
FAQ Section (6 items)
    ↓
CTA Section
    ↓
Footer
```

### Pricing Page (/pricing/)
```
Hero Section
    ↓
Intro Text
    ↓
Pricing Cards (9 cards)
    - Residential Cleaning
    - Commercial Cleaning
    - Bond Cleaning
    - Spring Cleaning
    - Deep Cleaning
    - Oven Cleaning
    - Carpet Cleaning
    - Bathroom Cleaning
    - Window Cleaning
    ↓
Why Choose Our Pricing
    ↓
CTA Section
    ↓
Footer
```

### Team Page (/team/)
```
Hero Section
    ↓
Team Intro
    ↓
Team Members Grid (6 cards)
    ↓
Team Values Section (6 items)
    ↓
Team Culture Section (4 features)
    ↓
Careers Section (with benefits)
    ↓
CTA Section
    ↓
Footer
```

### Service Detail Pages (/services/[service-name]/)
```
Hero Section
    ↓
Service Overview
    ↓
What's Included (checkmarks)
    ↓
Service Packages (pricing cards)
    ↓
Why Choose Us (6 reasons)
    ↓
Service Areas (Adelaide suburbs)
    ↓
CTA Section
    ↓
Footer
```

## URL Patterns Explained

### Service URLs
All services follow the pattern: `/services/{service-slug}/`

**Examples:**
- `/services/spring-cleaning/`
- `/services/carpet-cleaning/`
- `/services/office-cleaning/`

### Dynamic Service Routing
The `service_page_slug_pattern` regex handles:
- All service definitions from SERVICE_DEFINITIONS
- Multiple location aliases (adelaide, prospect, etc.)
- Custom URL patterns

### View Mapping
```python
# URL → View
/about/ → about()
/pricing/ → pricing()
/team/ → team()
/services/{slug}/ → service_page()
```

## Navigation Links on Each Page

### About Page Links
- Work With Us → /contact/
- About Services → /services/
- View Pricing → /pricing/
- Meet Team → /team/

### Pricing Page Links
- Get Your Quote → /contact/
- View Services → /services/
- Book Now → /#quote
- Back to Home → /

### Team Page Links
- Book a Cleaning → /contact/
- View Pricing → /pricing/
- Contact Us → /contact/

### Service Pages Links
- Get Quote → /contact/
- Quick Quote → /#quote
- Back to Services → /services/
- Related Services → (other services)

## Breadcrumb Navigation

### About Page
Home > About

### Pricing Page
Home > Pricing

### Team Page
Home > Team

### Service Pages
Home > Services > [Service Name]

## Mobile Navigation

### Header Menu Toggle (Hamburger)
- Home
- About
- Pricing
- Team
- Services (with submenu)
- Gallery
- Contact
- Resources (with submenu)
- Portals (with submenu)

### Mobile Search
- Search input field
- Quick access to popular pages
- Service search suggestions

## Analytics Tracking Points

### Page Tracking
- `/about/` - About page views
- `/pricing/` - Pricing interest
- `/team/` - Team interest
- `/services/spring-cleaning/` - Service interest
- (etc. for all new services)

### User Actions
- "About" link clicks
- "Pricing" link clicks
- "Team" link clicks
- Service card clicks
- Pricing card clicks
- CTA button clicks

## SEO Configuration

### Meta Tags Set
- `<title>` - Page title with keyword
- `<description>` - Meta description
- `<keywords>` - Relevant keywords
- `og:` tags - Social sharing

### Robots.txt
- `/about/` - Indexed
- `/pricing/` - Indexed
- `/team/` - Indexed
- All service pages - Indexed

### Sitemap.xml
- All new pages included
- All new services included
- Proper priority levels
- Update frequency set

## Version History

### Current Navigation (v2.0)
- ✅ Added 3 new main pages (About, Pricing, Team)
- ✅ Added 4 new services (Spring, Oven, Exit, Carpet Cleaning)
- ✅ Updated 3 existing services (Office, Bond, Bathroom Cleaning)
- ✅ Removed Reviews link
- ✅ Expanded services mega-menu (6 → 11 services)
- ✅ Updated search functionality

### Previous Navigation (v1.0)
- Home, Services, Gallery, Contact, Resources, Portals
- Reviews link
- 6 core services

## Mobile Responsiveness

### Breakpoints
- **Desktop**: 1200px+ (Multi-column layouts)
- **Tablet**: 768px - 1199px (2 columns)
- **Mobile**: < 768px (Single column)

### Adaptive Features
- Hamburger menu on mobile
- Single-column card layouts on mobile
- Touch-friendly button sizes (44x44px minimum)
- Font size adjustments for readability
- Proper spacing for thumb reach

## Performance Optimization

### Lazy Loading
- Images load on scroll
- Service images load asynchronously
- Team member images deferred

### Asset Optimization
- CSS files optimized and minified
- JS files optimized
- Images compressed
- Caching headers set

## Security Notes

- All URLs follow URL routing security patterns
- No sensitive data in URLs
- Form submissions CSRF protected
- All external links have rel="noopener noreferrer"
- Mobile apps support AMP

## Accessibility

### WCAG 2.1 Compliance
- ✅ Proper heading hierarchy (H1, H2, H3)
- ✅ Image alt text provided
- ✅ Color contrast ratios meet standards
- ✅ Keyboard navigation supported
- ✅ Screen reader friendly
- ✅ Form labels associated
- ✅ Focus indicators visible

---

**Last Updated:** July 12, 2026
**Version:** 2.0
**Status:** ✅ Production Ready
