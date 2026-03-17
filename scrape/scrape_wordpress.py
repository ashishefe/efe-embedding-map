"""
Scrape all blog posts from econforeverybodyblog.wordpress.com
Strategy: WordPress.com REST API v1.1 (public, no auth needed)
Fallback: sitemap.xml, then month-archive crawling
"""

import json
import re
import time
import sys
import os
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

API_BASE = "https://public-api.wordpress.com/rest/v1.1/sites/econforeverybodyblog.wordpress.com/posts/"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "wordpress_posts.json")

# Domains that count as internal links
INTERNAL_DOMAINS = {
    "econforeverybodyblog.wordpress.com",
    "econforeverybody.com",
    "www.econforeverybody.com",
}

# Pages to exclude from internal links (not blog posts)
EXCLUDE_PATHS = {"/about", "/what-is-efe", "/contact", "/subscribe", "/archive"}


def normalize_url(url):
    """Strip query params, fragments, trailing slashes."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def is_internal_post_link(url):
    """Check if a URL points to a blog post on either platform."""
    parsed = urlparse(url)
    if parsed.netloc not in INTERNAL_DOMAINS:
        return False
    path = parsed.path.rstrip("/")
    if path in EXCLUDE_PATHS or path == "" or path == "/":
        return False
    # WordPress post URLs typically have date-based paths or slugs
    # Substack posts are at /p/slug
    return True


def extract_internal_links(html_content):
    """Extract internal links from post HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        url = a["href"]
        try:
            if is_internal_post_link(url):
                links.append(normalize_url(url))
        except (ValueError, Exception):
            # Skip malformed URLs (e.g. invalid IPv6)
            continue
    return list(set(links))  # deduplicate


def strip_html(html_content):
    """Convert HTML to clean text, preserving paragraph structure."""
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove script, style, nav elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # Remove sharing/related post widgets
    for cls in ["sharedaddy", "jp-relatedposts", "wpcnt", "post-likes-widget"]:
        for el in soup.find_all(class_=re.compile(cls)):
            el.decompose()
    text = soup.get_text(separator="\n")
    # Clean up whitespace
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text


def scrape_via_api():
    """Primary strategy: WordPress.com REST API v1.1"""
    posts = []
    offset = 0
    batch_size = 100
    total = None

    print("Attempting WordPress.com REST API v1.1...")

    # Test the API first
    try:
        test = requests.get(API_BASE, params={"number": 1}, timeout=30)
        test.raise_for_status()
        total = test.json().get("found", 0)
        print(f"  API accessible. Total posts found: {total}")
    except Exception as e:
        print(f"  API test failed: {e}")
        return None

    while True:
        params = {"number": batch_size, "offset": offset, "order_by": "date", "order": "ASC"}
        try:
            resp = requests.get(API_BASE, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  API request failed at offset {offset}: {e}")
            if posts:
                print(f"  Returning {len(posts)} posts scraped so far.")
                return posts
            return None

        batch = data.get("posts", [])
        if not batch:
            break

        for wp_post in batch:
            html_content = wp_post.get("content", "")
            internal_links = extract_internal_links(html_content)
            content_text = strip_html(html_content)

            categories = list(wp_post.get("categories", {}).keys())
            tags = list(wp_post.get("tags", {}).keys())

            post = {
                "id": f"wp-{wp_post['ID']}",
                "title": wp_post.get("title", "").strip(),
                "url": normalize_url(wp_post.get("URL", "")),
                "date": wp_post.get("date", "")[:19] + "Z" if wp_post.get("date") else "",
                "content": content_text,
                "categories": categories,
                "tags": tags,
                "internal_links": internal_links,
                "source": "wordpress",
                "word_count": len(content_text.split()),
            }
            posts.append(post)

        offset += batch_size
        if len(posts) % 50 == 0 or len(posts) >= (total or float("inf")):
            print(f"  Progress: {len(posts)}/{total or '?'} posts")
        time.sleep(1)  # Rate limiting

    print(f"  Completed: {len(posts)} posts scraped via API.")
    return posts


def scrape_via_sitemap():
    """Fallback strategy 1: Sitemap crawling"""
    print("Attempting sitemap scraping...")
    sitemap_urls = [
        "https://econforeverybodyblog.wordpress.com/sitemap.xml",
        "https://econforeverybodyblog.wordpress.com/wp-sitemap.xml",
    ]

    post_urls = []
    for sitemap_url in sitemap_urls:
        try:
            resp = requests.get(sitemap_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Check for sitemap index
            sitemaps = soup.find_all("sitemap")
            if sitemaps:
                for sm in sitemaps:
                    loc = sm.find("loc")
                    if loc and "post" in loc.text.lower():
                        sub_resp = requests.get(loc.text, timeout=30)
                        sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                        for url_tag in sub_soup.find_all("url"):
                            loc_tag = url_tag.find("loc")
                            if loc_tag:
                                post_urls.append(loc_tag.text)
                        time.sleep(1)
            else:
                for url_tag in soup.find_all("url"):
                    loc_tag = url_tag.find("loc")
                    if loc_tag:
                        post_urls.append(loc_tag.text)
            if post_urls:
                print(f"  Found {len(post_urls)} URLs in sitemap.")
                break
        except Exception as e:
            print(f"  Sitemap {sitemap_url} failed: {e}")

    if not post_urls:
        print("  No sitemap URLs found.")
        return None

    # Scrape each post page
    posts = []
    for i, url in enumerate(post_urls):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("h1", class_="entry-title") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            # Find post content
            content_div = soup.find("div", class_="entry-content") or soup.find("article")
            html_content = str(content_div) if content_div else ""
            internal_links = extract_internal_links(html_content)
            content_text = strip_html(html_content) if content_div else ""

            # Date
            time_tag = soup.find("time")
            date_str = time_tag.get("datetime", "") if time_tag else ""

            post = {
                "id": f"wp-sitemap-{i}",
                "title": title,
                "url": normalize_url(url),
                "date": date_str[:19] + "Z" if date_str else "",
                "content": content_text,
                "categories": [],
                "tags": [],
                "internal_links": internal_links,
                "source": "wordpress",
                "word_count": len(content_text.split()),
            }
            posts.append(post)

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{len(post_urls)} posts")
            time.sleep(1)
        except Exception as e:
            print(f"  Failed to scrape {url}: {e}")

    print(f"  Completed: {len(posts)} posts scraped via sitemap.")
    return posts


def scrape_via_archives():
    """Fallback strategy 2: Month archive crawling"""
    print("Attempting month archive crawling...")
    base_url = "https://econforeverybodyblog.wordpress.com"
    post_urls = set()

    # Crawl monthly archives from 2017/05 through 2026/03
    for year in range(2017, 2027):
        for month in range(1, 13):
            if year == 2017 and month < 5:
                continue
            if year == 2026 and month > 3:
                break

            archive_url = f"{base_url}/{year:04d}/{month:02d}/"
            try:
                resp = requests.get(archive_url, timeout=30)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    parsed = urlparse(href)
                    if parsed.netloc == "econforeverybodyblog.wordpress.com":
                        # Post URLs typically have date structure: /YYYY/MM/DD/slug/
                        if re.match(r"/\d{4}/\d{2}/\d{2}/", parsed.path):
                            post_urls.add(normalize_url(href))

                print(f"  {year}/{month:02d}: {len(post_urls)} unique post URLs so far")
                time.sleep(1)
            except Exception as e:
                print(f"  Archive {year}/{month:02d} failed: {e}")

    if not post_urls:
        return None

    print(f"  Found {len(post_urls)} unique post URLs. Scraping each...")

    # Now scrape each post (same logic as sitemap fallback)
    posts = []
    for i, url in enumerate(sorted(post_urls)):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            title_tag = soup.find("h1", class_="entry-title") or soup.find("title")
            title = title_tag.get_text().strip() if title_tag else ""

            content_div = soup.find("div", class_="entry-content") or soup.find("article")
            html_content = str(content_div) if content_div else ""
            internal_links = extract_internal_links(html_content)
            content_text = strip_html(html_content) if content_div else ""

            time_tag = soup.find("time")
            date_str = time_tag.get("datetime", "") if time_tag else ""

            post = {
                "id": f"wp-archive-{i}",
                "title": title,
                "url": normalize_url(url),
                "date": date_str[:19] + "Z" if date_str else "",
                "content": content_text,
                "categories": [],
                "tags": [],
                "internal_links": internal_links,
                "source": "wordpress",
                "word_count": len(content_text.split()),
            }
            posts.append(post)

            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{len(post_urls)} posts")
            time.sleep(1)
        except Exception as e:
            print(f"  Failed to scrape {url}: {e}")

    print(f"  Completed: {len(posts)} posts scraped via archives.")
    return posts


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Try strategies in order
    posts = scrape_via_api()
    if not posts:
        posts = scrape_via_sitemap()
    if not posts:
        posts = scrape_via_archives()
    if not posts:
        print("ERROR: All scraping strategies failed!")
        sys.exit(1)

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(posts)} WordPress posts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
