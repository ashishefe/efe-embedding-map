"""
Scrape all blog posts from www.econforeverybody.com (Substack)
Strategy: Substack API archive endpoint (primary), sitemap fallback, HTML scrape fallback
"""

import json
import re
import time
import sys
import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

API_BASE = "https://www.econforeverybody.com/api/v1/archive"
SITE_BASE = "https://www.econforeverybody.com"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "substack_posts.json")

INTERNAL_DOMAINS = {
    "econforeverybodyblog.wordpress.com",
    "econforeverybody.com",
    "www.econforeverybody.com",
}

EXCLUDE_PATHS = {"/about", "/what-is-efe", "/contact", "/subscribe", "/archive", "/p"}


def normalize_url(url):
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def is_internal_post_link(url):
    parsed = urlparse(url)
    if parsed.netloc not in INTERNAL_DOMAINS:
        return False
    path = parsed.path.rstrip("/")
    if path in EXCLUDE_PATHS or path == "" or path == "/":
        return False
    return True


def extract_internal_links(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        url = a["href"]
        # Handle relative URLs
        if url.startswith("/"):
            url = SITE_BASE + url
        if is_internal_post_link(url):
            links.append(normalize_url(url))
    return list(set(links))


def strip_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # Remove Substack-specific widgets
    for cls in ["subscription-widget", "footer", "post-footer", "share-dialog"]:
        for el in soup.find_all(class_=re.compile(cls)):
            el.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text


def fetch_post_content(url):
    """Fetch full post content from a Substack post URL."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Substack post body is typically in a div with class containing "body"
        body = (
            soup.find("div", class_="body")
            or soup.find("div", class_="post-content")
            or soup.find("div", class_="available-content")
            or soup.find("article")
        )
        html_content = str(body) if body else ""
        internal_links = extract_internal_links(html_content)
        content_text = strip_html(html_content) if body else ""

        return content_text, internal_links
    except Exception as e:
        print(f"  Failed to fetch content from {url}: {e}")
        return "", []


def scrape_via_api():
    """Primary strategy: Substack API archive endpoint"""
    print("Attempting Substack API...")
    posts = []
    offset = 0
    batch_size = 50

    # Test the API
    try:
        test = requests.get(API_BASE, params={"sort": "new", "limit": 1, "offset": 0}, timeout=30)
        test.raise_for_status()
        test_data = test.json()
        if not isinstance(test_data, list):
            print(f"  API returned unexpected format: {type(test_data)}")
            return None
        print(f"  API accessible. First post: {test_data[0].get('title', 'N/A') if test_data else 'empty'}")
    except Exception as e:
        print(f"  API test failed: {e}")
        return None

    while True:
        try:
            resp = requests.get(
                API_BASE,
                params={"sort": "new", "limit": batch_size, "offset": offset},
                timeout=60,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            print(f"  API request failed at offset {offset}: {e}")
            if posts:
                return posts
            return None

        if not batch:
            break

        for ss_post in batch:
            post_url = ss_post.get("canonical_url", "") or f"{SITE_BASE}/p/{ss_post.get('slug', '')}"
            post_url = normalize_url(post_url)

            # Substack API usually includes post body HTML
            html_body = ss_post.get("body_html", "") or ""
            if html_body:
                internal_links = extract_internal_links(html_body)
                content_text = strip_html(html_body)
            else:
                # Need to fetch the page
                content_text, internal_links = fetch_post_content(post_url)
                time.sleep(1)

            date_str = ss_post.get("post_date", "") or ss_post.get("published_at", "") or ""
            if date_str:
                date_str = date_str[:19] + "Z"

            post = {
                "id": f"ss-{ss_post.get('id', offset)}",
                "title": ss_post.get("title", "").strip(),
                "url": post_url,
                "date": date_str,
                "content": content_text,
                "categories": [],
                "tags": [],
                "internal_links": internal_links,
                "source": "substack",
                "word_count": len(content_text.split()),
            }
            posts.append(post)

        offset += batch_size
        print(f"  Progress: {len(posts)} posts")
        time.sleep(1)

    print(f"  Completed: {len(posts)} posts scraped via API.")
    return posts


def scrape_via_sitemap():
    """Fallback strategy 1: Sitemap"""
    print("Attempting Substack sitemap...")
    sitemap_url = f"{SITE_BASE}/sitemap.xml"

    post_urls = []
    try:
        resp = requests.get(sitemap_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Check for sitemap index
        sitemaps = soup.find_all("sitemap")
        if sitemaps:
            for sm in sitemaps:
                loc = sm.find("loc")
                if loc:
                    sub_resp = requests.get(loc.text, timeout=30)
                    sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                    for url_tag in sub_soup.find_all("url"):
                        loc_tag = url_tag.find("loc")
                        if loc_tag and "/p/" in loc_tag.text:
                            post_urls.append(loc_tag.text)
                    time.sleep(1)
        else:
            for url_tag in soup.find_all("url"):
                loc_tag = url_tag.find("loc")
                if loc_tag and "/p/" in loc_tag.text:
                    post_urls.append(loc_tag.text)

        print(f"  Found {len(post_urls)} post URLs in sitemap.")
    except Exception as e:
        print(f"  Sitemap failed: {e}")
        return None

    if not post_urls:
        return None

    posts = []
    for i, url in enumerate(post_urls):
        content_text, internal_links = fetch_post_content(url)

        # Try to extract title and date from the page
        try:
            resp = requests.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""
            time_tag = soup.find("time")
            date_str = time_tag.get("datetime", "") if time_tag else ""
        except:
            title = ""
            date_str = ""

        post = {
            "id": f"ss-sitemap-{i}",
            "title": title,
            "url": normalize_url(url),
            "date": date_str[:19] + "Z" if date_str else "",
            "content": content_text,
            "categories": [],
            "tags": [],
            "internal_links": internal_links,
            "source": "substack",
            "word_count": len(content_text.split()),
        }
        posts.append(post)

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(post_urls)} posts")
        time.sleep(1)

    print(f"  Completed: {len(posts)} posts scraped via sitemap.")
    return posts


def scrape_via_archive_page():
    """Fallback strategy 2: HTML scrape of /archive"""
    print("Attempting HTML scrape of /archive page...")
    archive_url = f"{SITE_BASE}/archive"

    try:
        resp = requests.get(archive_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all post links on the archive page
        post_urls = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/p/" in href:
                if href.startswith("/"):
                    href = SITE_BASE + href
                post_urls.add(normalize_url(href))

        print(f"  Found {len(post_urls)} post URLs on archive page.")
    except Exception as e:
        print(f"  Archive page scrape failed: {e}")
        return None

    if not post_urls:
        return None

    posts = []
    for i, url in enumerate(sorted(post_urls)):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            body = (
                soup.find("div", class_="body")
                or soup.find("div", class_="post-content")
                or soup.find("div", class_="available-content")
                or soup.find("article")
            )
            html_content = str(body) if body else ""
            internal_links = extract_internal_links(html_content)
            content_text = strip_html(html_content) if body else ""

            time_tag = soup.find("time")
            date_str = time_tag.get("datetime", "") if time_tag else ""

            post = {
                "id": f"ss-archive-{i}",
                "title": title,
                "url": url,
                "date": date_str[:19] + "Z" if date_str else "",
                "content": content_text,
                "categories": [],
                "tags": [],
                "internal_links": internal_links,
                "source": "substack",
                "word_count": len(content_text.split()),
            }
            posts.append(post)

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{len(post_urls)} posts")
            time.sleep(1)
        except Exception as e:
            print(f"  Failed to scrape {url}: {e}")

    print(f"  Completed: {len(posts)} posts scraped via archive page.")
    return posts


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    posts = scrape_via_api()
    if not posts:
        posts = scrape_via_sitemap()
    if not posts:
        posts = scrape_via_archive_page()
    if not posts:
        print("ERROR: All Substack scraping strategies failed!")
        sys.exit(1)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(posts)} Substack posts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
