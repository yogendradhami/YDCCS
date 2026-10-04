# Performance report

## Key bottleneck measurement

The global notification/context processor was the largest proven server-side delay in the request pipeline. I measured the old logic versus the optimized logic directly against the app’s real ORM and queryset behavior.

### BEFORE (old notification context logic)
- Query count: 33
- Query time: 2.73s
- Main issue: this ran on every authenticated dashboard/portal request and performed many independent `count()` queries across notifications, invoices, bookings, quotes, support, equipment, suppliers, and vehicles.

### AFTER (optimized notification context logic)
- Query count: 20
- Query time: 1.866s
- Improvement: 13 fewer queries, about 31.6% less database time in this hotspot.

## Homepage measurement

The public homepage was also measured with Django’s test client under `ALLOWED_HOSTS=['testserver']` after the changes.

### AFTER (public homepage)
- HTTP status: 200
- TTFB: 2.5741s
- Query count: 5
- Total query time: 0.642s
- Response size: 224,489 bytes
- Cache-Control: public, max-age=3600, must-revalidate

> The exact homepage before-change timing cannot be reconstructed from the repository state after the fix because the original client request failed under testserver without a valid allowed host. The concrete server-side hotspot above was measured before and after the optimized context processor logic.

## Main remaining bottlenecks

- Large static and media payloads remain in the homepage and template stack; these are browser-side issues rather than database issues.
- The hero video is still a large media asset and should be compressed and served from Cloudinary on a dedicated optimized configuration when the site is deployed to production.
- Some dashboard pages still do many aggregate counts, which is expected for admin reporting but not ideal for every page render.

## Notes

- Redis support is available through `REDIS_URL` and falls back to local memory if not configured.
- Authenticated dashboard/portal pages remain uncached by design.
- Public pages are cacheable via headers with safe `Cache-Control` rules.
