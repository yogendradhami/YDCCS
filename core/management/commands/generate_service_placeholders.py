from django.core.management.base import BaseCommand
from django.conf import settings
import os

from core.seo_data import SERVICE_DEFINITIONS


class Command(BaseCommand):
    help = "Generate SVG placeholders for service images missing in static/images/services"

    def handle(self, *args, **options):
        static_dir = os.path.join(settings.BASE_DIR, "static", "images", "services")
        os.makedirs(static_dir, exist_ok=True)

        created = []
        for slug, definition in SERVICE_DEFINITIONS.items():
            # skip empty slugs
            if not slug:
                continue

            candidates = [f"{slug}.svg", f"{slug}.webp", f"{slug}.jpg", f"{slug}.png"]
            exists = any(os.path.exists(os.path.join(static_dir, c)) for c in candidates)

            if exists:
                continue

            svg_path = os.path.join(static_dir, f"{slug}.svg")
            title = definition.get("service_name", slug).replace("&", "&amp;")

            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
  <rect width="100%" height="100%" fill="#f5f7fa" />
  <g>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="48" fill="#2b2b2b">{title}</text>
  </g>
</svg>
'''

            try:
                with open(svg_path, "w", encoding="utf-8") as fh:
                    fh.write(svg_content)
                created.append(svg_path)
            except Exception as e:
                self.stderr.write(f"Failed to write {svg_path}: {e}")

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {len(created)} placeholders"))
            for p in created:
                self.stdout.write(f" - {p}")
        else:
            self.stdout.write("No placeholders were needed; all service images exist.")
