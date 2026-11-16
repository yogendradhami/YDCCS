#!/usr/bin/env python3
"""Read-only, rate-limited SEO indexing audit for a public website."""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path


LOGGER = logging.getLogger("seo_indexing_audit")
DEFAULT_BASE_URL = "https://www.ydcleaning.com.au"
USER_AGENT = "YDCCS-SEO-Audit/1.0 (+read-only)"
MAX_RESPONSE_BYTES = 2_000_000
MAX_SITEMAP_BYTES = 10_000_000


class PageMetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.robots = []
        self.canonical = ""
        self.internal_links = []
        self._inside_title = False

    def handle_starttag(self, tag, attrs):
        attrs = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self._inside_title = True
        elif tag.lower() == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.description = attrs.get("content", "").strip()
            elif name in {"robots", "googlebot"}:
                self.robots.append(attrs.get("content", "").strip())
        elif tag.lower() == "link" and "canonical" in {
            token.lower() for token in attrs.get("rel", "").split()
        }:
            if not self.canonical:
                self.canonical = attrs.get("href", "").strip()
        elif tag.lower() == "a" and attrs.get("href"):
            self.internal_links.append(attrs["href"].strip())

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._inside_title = False

    def handle_data(self, data):
        if self._inside_title:
            self.title += data


class RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = 10
    max_repeats = 10

    def __init__(self, initial_url):
        super().__init__()
        self.chain = []
        self.visited = {normalize_url(initial_url)}
        self.loop_detected = False

    def redirect_request(self, request, response, code, message, headers, new_url):
        resolved_url = urllib.parse.urljoin(request.full_url, new_url)
        normalized = normalize_url(resolved_url)
        self.chain.append(
            {
                "status": code,
                "source": request.full_url,
                "destination": resolved_url,
            }
        )
        if normalized in self.visited:
            self.loop_detected = True
            return None
        self.visited.add(normalized)
        return super().redirect_request(
            request,
            response,
            code,
            message,
            headers,
            resolved_url,
        )


def normalize_url(url):
    parsed = urllib.parse.urlsplit(url.strip())
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def same_origin(url, base_url):
    left = urllib.parse.urlsplit(url)
    right = urllib.parse.urlsplit(base_url)
    left_host = (left.hostname or "").lower()
    right_host = (right.hostname or "").lower()
    accepted_hosts = {right_host}
    if right_host.startswith("www."):
        accepted_hosts.add(right_host[4:])
    else:
        accepted_hosts.add(f"www.{right_host}")
    return left.scheme.lower() in {"http", "https"} and left_host in accepted_hosts


def fetch_url(url, timeout, retries, max_bytes=MAX_RESPONSE_BYTES):
    last_error = ""
    started = time.monotonic()
    for attempt in range(retries + 1):
        redirect_handler = RecordingRedirectHandler(url)
        opener = urllib.request.build_opener(redirect_handler)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xml,*/*",
            },
        )
        try:
            with opener.open(request, timeout=timeout) as response:
                body = response.read(max_bytes + 1)[:max_bytes]
                return {
                    "status": response.status,
                    "final_url": response.geturl(),
                    "headers": response.headers,
                    "body": body,
                    "chain": redirect_handler.chain,
                    "loop": redirect_handler.loop_detected,
                    "elapsed": time.monotonic() - started,
                    "error": "",
                }
        except urllib.error.HTTPError as error:
            body = error.read(max_bytes + 1)[:max_bytes]
            if error.code >= 500 and attempt < retries:
                last_error = f"HTTP {error.code}"
                time.sleep(0.5 * (attempt + 1))
                continue
            return {
                "status": error.code,
                "final_url": error.geturl(),
                "headers": error.headers,
                "body": body,
                "chain": redirect_handler.chain,
                "loop": redirect_handler.loop_detected,
                "elapsed": time.monotonic() - started,
                "error": last_error,
            }
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = str(error)
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    return {
        "status": 0,
        "final_url": url,
        "headers": {},
        "body": b"",
        "chain": [],
        "loop": False,
        "elapsed": time.monotonic() - started,
        "error": last_error,
    }


def read_sitemap_urls(base_url, timeout, retries):
    robots_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "robots.txt")
    robots_result = fetch_url(robots_url, timeout, retries)
    robots_body = robots_result["body"].decode("utf-8", errors="replace")
    sitemap_locations = [
        line.split(":", 1)[1].strip()
        for line in robots_body.splitlines()
        if line.strip().lower().startswith("sitemap:")
    ]
    if not sitemap_locations:
        sitemap_locations = [
            urllib.parse.urljoin(base_url.rstrip("/") + "/", "sitemap.xml")
        ]

    disallow_rules = []
    current_agents = []
    current_group_has_rules = False
    for line in robots_body.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        directive, value = (part.strip() for part in line.split(":", 1))
        directive = directive.lower()
        if directive == "user-agent":
            if current_group_has_rules:
                current_agents = []
            current_agents.append(value.lower())
            current_group_has_rules = False
        elif directive in {"allow", "disallow"} and "*" in current_agents and value:
            disallow_rules.append((directive, value))
            current_group_has_rules = True

    sitemap_urls = set()
    visited_sitemaps = set()
    sitemap_errors = []

    def visit_sitemap(sitemap_url, depth=0):
        normalized = normalize_url(sitemap_url)
        if normalized in visited_sitemaps or depth > 5:
            return
        visited_sitemaps.add(normalized)
        result = fetch_url(
            sitemap_url,
            timeout,
            retries,
            max_bytes=MAX_SITEMAP_BYTES,
        )
        if result["status"] < 200 or result["status"] >= 400:
            sitemap_errors.append(
                f"{sitemap_url}: HTTP {result['status']} {result['error']}".strip()
            )
            return
        try:
            root = ET.fromstring(result["body"])
        except ET.ParseError as error:
            sitemap_errors.append(f"{sitemap_url}: invalid XML ({error})")
            return
        root_name = root.tag.rsplit("}", 1)[-1].lower()
        locations = [
            item.text.strip()
            for item in root.iter()
            if item.tag.rsplit("}", 1)[-1].lower() == "loc" and item.text
        ]
        if root_name == "sitemapindex":
            for child_sitemap in locations:
                visit_sitemap(child_sitemap, depth + 1)
        else:
            sitemap_urls.update(normalize_url(location) for location in locations)

    for sitemap_url in sitemap_locations:
        visit_sitemap(sitemap_url)

    return robots_body, disallow_rules, sitemap_urls, sitemap_errors


def robots_disallows(url, rules):
    path = urllib.parse.urlsplit(url).path or "/"
    matches = []
    for directive, pattern in rules:
        regex = "^" + re.escape(pattern).replace(r"\*", ".*")
        if pattern.endswith("$"):
            regex = "^" + re.escape(pattern[:-1]).replace(r"\*", ".*") + "$"
        if re.search(regex, path):
            matches.append((len(pattern), directive == "allow"))
    if not matches:
        return False
    return not max(matches, key=lambda match: (match[0], match[1]))[1]


def load_csv_urls(csv_path):
    urls = []
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        rows = list(reader)
    if not rows:
        return urls

    header = [re.sub(r"[^a-z]", "", cell.lower()) for cell in rows[0]]
    url_columns = [
        index
        for index, value in enumerate(header)
        if value in {"url", "page", "address", "affectedurl", "urlinspected"}
        or value.endswith("url")
    ]
    column = url_columns[0] if url_columns else 0
    start = 1 if url_columns else 0
    for row in rows[start:]:
        if len(row) > column:
            value = row[column].strip()
            if value.startswith(("http://", "https://")):
                urls.append(value)
    return urls


def append_issue(record, label):
    if label not in record["issues"]:
        record["issues"].append(label)


def audit_page(
    url,
    sources,
    sitemap_urls,
    base_url,
    disallow_rules,
    timeout,
    retries,
    delay,
):
    result = fetch_url(url, timeout, retries)
    time.sleep(delay)
    headers = result["headers"]
    content_type = headers.get("Content-Type", "").lower()
    parser = PageMetadataParser()
    if "html" in content_type or re.match(
        rb"\s*<(?:!doctype|html|head|body)\b",
        result["body"],
        re.IGNORECASE,
    ):
        parser.feed(result["body"].decode("utf-8", errors="replace"))

    final_url = result["final_url"]
    canonical = (
        urllib.parse.urljoin(final_url, parser.canonical)
        if parser.canonical
        else ""
    )
    robots_directives = [directive.lower() for directive in parser.robots]
    header_robots = headers.get("X-Robots-Tag", "")
    robots_directives.append(header_robots.lower())
    noindex = any("noindex" in directive for directive in robots_directives)
    blocked = robots_disallows(url, disallow_rules)
    sitemap_included = normalize_url(url) in sitemap_urls
    sitemap_host = urllib.parse.urlsplit(url).netloc.lower()
    base_host = urllib.parse.urlsplit(base_url).netloc.lower()

    record = {
        "url": url,
        "http_status": result["status"],
        "redirect_chain": " -> ".join(
            (
                f'{item["status"]} {item["source"]} '
                f'=> {item["destination"]}'
            )
            for item in result["chain"]
        ),
        "redirect_count": len(result["chain"]),
        "final_destination": final_url,
        "canonical_url": canonical,
        "robots_indexable": not noindex and not blocked,
        "robots_directives": "; ".join(
            value for value in robots_directives if value
        ),
        "title": " ".join(parser.title.split()),
        "meta_description": " ".join(parser.description.split()),
        "sitemap_inclusion": sitemap_included,
        "response_time_seconds": round(result["elapsed"], 3),
        "error_details": result["error"],
        "sources": "; ".join(sorted(sources)),
        "internal_links": parser.internal_links,
        "issues": [],
    }
    if result["loop"]:
        append_issue(record, "redirect loop")
    if sitemap_included and result["chain"]:
        append_issue(record, "3xx URL in sitemap")
    if len(result["chain"]) > 1:
        append_issue(record, "redirect chain")
    if result["status"] == 0 or result["status"] >= 500:
        append_issue(record, "5xx or request error")
    elif result["status"] >= 400:
        append_issue(record, "4xx")
    if not canonical and "html" in content_type:
        append_issue(record, "missing canonical")
    elif canonical:
        canonical_parts = urllib.parse.urlsplit(canonical)
        final_parts = urllib.parse.urlsplit(final_url)
        if (
            canonical_parts.netloc.lower() != final_parts.netloc.lower()
            or canonical_parts.path != final_parts.path
            or canonical_parts.query
        ):
            append_issue(record, "canonical mismatch")
    if sitemap_included and sitemap_host != base_host:
        append_issue(record, "wrong sitemap domain")
    if blocked:
        append_issue(record, "robots blocked")
    if noindex:
        append_issue(record, "noindex")
    if sources and "internal link" in sources and result["status"] >= 400:
        append_issue(record, "broken internal link")
    record["recommended_action"] = recommended_action(record["issues"])
    return record


def recommended_action(issues):
    if not issues:
        return (
            "No technical issue detected; assess content quality before "
            "requesting indexing."
        )
    actions = {
        "redirect loop": (
            "Correct the loop at the hosting/proxy or application routing layer."
        ),
        "3xx URL in sitemap": (
            "Replace the sitemap entry with the final canonical 200 URL."
        ),
        "redirect chain": (
            "Update links and redirects to point directly to the final destination."
        ),
        "5xx or request error": (
            "Investigate the production response and server/application logs."
        ),
        "4xx": (
            "Confirm the URL should exist; restore it or remove stale references."
        ),
        "missing canonical": (
            "Add one self-referencing canonical to the indexable page."
        ),
        "canonical mismatch": (
            "Align the canonical with the final, preferred 200 URL."
        ),
        "wrong sitemap domain": (
            "Regenerate the sitemap using the preferred HTTPS host."
        ),
        "robots blocked": (
            "Review robots.txt only if this page should be crawlable."
        ),
        "noindex": "Confirm noindex is intentional for this page.",
        "broken internal link": (
            "Update the source page to a valid canonical destination."
        ),
        "duplicate title": (
            "Write a unique, descriptive title for each page."
        ),
        "duplicate description": (
            "Write a unique meta description for each page."
        ),
    }
    return " ".join(actions[item] for item in issues if item in actions)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--gsc-csv", help="CSV export containing affected page URLs.")
    parser.add_argument("--output", default="seo_indexing_audit.csv")
    parser.add_argument(
        "--max-urls",
        type=int,
        default=100,
        help="Maximum sitemap URLs to audit; use 0 to audit the full sitemap.",
    )
    parser.add_argument(
        "--max-internal-links",
        type=int,
        default=100,
        help="Maximum discovered internal links to audit; use 0 to disable.",
    )
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("urls", nargs="*", help="Additional page URLs to audit.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    base_url = args.base_url.rstrip("/")
    if urllib.parse.urlsplit(base_url).scheme not in {"http", "https"}:
        parser.error("--base-url must use HTTP or HTTPS")
    if (
        args.max_urls < 0
        or args.max_internal_links < 0
        or args.concurrency < 1
        or args.retries < 0
    ):
        parser.error(
            "URL limits cannot be negative, concurrency must be positive, "
            "and retries cannot be negative"
        )

    robots_body, disallow_rules, sitemap_urls, sitemap_errors = read_sitemap_urls(
        base_url,
        args.timeout,
        args.retries,
    )
    gsc_urls = load_csv_urls(args.gsc_csv) if args.gsc_csv else []

    ordered_urls = []
    sources_by_url = {}

    def add_url(value, source):
        resolved = urllib.parse.urljoin(base_url + "/", value.strip())
        parsed = urllib.parse.urlsplit(resolved)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return
        key = normalize_url(resolved)
        sources_by_url.setdefault(key, set()).add(source)
        if key not in ordered_urls:
            ordered_urls.append(key)

    for url in gsc_urls:
        add_url(url, "GSC CSV")
    for url in args.urls:
        add_url(url, "command line")
    add_url(urllib.parse.urljoin(base_url + "/", "robots.txt"), "robots.txt")
    add_url(urllib.parse.urljoin(base_url + "/", "sitemap.xml"), "sitemap endpoint")
    primary_urls = list(ordered_urls)
    sitemap_only_urls = []
    for url in sorted(sitemap_urls):
        key = normalize_url(url)
        sources_by_url.setdefault(key, set()).add("sitemap")
        if key not in primary_urls:
            sitemap_only_urls.append(key)

    records_by_url = {}

    def audit_batch(urls):
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = [
                executor.submit(
                    audit_page,
                    url,
                    sources_by_url[url],
                    sitemap_urls,
                    base_url,
                    disallow_rules,
                    args.timeout,
                    args.retries,
                    args.delay,
                )
                for url in urls
            ]
            return [future.result() for future in futures]

    for record in audit_batch(primary_urls):
        records_by_url[normalize_url(record["url"])] = record

    internal_candidates = []
    for record in records_by_url.values():
        for href in record.pop("internal_links", []):
            target = urllib.parse.urljoin(record["final_destination"], href)
            parsed = urllib.parse.urlsplit(target)
            if (
                same_origin(target, base_url)
                and parsed.path
                and parsed.scheme in {"http", "https"}
                and not parsed.path.startswith(("/static/", "/media/"))
            ):
                key = normalize_url(target)
                if key not in records_by_url and key not in internal_candidates:
                    sources_by_url.setdefault(key, set()).add("internal link")
                    internal_candidates.append(key)

    additional_urls = internal_candidates[:args.max_internal_links]
    for record in audit_batch(additional_urls):
        records_by_url[normalize_url(record["url"])] = record

    selected_sitemap_urls = [
        url
        for url in sitemap_only_urls
        if url not in records_by_url
    ]
    if args.max_urls:
        selected_sitemap_urls = selected_sitemap_urls[: args.max_urls]
    for record in audit_batch(selected_sitemap_urls):
        records_by_url[normalize_url(record["url"])] = record
    if len(sitemap_only_urls) > len(selected_sitemap_urls):
        LOGGER.warning(
            "Audited %d of %d sitemap-only URLs; increase --max-urls to inspect more.",
            len(selected_sitemap_urls),
            len(sitemap_only_urls),
        )

    records = list(records_by_url.values())
    title_counts = {}
    description_counts = {}
    for record in records:
        title = record["title"].casefold()
        description = record["meta_description"].casefold()
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1
        if description:
            description_counts[description] = description_counts.get(description, 0) + 1
    for record in records:
        if record["title"] and title_counts[record["title"].casefold()] > 1:
            append_issue(record, "duplicate title")
        if (
            record["meta_description"]
            and description_counts[record["meta_description"].casefold()] > 1
        ):
            append_issue(record, "duplicate description")
        record["issue_classification"] = "; ".join(record["issues"]) or "none detected"
        if record["issues"]:
            record["recommended_action"] = recommended_action(record["issues"])
        record.pop("issues")
        record.pop("internal_links", None)

    fieldnames = [
        "url",
        "http_status",
        "redirect_chain",
        "redirect_count",
        "final_destination",
        "canonical_url",
        "robots_indexable",
        "robots_directives",
        "title",
        "meta_description",
        "sitemap_inclusion",
        "response_time_seconds",
        "error_details",
        "sources",
        "issue_classification",
        "recommended_action",
    ]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    sitemap_audited = sum(
        "sitemap" in record["sources"].split("; ")
        for record in records
    )
    LOGGER.info(
        "Audited %d URLs (%d sitemap URLs; %d available); wrote %s.",
        len(records),
        sitemap_audited,
        len(sitemap_urls),
        output_path,
    )
    if sitemap_errors:
        for error in sitemap_errors:
            LOGGER.error("Sitemap error: %s", error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
