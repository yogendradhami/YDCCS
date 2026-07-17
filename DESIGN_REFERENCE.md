# Modern Design System - Quick Reference Guide

## 🎨 Color Palette

### Primary Colors
```css
--primary: #2563eb;           /* Modern Blue - Main brand color */
--primary-dark: #1e40af;      /* Darker blue for hover states */
--primary-light: #3b82f6;     /* Lighter blue for backgrounds */
```

### Secondary & Accent
```css
--secondary: #10b981;         /* Fresh Green - Success, accents */
--accent: #f59e0b;            /* Warm Amber - Highlights, warnings */
--accent-light: #fbbf24;      /* Lighter amber for backgrounds */
```

### Status Colors
```css
--success: #10b981;           /* Green - Success messages */
--warning: #f59e0b;           /* Amber - Warning messages */
--danger: #ef4444;            /* Red - Error messages */
--info: #3b82f6;              /* Blue - Info messages */
```

### Neutral Colors
```css
--dark: #0f172a;              /* Almost black - Text */
--dark-gray: #1f2937;         /* Dark gray - Secondary text */
--gray: #6b7280;              /* Medium gray - Body text */
--light-gray: #e5e7eb;        /* Light gray - Borders */
--lighter-gray: #f3f4f6;      /* Very light - Backgrounds */
--white: #ffffff;             /* White - Primary background */
```

---

## 📏 Spacing System

```css
--spacing-xs: 4px;            /* Extra small padding */
--spacing-sm: 8px;            /* Small padding */
--spacing-md: 16px;           /* Medium padding (default) */
--spacing-lg: 24px;           /* Large padding */
--spacing-xl: 32px;           /* Extra large padding */
--spacing-2xl: 48px;          /* 2x large padding */
--spacing-3xl: 64px;          /* 3x large padding */
```

**Usage Pattern**: 
- Card padding: `--spacing-lg` (24px)
- Section spacing: `--spacing-3xl` (64px) top/bottom
- Gaps between elements: `--spacing-md` to `--spacing-lg`

---

## 🔘 Border Radius

```css
--radius-sm: 4px;             /* Small rounded corners */
--radius-md: 8px;             /* Medium rounded corners */
--radius-lg: 12px;            /* Large rounded corners (cards) */
--radius-xl: 16px;            /* Extra large rounded corners */
--radius-full: 9999px;        /* Fully rounded (pills, circles) */
```

**Usage Pattern**:
- Cards: `--radius-lg`
- Buttons: `--radius-lg`
- Form inputs: `--radius-md`
- Badges: `--radius-full`

---

## 🌑 Shadow System

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
```

**Usage Pattern**:
- Hover state: `var(--shadow-lg)`
- Default card: `var(--shadow-md)`
- Prominent elements: `var(--shadow-xl)`

---

## ⏱️ Transitions

```css
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

**Standard timing**:
- Duration: 0.3s
- Easing: cubic-bezier(0.4, 0, 0.2, 1) (smooth acceleration/deceleration)
- Applied to: color, background, transform, box-shadow, border

**Example**:
```css
.card {
    transition: var(--transition);
}

.card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}
```

---

## 🎯 Common Patterns

### Hero Section
```css
.hero {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    color: var(--white);
    padding: 100px 0;
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
}
```

### Card Component
```css
.card {
    background: var(--white);
    border: 2px solid var(--light-gray);
    border-radius: var(--radius-lg);
    padding: 28px;
    box-shadow: var(--shadow-md);
    transition: var(--transition);
}

.card:hover {
    border-color: var(--primary);
    box-shadow: var(--shadow-lg);
    transform: translateY(-6px);
}
```

### Button Component
```css
.btn-fill {
    background: var(--primary);
    color: var(--white);
    padding: 14px 28px;
    border-radius: var(--radius-lg);
    font-weight: 600;
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
    transition: var(--transition);
}

.btn-fill:hover {
    background: var(--primary-dark);
    box-shadow: 0 8px 25px rgba(37, 99, 235, 0.4);
    transform: translateY(-2px);
}
```

### Grid Layout
```css
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 30px;
}

@media (max-width: 768px) {
    .grid {
        grid-template-columns: 1fr;
    }
}
```

---

## 📐 Typography

### Heading Sizes
- H1: 48px (hero title)
- H2: 42px (section title)
- H3: 24px (card title)
- H4: 18px (small title)

### Body Text
- Large: 18px (intro text)
- Regular: 16px (default body)
- Small: 15px (description)
- Tiny: 13px-14px (meta info)

### Font Weight
- Bold/Headings: 700-800 (font-weight: bold, --weight: 700+)
- Semi-Bold: 600 (button text)
- Regular: 400-500 (body text)

---

## 🎬 Animation Effects

### Slide In Animation
```css
@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

### Float Animation
```css
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(30px); }
}
```

### Slide Down (Expandable)
```css
@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

---

## 📱 Responsive Breakpoints

```css
/* Desktop - 1024px and above (no specific media query) */
/* Tablet - 768px to 1023px */
@media (max-width: 1024px) {
    /* Tablet adjustments */
}

/* Mobile - below 768px */
@media (max-width: 768px) {
    /* Mobile adjustments */
}
```

---

## 💡 Usage Tips

### 1. Always Use CSS Variables
❌ **DON'T**:
```css
color: #2563eb;
```

✅ **DO**:
```css
color: var(--primary);
```

### 2. Consistent Spacing
❌ **DON'T**:
```css
padding: 15px 20px 18px 16px;
```

✅ **DO**:
```css
padding: var(--spacing-lg);
```

### 3. Use Transitions
❌ **DON'T**:
```css
transition: all 0.2s linear;
```

✅ **DO**:
```css
transition: var(--transition);
```

### 4. Hover States
Always include hover states:
```css
.element {
    transition: var(--transition);
}

.element:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}
```

### 5. Mobile First
Write mobile styles first, then expand:
```css
.grid {
    grid-template-columns: 1fr;  /* Mobile */
}

@media (max-width: 768px) {
    .grid {
        grid-template-columns: repeat(3, 1fr);  /* Desktop */
    }
}
```

---

## 🎨 Gradient Presets

### Main Gradient (Blue to Dark)
```css
background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
```

### Light Gradient (Background)
```css
background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
```

### Text Gradient
```css
background: linear-gradient(135deg, var(--primary), var(--secondary));
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

---

## 🔍 Helpful Snippets

### Image Zoom on Hover
```css
.image {
    overflow: hidden;
    border-radius: var(--radius-lg);
}

.image:hover {
    transform: scale(1.1);
}
```

### Quote Mark Overlay
```css
element::before {
    content: '"';
    position: absolute;
    font-size: 120px;
    color: rgba(37, 99, 235, 0.1);
    line-height: 1;
    z-index: 0;
}
```

### Expandable Item with Icon Rotation
```css
.toggle {
    transition: transform 0.3s ease;
}

.item.open .toggle {
    transform: rotate(180deg);
}
```

---

## 📋 File Structure

```
static/css/
├── base/variables.css    ← Design system (update colors here)
├── base/main.css         ← Base styles
├── components/buttons.css ← Component styles
├── components/layout.css
├── components/shared.css
├── pages/home.css        ← Page-specific styles
├── pages/services.css
├── pages/contact.css
├── pages/gallery.css
├── pages/blog.css
├── pages/reviews.css
├── pages/locations.css
├── responsive/responsive.css
└── consolidated.css      ← Master import file
```

---

## 🚀 Quick Start for New Components

1. **Name your class** with descriptive name
2. **Use CSS variables** for colors, spacing, shadows
3. **Add transitions** for interactivity
4. **Include hover states** for good UX
5. **Test mobile** with media queries
6. **Import in consolidated.css** if new file

Example:
```css
/* pages/newpage.css */
.new-component {
    background: var(--white);
    padding: var(--spacing-lg);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    transition: var(--transition);
}

.new-component:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}

@media (max-width: 768px) {
    .new-component {
        padding: var(--spacing-md);
    }
}
```

---

## ✨ That's it!

You now have a beautiful, consistent, modern design system that's easy to maintain and extend! 🎉
