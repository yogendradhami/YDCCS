import csv
import time
import requests
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

SITEMAP_URL = "https://ydcleaning.com.au/sitemap.xml"
OUTPUT_FILE = "sitemap_audit.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; YDCleaning-Sitemap-Audit/1.0)"
}


def get_urls():
    print(f"Downloading sitemap: {SITEMAP_URL}")

    response = requests.get(
        SITEMAP_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    namespace = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9"
    }

    urls = []

    for url in root.findall("sm:url", namespace):
        loc = url.find("sm:loc", namespace)

        if loc is not None and loc.text:
            urls.append(loc.text.strip())

    return urls


def check_url(url):
    start = time.time()

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=True
        )

        elapsed = round(time.time() - start, 2)

        return {
            "url": url,
            "status": response.status_code,
            "final_url": response.url,
            "redirected": response.url != url,
            "response_time": elapsed,
            "error": ""
        }

    except requests.RequestException as e:
        elapsed = round(time.time() - start, 2)

        return {
            "url": url,
            "status": "ERROR",
            "final_url": "",
            "redirected": False,
            "response_time": elapsed,
            "error": str(e)
        }


def main():

    urls = get_urls()

    print()
    print("=" * 60)
    print(f"TOTAL SITEMAP URLS: {len(urls)}")
    print("=" * 60)
    print()

    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:

        futures = {
            executor.submit(check_url, url): url
            for url in urls
        }

        completed = 0

        for future in as_completed(futures):

            result = future.result()

            results.append(result)

            completed += 1

            print(
                f"[{completed}/{len(urls)}] "
                f"{result['status']} "
                f"{result['url']}"
            )

    results.sort(key=lambda x: x["url"])

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "url",
                "status",
                "final_url",
                "redirected",
                "response_time",
                "error"
            ]
        )

        writer.writeheader()
        writer.writerows(results)

    print()
    print("=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)

    status_counts = {}

    for result in results:
        status = str(result["status"])

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")

    live = sum(
        1 for r in results
        if r["status"] == 200
    )

    redirects = sum(
        1 for r in results
        if r["redirected"]
    )

    errors = sum(
        1 for r in results
        if str(r["status"]).startswith("4")
        or str(r["status"]).startswith("5")
        or r["status"] == "ERROR"
    )

    print()
    print(f"LIVE (200):       {live}")
    print(f"REDIRECTED:       {redirects}")
    print(f"ERROR/4xx/5xx:    {errors}")
    print()
    print(f"CSV saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()