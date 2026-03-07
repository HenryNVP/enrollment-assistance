#!/usr/bin/env python3
"""
SJSU (sjsu.edu) web scraper for building RAG-ready text corpora.

Reads seed URLs from a text file, crawls pages and linked sjsu.edu URLs,
extracts main content (HTML via Trafilatura, PDF via pypdf), respects
robots.txt, deduplicates by URL and content, and writes .txt files with
metadata for vector store ingestion.

Usage:
  python scrape_sjsu.py input/urls_sjsu_sample.txt [--output-dir DIR] ...

Layout: run from tools/scraper/ or pass paths. Default output is output/
in this script's directory. Put URL lists in input/.

Dependencies: pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

try:
    import requests
    from bs4 import BeautifulSoup
    import trafilatura
    from pypdf import PdfReader
    from io import BytesIO
except ImportError as e:
    _script_dir = Path(__file__).resolve().parent
    print(
        f"Install dependencies: pip install -r {_script_dir / 'requirements.txt'}",
        file=sys.stderr,
    )
    print(f"Missing: {e}", file=sys.stderr)
    sys.exit(1)

# Domain restriction: any sjsu.edu subdomain (www, catalog, etc.)
def _is_sjsu_domain(netloc: str) -> bool:
    n = (netloc or "").lower().strip()
    return n == "sjsu.edu" or n.endswith(".sjsu.edu")

USER_AGENT = "EnrollmentAssistantScraper/1.0 (+https://github.com/enrollment-assistant)"
REQUEST_TIMEOUT = 30
DEFAULT_DELAY_SEC = 1.0
DEFAULT_MAX_DEPTH = 0
DEFAULT_MAX_PAGES = 200
SCRAPED_URLS_FILE = "_scraped_urls.txt"
DEFAULT_MAX_LINKS_PER_PAGE = 80

# Content hash length for dedup
CONTENT_HASH_LEN = 12


def _default_output_dir() -> str:
    """Default output directory: output/ next to this script."""
    return str(Path(__file__).resolve().parent / "output")


def normalize_sjsu_url(url: str, base: str | None = None) -> str | None:
    """Normalize and validate URL; return None if not sjsu.edu."""
    url = (url or "").strip()
    if not url or url.startswith("#") or url.lower().startswith(("mailto:", "javascript:", "tel:")):
        return None
    if base:
        url = urljoin(base, url)
    try:
        parsed = urlparse(url)
        if not _is_sjsu_domain(parsed.netloc):
            return None
        scheme = parsed.scheme or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        path = path.rstrip("/") or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return None


def slug_from_url(url: str, url_hash: str = "") -> str:
    """Produce a safe, flat filename slug from URL (no path separators)."""
    parsed = urlparse(url)
    path = (parsed.path or "/").strip("/") or "index"
    slug = re.sub(r"[^\w\-/]", "_", path)
    slug = slug.replace("/", "_")
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        slug = "index"
    if len(slug) > 160:
        slug = slug[:160]
    if url_hash:
        slug = f"{slug}_{url_hash}"
    return slug


def content_hash(text: str) -> str:
    """Stable hash of normalized content for deduplication."""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:CONTENT_HASH_LEN]


def get_robots_parser(session: requests.Session, netloc: str) -> RobotFileParser:
    """Fetch and parse robots.txt for the given netloc. If missing/failed, allow all."""
    rp = RobotFileParser()
    url = f"https://{netloc}/robots.txt"
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200 and r.text.strip():
            rp.parse(r.text.splitlines())
        else:
            rp.parse(["User-agent: *", "Allow: /"])
    except Exception:
        rp.parse(["User-agent: *", "Allow: /"])
    return rp


def extract_html_main_content(html: str, url: str) -> tuple[str, str]:
    """Extract main content and title from HTML using Trafilatura. Returns (title, body)."""
    body = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        output_format="txt",
    )
    if not body:
        body = trafilatura.extract(html, url=url, output_format="txt", no_fallback=True) or ""
    body = (body or "").strip()
    title = ""
    try:
        meta = trafilatura.extract_metadata(html)
        if meta and getattr(meta, "title", None):
            title = (meta.title or "").strip()
    except Exception:
        pass
    if not title and body:
        first_line = body.split("\n")[0].strip()
        if len(first_line) < 200:
            title = first_line
    return title or url, body


def extract_links_from_html(html: str, base_url: str) -> list[str]:
    """Extract sjsu.edu links from HTML for crawling."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        normalized = normalize_sjsu_url(a["href"].strip(), base_url)
        if normalized and normalized not in links:
            links.append(normalized)
    return links


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes."""
    reader = PdfReader(BytesIO(data))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


def fetch_resource(
    session: requests.Session,
    url: str,
    robots: RobotFileParser | None,
) -> tuple[str | None, str | None, str | None, list[str]]:
    """
    Fetch URL and return (content_type, title, body_text, links).
    content_type is 'html', 'pdf', or None on failure.
    For PDF, links is empty.
    """
    if robots and not robots.can_fetch(USER_AGENT, url):
        return None, None, None, []

    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        r.raise_for_status()
        content_type = (r.headers.get("Content-Type") or "").lower()
        is_pdf = "application/pdf" in content_type or url.rstrip("/").lower().endswith(".pdf")

        if is_pdf:
            raw = r.content
            if not raw:
                return None, None, None, []
            title = url.split("/")[-1] or "document"
            if title.endswith(".pdf"):
                title = title[:-4]
            body = extract_text_from_pdf(raw)
            return "pdf", title, body, []

        # HTML
        r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        title, body = extract_html_main_content(html, url)
        links = extract_links_from_html(html, url)
        return "html", title, body, links

    except requests.RequestException as e:
        print(f"  Error fetching {url}: {e}", file=sys.stderr)
        return None, None, None, []
    except Exception as e:
        print(f"  Error processing {url}: {e}", file=sys.stderr)
        return None, None, None, []


def load_seed_urls(path: str) -> list[str]:
    """Load and normalize seed URLs from a text file (one per line, # comments)."""
    urls = []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"URLs file not found: {path}")
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        u = normalize_sjsu_url(line)
        if u and u not in urls:
            urls.append(u)
    return urls


def load_previously_scraped_urls(output_dir: Path) -> set[str]:
    """Load URLs already scraped in a prior run (from sidecar file). Enables resume/skip on rerun."""
    sidecar = output_dir / SCRAPED_URLS_FILE
    if not sidecar.exists():
        return set()
    try:
        return {
            line.strip()
            for line in sidecar.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def save_page(
    output_dir: Path,
    url: str,
    title: str,
    body: str,
    source_type: str,
) -> Path:
    """Write page content to a .txt file with metadata; return path. Uses safe, unique filenames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    base_slug = slug_from_url(url, url_hash)
    path = output_dir / f"{base_slug}.txt"
    counter = 0
    while path.exists():
        counter += 1
        path = output_dir / f"{base_slug}_{counter}.txt"

    header = f"Source: {url}\nTitle: {title}\nType: {source_type.upper()}\n\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body, encoding="utf-8")
    # Record URL so reruns skip this page
    sidecar = output_dir / SCRAPED_URLS_FILE
    try:
        with sidecar.open("a", encoding="utf-8") as f:
            f.write(url + "\n")
    except Exception:
        pass
    return path


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    default_out = script_dir / "output"

    parser = argparse.ArgumentParser(
        description="Scrape SJSU (sjsu.edu) pages; extract main content (HTML/PDF) and save .txt for RAG.",
    )
    parser.add_argument(
        "url_file",
        type=str,
        help="Text file with one SJSU URL per line (# comments ignored). Use input/urls_sjsu_sample.txt",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=str(default_out),
        help=f"Output directory for .txt files (default: {default_out})",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help=f"Crawl depth from seed URLs (0=seeds only) (default: {DEFAULT_MAX_DEPTH})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Stop after saving this many pages (default: {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--max-links-per-page",
        type=int,
        default=DEFAULT_MAX_LINKS_PER_PAGE,
        help=f"Max sjsu.edu links to queue per page (default: {DEFAULT_MAX_LINKS_PER_PAGE})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SEC,
        help=f"Seconds between requests (default: {DEFAULT_DELAY_SEC})",
    )
    parser.add_argument(
        "--no-robots",
        action="store_true",
        help="Disable robots.txt checks (not recommended for production)",
    )
    parser.add_argument(
        "--no-content-dedup",
        action="store_true",
        help="Do not skip pages with duplicate content (by default duplicates are skipped)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not skip URLs already scraped in a previous run (default: resume by skipping existing)",
    )
    args = parser.parse_args()

    try:
        seed_urls = load_seed_urls(args.url_file)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    if not seed_urls:
        print("No valid SJSU URLs found in file.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    # Load URLs from previous run so we skip them (resume on rerun)
    seen_urls: set[str] = set()
    if not args.no_resume:
        seen_urls = load_previously_scraped_urls(output_dir)
        if seen_urls:
            print(f"Resuming: skipping {len(seen_urls)} URL(s) already scraped in {output_dir}")

    # robots.txt per netloc (loaded on first use for each subdomain)
    robots_cache: dict[str, RobotFileParser] = {}

    seen_content_hashes: set[str] = set()
    saved_count = 0
    # (url, depth)
    queue: deque[tuple[str, int]] = deque((u, 0) for u in seed_urls)

    while queue and saved_count < args.max_pages:
        url, depth = queue.popleft()
        if url in seen_urls:
            continue
        seen_urls.add(url)

        netloc = urlparse(url).netloc.lower()
        if not args.no_robots and netloc not in robots_cache:
            robots_cache[netloc] = get_robots_parser(session, netloc)
        robots = None if args.no_robots else robots_cache.get(netloc)
        if robots and not robots.can_fetch(USER_AGENT, url):
            print(f"Skipped (robots.txt): {url}")
            continue

        print(f"[depth={depth}] {url}")
        content_type, title, body, links = fetch_resource(session, url, robots)
        time.sleep(args.delay)

        if content_type and body and body.strip():
            if not args.no_content_dedup:
                h = content_hash(body)
                if h in seen_content_hashes:
                    print(f"  Skipped (duplicate content)")
                    if depth < args.max_depth:
                        for link in links[: args.max_links_per_page]:
                            if link not in seen_urls:
                                queue.append((link, depth + 1))
                    continue
                seen_content_hashes.add(h)

            out_path = save_page(output_dir, url, title, body, content_type)
            print(f"  Saved: {out_path} ({content_type})")
            saved_count += 1
        elif content_type is None:
            pass  # already logged

        if depth < args.max_depth and saved_count < args.max_pages:
            for link in links[: args.max_links_per_page]:
                if link not in seen_urls:
                    queue.append((link, depth + 1))

    print(f"\nDone. Saved {saved_count} page(s) to {output_dir.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
