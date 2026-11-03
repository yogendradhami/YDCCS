# YDCCS Service-Page Architecture Audit

Audit completed before implementation on 3 November 2026.

## Inventory

- **Active database services:** 13.
- **SEO definitions:** 23.
- **FAQ profiles:** 23.
- **Service-specific Why Choose profiles:** 23.
- **Distinct currently addressable base service pages:** 24: 12 database services overlap definitions, 11 definitions have no active database row, and `standard-bathroom-cleaning-adelaide` exists only in the database.
- All 13 active database records have a name, description, overview, introduction, process, inclusions, and hero image. All have package arrays, but not all package entries are usable.
- The 23 curated FAQ profiles contain 5 questions each, except `kitchen-deep-cleaning`, which contains 6. Their 116 questions are distinct across the profile set.
- The 23 definitions have unique explicit meta titles except `kitchen-deep-cleaning`, whose title block can still generate a title fallback. No duplicate meta descriptions were found.

The database inventory and route-backed services were inspected without modifying database content. Service detail URLs use the existing `service_page` route and `/services/<slug>/` canonical pattern.

## Findings

### Data resolution and completeness

1. `_service_context_from_model` treats populated database fields as the complete service profile rather than applying per-field fallback to `SERVICE_DEFINITIONS`. This is especially consequential for FAQs and packages.
2. The database `introduction` field is populated on all active records but is not included in the model-derived template context.
3. The model exposes `process`, but model-derived context reads the nonexistent `process_steps` attribute, so stored process steps are not rendered.
4. Database FAQs range from 2 to 7 entries. Builders cleaning, carpet cleaning, deep cleaning, spring cleaning and post-construction cleaning have fewer than five; their more complete curated FAQ profiles are suppressed by the current “database value or curated fallback” selection.
5. Five package entries on carpet cleaning lack both names and descriptions. Three house-cleaning and two spring-cleaning package entries lack prices. Empty package cards and a blank “starting price” can therefore render.
6. Twelve database description/overview pairs differ from their SEO-definition counterparts. These are treated as existing admin-managed content, not presumed errors; changes should preserve nonblank database content.
7. `standard-bathroom-cleaning` is the only active database service without a matching SEO, FAQ or Why Choose profile. Its public page currently relies on generic fallbacks.
8. The `kitchen-deep-cleaning` SEO definition has no explicit `meta_title`; a generated title fallback is available.

### Catalog, URL and link coverage

1. The service directory is populated from active database records only. It therefore omits the 11 definition-only service pages already resolvable by the service view.
2. The detail sitemap and generated local-service sitemap likewise derive service slugs from active database records, omitting those same definition-only pages.
3. The related-service builder uses token-overlap fallback after curated relationships. This can add weakly related links; curated relationships should remain the source of related targets, with every target restricted to a known active or defined canonical page.
4. Content overlaps requiring distinct search intent include end-of-lease/bond/exit/move-out/inspection cleaning; carpet/carpet-steam cleaning; bathroom/standard-bathroom cleaning; kitchen/kitchen-deep cleaning; and builders/post-construction cleaning. Existing URLs should remain intact; no redirects or consolidations are justified by this audit alone.

### Rendering and SEO

1. The view computes `why_choose_section` from the exact service profile, but `service_detail.html` suppresses the base Why Choose partial and renders six generic hardcoded cards instead.
2. The service page has one visible FAQ renderer. The base template supplies the FAQ schema; the service template supplies Service and BreadcrumbList JSON-LD. The latter embeds another LocalBusiness object despite the site-wide LocalBusiness entity, so the provider should reference the existing entity by `@id`.
3. The service hero image is marked lazy-loaded even though it is the primary above-the-fold image.
4. The template includes unsupported generic claims such as a satisfaction guarantee, customer counts, response-time claims, insurance, and specific equipment. These should not be repeated unless substantiated by service data.
5. The standalone service-page template currently has no visible breadcrumb navigation.

### Quote and booking integration

The service detail page includes one shared quick-quote form. Its existing form action, POST handling, CSRF field, workflow/idempotency token, AJAX response path, reCAPTCHA, and separate property-photo upload workflow are present. The page view selects the quote service from the normalized service slug and location from the URL. The audit found no reason to replace the form or change its backend integration.

## Implementation guardrails

- Keep all existing service URLs and canonical behavior.
- Preserve nonblank admin-managed fields and package information; use curated values only as field-level fallbacks.
- Filter incomplete package entries instead of emitting empty cards or invented prices.
- Do not add migrations or write service data to the database.
- Use the existing service, guide, blog, case-study, FAQ, and Why Choose routes/data only.
- Validate the changed behavior with focused tests and the project checks.

## Implementation completed

- The service directory now includes active database services and definition-only services without changing their existing detail URLs.
- Service context now uses field-level curated fallbacks, preserves populated model content, reads the model's `process` field, merges FAQs without duplicate questions, and filters incomplete package entries.
- Related-service links now use known curated relationships and validated targets; each currently defined service page exposes three to six related services.
- Relevant existing guide and published blog links, the Adelaide A–Z directory, and a matching controlled suburb page are rendered as crawlable links where available.
- The service quote selector covers the defined services and maps bathroom cleaning to the existing standard-bathroom quote choice. Existing submission and upload workflows are unchanged.
- Service pages now render visible breadcrumbs and the service-specific Why Choose section, prioritize the hero image, reference the existing LocalBusiness schema entity, and omit unsupported generic claims.
- The service detail and local-service sitemaps now include definition-only service pages; the suburb sitemap includes controlled pages from both existing local-area registries.
- No model changes, migrations, redirects, or service data edits were made.

## Validation

- `python manage.py check`: passed.
- Focused service-page and quote-choice tests: passed.
- `git diff --check`: passed.
- Full suite using isolated SQLite settings: 502 tests run; 501 passed and one unrelated pre-existing dashboard role-editor assertion failed because the response did not contain “Use least privilege.”
