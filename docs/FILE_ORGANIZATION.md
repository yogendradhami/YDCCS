# YD Cleaning - File Organization Guide

## Repository Structure

### Root Level (Essential Project Files Only)
```
/
├── manage.py                 # Django management CLI
├── Dockerfile                # Docker build configuration
├── Makefile                  # Build and run shortcuts
├── README.md                 # Main project documentation
├── db.sqlite3                # Development SQLite database
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Python project metadata
├── docker-compose.yml        # Production Docker Compose
├── docker-compose.dev.yml    # Development Docker Compose
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
└── .env (untracked)          # Local development secrets
```

### Django Project Structure
```
/ydcleaning/                  # Main Django project package
├── settings.py               # Django configuration
├── urls.py                   # URL routing
├── wsgi.py                   # WSGI application entry
└── asgi.py                   # ASGI application entry

/templates/                   # Project-wide templates
├── base.html                 # Main layout template
├── dashboard_base.html       # Dashboard layout
├── layouts/                  # Layout variants
├── includes/                 # Reusable template parts
├── pages/                    # Static pages (about, contact, etc.)
├── partials/                 # UI component partials
├── services/                 # Service listing templates
└── [app_name]/               # App-specific templates

/static/                      # Static assets (CSS, JS, images)
├── css/                      # Stylesheets
├── js/                       # JavaScript files
└── images/                   # Static images

/media/                       # User-uploaded files
```

### Django Apps (Located at Root)
Each app follows Django's standard structure:
```
/[app_name]/
├── models.py                 # Database models
├── views.py                  # Request handlers
├── urls.py                   # App URL routing
├── forms.py                  # Django forms
├── admin.py                  # Django admin customization
├── tests.py                  # Unit tests
├── apps.py                   # App configuration
├── migrations/               # Database migrations
└── templates/[app_name]/     # App-specific templates
```

### Installed Apps
- **attendance** - Employee attendance tracking
- **blog** - Blog posts and content
- **bookings** - Job and cleaning bookings
- **contracts** - Customer contracts management
- **core** - Core utilities, SEO, sitemaps
- **customers** - Customer management
- **dashboard** - Administrative dashboard
- **employees** - Employee management and portal
- **expenses** - Expense tracking
- **gallery** - Image gallery management
- **google_reviews** - Google review integration
- **invoices** - Invoice generation and management
- **leave_management** - Employee leave requests
- **locations** - Service location management
- **notifications** - User notifications
- **payroll** - Payroll management
- **portal** - Customer self-service portal
- **quotes** - Quote request management
- **reports** - Report generation
- **reviews** - Customer reviews management
- **rosters** - Staff roster scheduling
- **services** - Cleaning services definition
- **signatures** - Digital signature handling
- **support** - Customer support tickets
- **ydcleaning** - Main Django project package

### Documentation Structure (docs/)
```
/docs/
├── ENVIRONMENT.md            # Environment configuration guide
├── FILE_ORGANIZATION.md      # This file
├── notes/                    # Implementation notes and checklists
│   ├── BLOG_IMAGE_*.md
│   ├── COMPLETION_*.md
│   ├── DESIGN_*.md
│   ├── IMPLEMENTATION_*.md
│   ├── PERFORMANCE_*.md
│   ├── STRUCTURE_GUIDE.md
│   └── [other_documentation]
├── reports/                  # Test and audit reports
│   ├── 127.0.0.1_*.report.html
│   └── chromewebdata_*.report.html
└── lighthouse/               # Lighthouse performance reports
    ├── lighthouse-report-*.json
    └── lighthouse_*.json
```

### Infrastructure Files
```
/scripts/                     # Build and deployment scripts
/.github/                     # GitHub configuration
├── workflows/                # GitHub Actions CI/CD
│   └── ci.yml                # Continuous integration
└── copilot-instructions.md   # AI assistant configuration
```

### Virtual Environment & Caching
```
/venv/                        # Python virtual environment (not committed)
/__pycache__/                 # Python cache files (not committed)
/staticfiles/                 # Collected static files (generated, not committed)
```

## File Management Best Practices

### What's Tracked in Git
- ✓ Source code (Python, HTML, CSS, JS)
- ✓ Configuration templates (.env.example)
- ✓ Database migrations
- ✓ Documentation and guides
- ✓ Docker configuration
- ✓ Requirements and dependencies

### What's NOT Tracked (in .gitignore)
- ✗ Virtual environment (`venv/`)
- ✗ Cache files (`__pycache__/`, `*.pyc`)
- ✗ Local environment variables (`.env`, `.env.local`)
- ✗ Database files (`db.sqlite3`)
- ✗ User uploads (`media/`)
- ✗ Collected static files (`staticfiles/`)
- ✗ Test and lighthouse reports
- ✗ IDE configuration (`.vscode/`, `.idea/`)
- ✗ System files (`.DS_Store`)

### Adding New Files
1. **Source Code** → Place in appropriate app or at root with descriptive name
2. **Documentation** → Save to `docs/notes/` with clear naming
3. **Tests/Reports** → Save to `docs/reports/` or `docs/lighthouse/`
4. **Static Assets** → Save to `static/` organized by type (css/, js/, images/)
5. **User Uploads** → Automatically handled in `media/` directory

### Template Organization
- Root templates in `templates/`
- App-specific templates in `templates/[app_name]/`
- Reusable partials in `templates/partials/` or `templates/includes/`
- Shared components in `templates/shared/`

## Cleanup Actions Performed
- ✓ Moved 32+ report HTML files to `docs/reports/`
- ✓ Moved 11 Lighthouse JSON files to `docs/lighthouse/`
- ✓ Moved 20+ implementation notes to `docs/notes/`
- ✓ Moved temporary marker files to `docs/notes/`
- ✓ Updated `.gitignore` to exclude test artifacts
- ✓ Removed 114 exact duplicate root-level templates
- ✓ Removed 2 unused template duplicates (layouts/base.html, service_detail.html)
- ✓ Resolved Git merge conflicts in 3 files

## Key Statistics
- **Django Apps:** 24 installed applications
- **Templates:** 100+ template files organized hierarchically
- **Documentation Files:** 30+ guides and implementation notes (archived in docs/)
- **Static Assets:** CSS, JavaScript, and images organized in static/
- **Core Project Files:** 4 essential files at root level
