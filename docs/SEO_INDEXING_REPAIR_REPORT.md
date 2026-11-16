# SEO Indexing Repair Report

**Prepared:** 16 November 2026  
**Preferred canonical origin:** `https://www.ydcleaning.com.au`  
**Status:** Application changes and regression coverage prepared; production revalidation is blocked on the Cloudflare hostname rule and the complete Google Search Console URL export.

## 1. Initial diagnosis

The initial worktree was clean on `main` at `2a62c65`. The attachment supplied 29 example affected URLs, but did not include the full 229-row Google Search Console export or production logs for the reported 5xx events.

The read-only production audit made 65 requests: all supplied examples, the requested smoke-test endpoints, a bounded sample of internal links, and a bounded sample of sitemap URLs. The live results were:

- 64 URLs returned HTTP 200 after redirects; `/local/adelaide/` returned 404.
- No 5xx response was reproduced among the audited URLs.
- Requests to the `www` hostname redirected to the apex hostname at Cloudflare. The homepage, `robots.txt`, and `sitemap.xml` all exhibited this behavior.
- The HTML canonical URLs in the sample used `www`, while the delivered pages ended at the apex host. The audit flagged 62 canonical mismatches.
- 22 sampled URLs associated with the sitemap used the apex host. The live sitemap contained 1,794 URL entries and included `/booking/`.
- Five supplied legacy service URLs took two redirects when requested on `www`: the Cloudflare hostname redirect followed by the application’s legacy service redirect.
- No broken link was found among the 19 sampled internal-link records.
- The report also flags duplicate titles and descriptions in the sampled pages. Service-location pages now use location-specific metadata in the application, but this needs a new live audit after deployment.

These are observations of the live deployment before the changes in this branch are deployed. They do not establish that Google has indexed or will index any page.

## 2. Root cause assessment

### Page with redirect

The redirect common to all tested `www` URLs is an edge-level Cloudflare redirect from `www.ydcleaning.com.au` to `ydcleaning.com.au`. That directly conflicts with the requested preferred `www` hostname and explains why otherwise valid pages can appear as redirecting URLs when Google crawls the `www` property.

Some individual legacy URLs also redirect to canonical service paths. Those are valid only when their final destination is a relevant HTTP 200 page. The full affected URL list is needed to classify all 205 entries individually.

### Redirect error

The supplied redirect-error examples currently reach HTTP 200 destinations; no loop was observed. Five `www` examples incur two hops because of the hostname redirect followed by a legacy-path redirect. Valid historical service aliases remain supported. Unknown root-level slugs no longer receive a speculative redirect to a service URL that would return 404.

### Server error (5xx)

No example returned a 5xx response during this audit. The historical server errors cannot be attributed to application code without the exact URLs, timestamps, and Render/application logs. The location view did have a separate data-quality defect: it treated the complete South Australian postcode dataset as Adelaide coverage and fabricated generic pages for distant or malformed entries. That defect is corrected without converting application failures into success responses.

## 3. Files changed

- [`ydcleaning/settings.py`](../ydcleaning/settings.py): load local environment files before reading `SITE_URL`, normalize the company domain to HTTPS `www`, and prevent production `SITE_URL` overrides from changing the canonical host.
- [`core/sitemaps.py`](../core/sitemaps.py): use the configured canonical host, omit booking, and include public static pages, published blog posts, and the existing guide pages.
- [`core/urls.py`](../core/urls.py): make `/local/adelaide/` the directory hub and permanently redirect the old `/local/index/adelaide/` hub path.
- [`core/views.py`](../core/views.py): limit local detail pages to curated areas or exact Adelaide-metro postcode records; return 404 for unsupported locations; avoid speculative redirects for unknown legacy service slugs; localize service-location descriptions and structured-data URLs.
- [`core/templatetags/seo_tags.py`](../core/templatetags/seo_tags.py): source organization and website structured-data URLs from `SITE_URL`.
- [`dashboard/context_processors.py`](../dashboard/context_processors.py): provide the configured site origin to shared metadata.
- [`templates/robots.txt`](../templates/robots.txt): point the sitemap directive at the configured canonical origin.
- [`templates/base.html`](../templates/base.html), [`templates/services/service_detail.html`](../templates/services/service_detail.html), [`templates/services/suburb_detail.html`](../templates/services/suburb_detail.html), [`templates/videos/cleaning_services_adelaide.html`](../templates/videos/cleaning_services_adelaide.html), [`templates/pages/blog_post_detail.html`](../templates/pages/blog_post_detail.html), and [`templates/pages/service-detail.html`](../templates/pages/service-detail.html): align structured data, canonical-related URLs, and location metadata with the configured canonical origin.
- [`templates/emails/application_update.html`](../templates/emails/application_update.html), [`templates/emails/application_update.txt`](../templates/emails/application_update.txt), and [`templates/emails/reviews/reports/cleaning_report_email.txt`](../templates/emails/reviews/reports/cleaning_report_email.txt): update hard-coded internal links to the preferred host.
- [`core/tests.py`](../core/tests.py), [`core/test_sitemaps.py`](../core/test_sitemaps.py), and [`core/test_seo_audit.py`](../core/test_seo_audit.py): add routing, location, sitemap, and audit-script regression coverage.
- [`scripts/seo_indexing_audit.py`](../scripts/seo_indexing_audit.py): add a read-only, bounded external audit utility.
- [`docs/SEO_INDEXING_URL_AUDIT.csv`](./SEO_INDEXING_URL_AUDIT.csv): save the bounded live baseline audit.

## 4. Redirect and location changes

- Valid service aliases continue redirecting to their relevant service destinations.
- Unknown root-level slugs now return 404 instead of receiving an artificial redirect.
- `/local/adelaide/` now serves the Adelaide directory hub; the former hub URL redirects directly to it.
- Curated location pages retain their unique content and indexability.
- Exact postcode records within the Adelaide metro range `5000–5199` can still render at 200, but uncurated records are marked `noindex, follow` and are not added to the sitemap.
- Unknown locations, incorrect name/postcode combinations, and out-of-range South Australian locations return 404. No location content was added or removed from the source data.

The current Cloudflare redirect has not been changed. Do not deploy the `www` canonical configuration as a completed repair until Cloudflare stops redirecting `www` to the apex host and instead preserves `www` while redirecting the apex host to `www`.

## 5. Sitemap, robots, and metadata

- Sitemap URLs are generated with HTTPS and the configured preferred host.
- Booking is removed from the sitemap and marked `noindex, follow`. Robots no longer blocks the booking page, allowing crawlers to read the noindex directive.
- Published blog posts and the six existing public guides are included; unpublished posts are excluded.
- Existing service and curated Adelaide-area sitemap entries are retained.
- Robots now references `{{ SITE_URL }}/sitemap.xml`.
- Shared organization, website, service, video, and breadcrumb structured-data URLs use the preferred origin. Blog and service-page structured data use canonical paths rather than request URLs that can include the wrong host or tracking parameters.
- Service-location titles and descriptions include the actual location to avoid reusing one base-service title and description across every area.

The live sitemap and robots file still reflect the deployed application and will not show these code changes until a deployment is made.

## 6. Internal links and content quality

The sampled 19 internal destinations contained no broken links. The application now uses `/local/adelaide/` for the hub. A complete crawl of all 1,794 live sitemap entries and the full GSC URL list remains outstanding.

Only curated location pages are indexable. Other exact metro records remain available but are noindexed until their content is reviewed and improved. No 404 or 5xx pages were redirected to the homepage or made to return fake 200 responses.

## 7. Automated audit script

The script uses Python’s standard library; it adds no dependency. It only issues GET requests, does not submit forms or mutate records, follows and records redirects, imports URL columns from common GSC CSV exports, and includes timeouts, retries, a concurrency limit, and per-request delay.

Example:

```bash
venv/bin/python scripts/seo_indexing_audit.py \
  --base-url https://www.ydcleaning.com.au \
  --gsc-csv /path/to/gsc-affected-urls.csv \
  --max-urls 0 \
  --max-internal-links 100 \
  --concurrency 2 \
  --timeout 10 \
  --retries 1 \
  --delay 0.3 \
  --output docs/SEO_INDEXING_URL_AUDIT.csv
```

`--max-urls 0` audits the full sitemap. Increase the internal-link limit only when a larger crawl is appropriate; use the complete GSC export to include every affected URL.

## 8. Tests

- Targeted SEO/core regression tests: **74 passed**, including SEO middleware and booking robots behavior.
- Django system check: **no issues**.
- Full suite: **572 tests run; 4 unrelated dashboard tests failed**:
  - `SystemWorkspacePageTests.test_role_editor_groups_permissions_and_preserves_selection`
  - `BookingReassignmentFailureTests.test_missing_new_employee_calendar_service_keeps_assignment_consistent`
  - `BookingReassignmentFailureTests.test_new_employee_calendar_failure_keeps_consistent_retryable_assignment`
  - `BookingReassignmentFailureTests.test_ordinary_booking_edit_still_updates_booking_and_roster`

The full-suite failures concern dashboard role-editor text and booking reassignment behavior, outside the files changed for this repair. They were not altered as part of this task. Tests were run against isolated in-memory SQLite because the configured external test database name already existed; no database was deleted or modified.

## 9. Production verification and remaining limitations

The live audit is saved in [`SEO_INDEXING_URL_AUDIT.csv`](./SEO_INDEXING_URL_AUDIT.csv). It covered all examples in the supplied task, required smoke endpoints, 15 internal-link targets, and 15 additional sitemap URLs (with overlaps), for 65 records total.

Before the code changes are deployed, the live site still has:

1. A Cloudflare `www` → apex redirect, conflicting with the requested canonical host.
2. The old live `/local/adelaide/` response returning 404.
3. Sitemap URLs using the apex domain, including the booking URL.
4. No reproduced 5xx, so the historical 15 reported server-error URLs cannot yet be attributed to a specific cause.
5. No complete GSC CSV or historical Render logs available for individual review of all 229 reported URLs.

After Cloudflare and application deployment, rerun the audit with the complete GSC export and verify every resulting URL. Do not treat this report or a 200 response as proof of indexing.

## 10. Google Search Console revalidation plan

1. **Page with redirect:** Normal for noncanonical variants when the destination is relevant, returns 200, and is canonical. Fix the Cloudflare host rule and internal links first; then validate the remaining affected sample URLs.
2. **Redirect error:** Review every redirect chain and final destination. A redirect to a 404, loop, or unrelated page requires correction; legitimate historical aliases should resolve directly to the right page.
3. **Server error (5xx):** Require corrective action if reproducible. Use timestamped Render and application logs; validate only after repeated production checks show stable non-5xx responses.
4. **Not found (404):** Correct if a valuable intended page is missing. A 404 is appropriate for invalid postcode/location pairs and unsupported areas; remove those URLs from links and sitemaps rather than redirecting them to the homepage.
5. **Excluded by noindex tag:** Expected for private pages and uncurated location pages. Confirm no valuable public page is unintentionally noindexed and that robots.txt does not prevent Google from seeing an intended noindex directive.
6. **Crawled – currently not indexed:** Not inherently an error. Check uniqueness, usefulness, canonical selection, and internal links; request indexing only for materially improved, valuable pages.
7. **Discovered – currently not indexed:** Check crawlability, sitemap quality, duplicate/thin content, and internal linking. Do not repeatedly submit large URL batches.
8. **Duplicate without user-selected canonical:** Select one preferred 200 URL, align internal links and sitemap entries, and redirect only genuine duplicate aliases to that page.

After deployment and production verification, submit `https://www.ydcleaning.com.au/sitemap.xml`, inspect the homepage and representative service and curated suburb pages, request indexing for a small set of important corrected URLs, and start validation for the corrected GSC categories. Do not request indexing for every affected URL until its response, canonical, and content quality have been checked.
