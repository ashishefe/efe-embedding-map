"""
Merge WordPress and Substack posts, deduplicate cross-posted content.
Output: data/posts.json
"""

import json
import os
import sys
from difflib import SequenceMatcher

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
WP_PATH = os.path.join(DATA_DIR, "wordpress_posts.json")
SS_PATH = os.path.join(DATA_DIR, "substack_posts.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "posts.json")


def load_json(path):
    if not os.path.exists(path):
        print(f"Warning: {path} not found. Returning empty list.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def titles_match(t1, t2):
    """Case-insensitive exact title match."""
    return t1.strip().lower() == t2.strip().lower()


def content_overlap(c1, c2, threshold=0.8):
    """Check if first 500 chars have >threshold overlap."""
    s1 = c1[:500].strip()
    s2 = c2[:500].strip()
    if not s1 or not s2:
        return False
    ratio = SequenceMatcher(None, s1, s2).ratio()
    return ratio > threshold


def same_day(d1, d2):
    """Check if two date strings share the same day."""
    return d1[:10] == d2[:10] and len(d1) >= 10 and len(d2) >= 10


def merge_posts(wp_post, ss_post):
    """Merge a duplicate pair: Substack URL primary, WordPress metadata."""
    merged = {
        "id": ss_post["id"],  # Use Substack ID as primary
        "title": ss_post["title"] or wp_post["title"],
        "url": ss_post["url"],  # Substack URL as primary
        "alt_url": wp_post["url"],  # WordPress URL as alt
        "date": ss_post["date"] or wp_post["date"],
        # Keep whichever content is longer
        "content": ss_post["content"] if len(ss_post.get("content", "")) >= len(wp_post.get("content", "")) else wp_post["content"],
        # Merge categories and tags from WordPress (Substack typically has none)
        "categories": list(set(wp_post.get("categories", []) + ss_post.get("categories", []))),
        "tags": list(set(wp_post.get("tags", []) + ss_post.get("tags", []))),
        # Merge internal links
        "internal_links": list(set(wp_post.get("internal_links", []) + ss_post.get("internal_links", []))),
        "source": "both",
        "word_count": max(wp_post.get("word_count", 0), ss_post.get("word_count", 0)),
    }
    return merged


def main():
    wp_posts = load_json(WP_PATH)
    ss_posts = load_json(SS_PATH)

    print(f"WordPress posts: {len(wp_posts)}")
    print(f"Substack posts: {len(ss_posts)}")

    # Find duplicates
    matched_wp = set()
    matched_ss = set()
    merged = []

    for si, ss in enumerate(ss_posts):
        for wi, wp in enumerate(wp_posts):
            if wi in matched_wp:
                continue

            is_dup = False
            # Rule 1: Exact title match
            if titles_match(ss.get("title", ""), wp.get("title", "")):
                is_dup = True
            # Rule 2: Same day + content overlap
            elif same_day(ss.get("date", ""), wp.get("date", "")) and \
                 content_overlap(ss.get("content", ""), wp.get("content", "")):
                is_dup = True

            if is_dup:
                merged.append(merge_posts(wp, ss))
                matched_wp.add(wi)
                matched_ss.add(si)
                break

    print(f"Duplicates found: {len(merged)}")

    # Add remaining unmatched posts
    all_posts = list(merged)
    for wi, wp in enumerate(wp_posts):
        if wi not in matched_wp:
            wp["alt_url"] = None
            all_posts.append(wp)
    for si, ss in enumerate(ss_posts):
        if si not in matched_ss:
            ss["alt_url"] = None
            all_posts.append(ss)

    # Sort by date
    all_posts.sort(key=lambda p: p.get("date", ""))

    # Verify no duplicate URLs
    urls = [p["url"] for p in all_posts]
    dupe_urls = [u for u in set(urls) if urls.count(u) > 1]
    if dupe_urls:
        print(f"WARNING: {len(dupe_urls)} duplicate URLs remain after dedup!")
        for u in dupe_urls[:5]:
            print(f"  {u}")

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\nTotal merged posts: {len(all_posts)}")
    print(f"  WordPress only: {sum(1 for p in all_posts if p['source'] == 'wordpress')}")
    print(f"  Substack only: {sum(1 for p in all_posts if p['source'] == 'substack')}")
    print(f"  Both: {sum(1 for p in all_posts if p['source'] == 'both')}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
