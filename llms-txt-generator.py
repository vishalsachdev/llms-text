#!/usr/bin/env python3
"""
llms.txt Generator (llmstxt.org spec)
-------------------------------------
Crawls a website and generates spec-compliant llms.txt files:
  # Title > Summary, ## Sections, - [Link](url): description

Highlights:
  - Respects robots.txt and seeds the crawl from sitemap.xml when available.
  - Normalizes URLs (drops fragments and tracking params) and stays strictly
    on the target host/path prefix.
  - With --full, fetches each page and extracts its main text to build a real
    llms-full.txt (page content, not just a link map), per the spec.
  - Optionally polishes the index with the Gemini API.
"""

import argparse
import datetime
import json
import os
import re
import time
from collections import defaultdict
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

USER_AGENT = "llms-txt-generator/1.0 (+https://llmstxt.org/)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

SKIP_SUFFIXES = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".zip", ".gz",
    ".tar", ".mp4", ".mp3", ".mov", ".css", ".js", ".ico", ".woff", ".woff2",
    ".xml", ".json", ".rss",
)
TRACKING_PARAMS = ("utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "gclid", "fbclid", "mc_cid", "mc_eid", "ref")


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def normalize_url(url):
    """Drop fragments and tracking query params; normalize trailing slash."""
    url, _ = urldefrag(url)
    parts = urlparse(url)
    query = "&".join(
        kv for kv in parts.query.split("&")
        if kv and kv.split("=", 1)[0].lower() not in TRACKING_PARAMS
    )
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((parts.scheme, parts.netloc, path, parts.params, query, ""))


def in_scope(url, base):
    """True if url is on the same host and under the base path prefix."""
    u, b = urlparse(url), urlparse(base)
    if u.scheme not in ("http", "https") or u.netloc.lower() != b.netloc.lower():
        return False
    base_prefix = b.path.rstrip("/")
    return u.path == base_prefix or u.path.startswith(base_prefix + "/") or base_prefix == ""


def looks_like_html(url):
    return not url.lower().split("?", 1)[0].endswith(SKIP_SUFFIXES)


# ---------------------------------------------------------------------------
# Crawl
# ---------------------------------------------------------------------------

def load_robots(base_url):
    rp = robotparser.RobotFileParser()
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        resp = SESSION.get(robots_url, timeout=10)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp.parse([])  # no robots.txt -> allow all
    except requests.RequestException:
        rp.parse([])
    return rp


def discover_sitemap_urls(base_url, limit=2000):
    """Best-effort sitemap.xml discovery (handles one level of sitemap index)."""
    found = []
    queue = [urljoin(base_url, "/sitemap.xml")]
    seen_sitemaps = set()
    while queue and len(found) < limit:
        sm_url = queue.pop(0)
        if sm_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sm_url)
        try:
            resp = SESSION.get(sm_url, timeout=15)
            if resp.status_code != 200:
                continue
            root = ElementTree.fromstring(resp.content)
        except (requests.RequestException, ElementTree.ParseError):
            continue
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.findall(".//sm:sitemap/sm:loc", ns):
            if loc.text:
                queue.append(loc.text.strip())
        for loc in root.findall(".//sm:url/sm:loc", ns):
            if loc.text:
                found.append(loc.text.strip())
    return found


def fetch_page(url):
    """Return (final_url, title, text) or None on failure."""
    try:
        resp = SESSION.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"  ↳ Error: {e}")
        return None
    if resp.status_code != 200 or "html" not in resp.headers.get("Content-Type", ""):
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    return resp.url, re.sub(r"\s+", " ", title), soup


def extract_links(soup, page_url):
    for link in soup.find_all("a", href=True):
        yield normalize_url(urljoin(page_url, link["href"]))


def extract_text(soup, max_chars=4000):
    """Lightweight HTML -> markdown-ish text for llms-full.txt."""
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "aside", "form", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    chunks = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        if not text:
            continue
        name = el.name
        if name in ("h1", "h2"):
            chunks.append(f"\n### {text}")
        elif name in ("h3", "h4"):
            chunks.append(f"\n**{text}**")
        elif name == "li":
            chunks.append(f"- {text}")
        else:
            chunks.append(text)
    out = "\n".join(chunks).strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + " […]"
    return out


def crawl_site(base_url, max_pages=150, delay=0.2, want_text=False,
               respect_robots=True):
    base_url = normalize_url(base_url)
    print(f"Starting crawl of {base_url} (max: {max_pages} pages)")

    rp = load_robots(base_url) if respect_robots else None

    def allowed(url):
        return rp is None or rp.can_fetch(USER_AGENT, url)

    seeds = discover_sitemap_urls(base_url)
    seeds = [u for u in (normalize_url(s) for s in seeds)
             if in_scope(u, base_url) and looks_like_html(u) and allowed(u)]
    if seeds:
        print(f"  Seeded {len(seeds)} URLs from sitemap.xml")

    to_visit = [base_url] + seeds
    visited = set()
    pages = []  # list of dicts: {url, title, text}

    while to_visit and len(pages) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not (in_scope(url, base_url) and looks_like_html(url) and allowed(url)):
            continue

        print(f"Crawling [{len(pages) + 1}/{max_pages}]: {url}")
        result = fetch_page(url)
        time.sleep(delay)
        if not result:
            continue
        final_url, title, soup = result
        final_url = normalize_url(final_url)
        if final_url in visited and final_url != url:
            continue
        visited.add(final_url)

        record = {"url": final_url, "title": title}
        if want_text:
            record["text"] = extract_text(soup)
        pages.append(record)

        for link in extract_links(soup, final_url):
            if link not in visited and link not in to_visit:
                to_visit.append(link)

    print(f"Crawl complete. Found {len(pages)} pages.")
    return pages


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def section_label(slug):
    return slug.replace("-", " ").replace("_", " ").title() if slug else "Home"


def group_by_section(pages, base_url):
    grouped = defaultdict(list)
    base_prefix = urlparse(normalize_url(base_url)).path.rstrip("/")
    for page in pages:
        path = urlparse(page["url"]).path
        if base_prefix and path.startswith(base_prefix):
            path = path[len(base_prefix):]
        parts = [p for p in path.strip("/").split("/") if p]
        grouped[parts[0] if parts else ""].append(page)
    sections = sorted(grouped, key=lambda s: (s != "", s))  # "" (Home) first
    return [(s, grouped[s]) for s in sections]


def build_index(pages, site_name, base_url):
    """Spec-compliant llms.txt: H1, blockquote, H2 sections of links."""
    out = [f"# {site_name}", ""]
    out.append(f"> Site map of {site_name} ({base_url}), auto-generated for LLM context.")
    out.append("")
    for slug, items in group_by_section(pages, base_url):
        out.append(f"## {section_label(slug)}")
        out.append("")
        for page in sorted(items, key=lambda p: len(p["url"])):
            out.append(f"- [{page['title']}]({page['url']})")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def build_full(pages, site_name, base_url):
    """llms-full.txt: page content grouped by section."""
    today = datetime.date.today().isoformat()
    out = [f"# {site_name}", ""]
    out.append(f"> Full content export of {site_name} ({base_url}), generated {today}.")
    out.append("")
    for slug, items in group_by_section(pages, base_url):
        out.append(f"## {section_label(slug)}")
        out.append("")
        for page in sorted(items, key=lambda p: len(p["url"])):
            out.append(f"### {page['title']}")
            out.append(f"Source: {page['url']}")
            out.append("")
            out.append(page.get("text", "").strip() or "_(no extractable text)_")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Gemini enhancement (optional)
# ---------------------------------------------------------------------------

def get_gemini_api_key():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        api_key = input("Enter your Google API key (or set GOOGLE_API_KEY): ").strip()
    return api_key


def call_gemini(prompt, api_key, model="gemini-2.0-flash"):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "topK": 40, "topP": 0.95,
                             "maxOutputTokens": 8192},
    }
    resp = requests.post(f"{url}?key={api_key}",
                         headers={"Content-Type": "application/json"},
                         data=json.dumps(data), timeout=60)
    if resp.status_code != 200:
        print(f"Error calling Gemini API: {resp.status_code}\n{resp.text}")
        return None
    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        print(f"Error parsing Gemini response: {e}")
        return None


def strip_code_fences(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(lines).strip()
    return text + "\n"


def enhance_index(basic_index, site_name, api_key, model="gemini-2.0-flash"):
    print("Enhancing index with Gemini API...")
    prompt = f"""You are generating an llms.txt file following the official spec (llmstxt.org).

Given this raw site map of {site_name}, produce a spec-compliant llms.txt file.

STRICT FORMAT RULES — follow these exactly:
1. Line 1: # {site_name}
2. A blank line, then a single blockquote (>) with a 1-2 sentence summary of the site
3. Optionally, 1-2 plain paragraphs of additional context (NO headings here)
4. Then ## sections grouping related pages. Only use ## headings (H2), never ### or deeper
5. Inside each ## section: a markdown list where each item is:
   - [Page Title](https://full-url): Brief description of what this page contains
6. Include a ## Optional section at the end for lower-priority pages
7. Output ONLY the raw markdown. No code fences, no JSON metadata

CONTENT RULES:
- Preserve ALL original URLs exactly as given
- Group related pages logically (programs, student life, research, about, etc.)
- Write concise descriptions (under 15 words each) after the colon
- Merge duplicate or near-duplicate entries
- Put the most important pages first within each section

Here's the raw site map to enhance:

{basic_index}"""
    result = call_gemini(prompt, api_key, model=model)
    return strip_code_fences(result) if result else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate llms.txt files following the llmstxt.org spec")
    parser.add_argument("url", nargs="?", default="https://giesbusiness.illinois.edu",
                        help="Website URL to crawl")
    parser.add_argument("--name", default=None, help="Site name for the H1 title")
    parser.add_argument("--max-pages", type=int, default=150,
                        help="Maximum pages to crawl")
    parser.add_argument("--delay", type=float, default=0.2,
                        help="Delay between requests (seconds)")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--skip-enhance", action="store_true",
                        help="Skip the Gemini enhancement step")
    parser.add_argument("--full", action="store_true",
                        help="Also generate llms-full.txt with extracted page content")
    parser.add_argument("--gemini-model", default="gemini-2.0-flash",
                        help="Gemini model for enhancement")
    parser.add_argument("--ignore-robots", action="store_true",
                        help="Do not honor robots.txt (use responsibly)")
    args = parser.parse_args()

    name = args.name
    if not name:
        netloc = urlparse(args.url).netloc
        bits = netloc.split(".")
        name = (bits[-2] if len(bits) > 1 else netloc).capitalize()

    os.makedirs(args.output_dir, exist_ok=True)
    index_path = os.path.join(args.output_dir, "llms.txt")
    full_path = os.path.join(args.output_dir, "llms-full.txt")

    pages = crawl_site(args.url, max_pages=args.max_pages, delay=args.delay,
                       want_text=args.full, respect_robots=not args.ignore_robots)
    if not pages:
        print("No pages crawled — check the URL, robots.txt, or network.")
        return

    basic_index = build_index(pages, name, args.url)

    index_text = basic_index
    if not args.skip_enhance:
        try:
            api_key = get_gemini_api_key()
            if api_key:
                enhanced = enhance_index(basic_index, name, api_key,
                                         model=args.gemini_model)
                if enhanced:
                    index_text = enhanced
                else:
                    print("⚠️ Enhancement failed; writing basic index instead")
        except Exception as e:  # noqa: BLE001 - keep the basic output on any failure
            print(f"⚠️ Enhancement error ({e}); writing basic index instead")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_text)
    print(f"✅ Wrote {index_path} ({len(pages)} pages)")

    if args.full:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(build_full(pages, name, args.url))
        print(f"✅ Wrote {full_path} (page content for {len(pages)} pages)")


if __name__ == "__main__":
    main()
