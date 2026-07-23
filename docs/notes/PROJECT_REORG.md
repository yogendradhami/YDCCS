# YD Cleaning Project Reorganization

This project has been updated with a cleaner structure while preserving existing application code and templates.

## What changed

- Removed the legacy `config/` package and kept the canonical `ydcleaning/` project package.
- Updated `manage.py` to use `ydcleaning.settings`.
- Created a more modern template organization pattern:
  - `templates/layouts/`
  - `templates/includes/`
  - `templates/pages/`
- Created CSS layout directories for future reorganization:
  - `static/css/base/`
  - `static/css/components/`
  - `static/css/pages/`

## Why this is better

- `ydcleaning/` now contains the active project configuration and URL routing.
- `templates/layouts/` and `templates/includes/` make it easier to find shared layout files.
- `templates/pages/` groups page-level templates in a more scalable way.
- `static/css/*` directories let you separate base styles, component styles, and page-specific styles.

## Notes

- The existing `ydcleaning/` package is still preserved for compatibility.
- Active Django execution now uses `ydcleaning/settings.py` through `manage.py`.
- No application logic was changed; the code behavior remains the same.

## Next steps

- Gradually move reusable templates into `templates/layouts/` and `templates/includes/`.
- Move page-specific templates into `templates/pages/` as a second phase.
- Refactor CSS into `static/css/base/`, `static/css/components/`, and `static/css/pages/` over time.
