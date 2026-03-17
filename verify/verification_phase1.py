import json
import sys
from datetime import datetime


def verify_phase1(filepath="data/posts.json"):
    with open(filepath) as f:
        posts = json.load(f)

    errors = []
    warnings = []

    # CHECK 1: Minimum post count
    if len(posts) < 500:
        errors.append(f"Only {len(posts)} posts found. Expected 1000+. Scraping likely incomplete.")
    elif len(posts) < 1000:
        warnings.append(f"{len(posts)} posts found. Expected 1000+. Some posts may be missing.")

    # CHECK 2: Required fields present on every post
    required = ["id", "title", "url", "date", "content", "source"]
    for i, p in enumerate(posts):
        for field in required:
            if field not in p or not p[field]:
                errors.append(f"Post {i} missing required field: {field}")

    # CHECK 3: Date range spans expected period
    dates = sorted([p["date"] for p in posts if p.get("date")])
    if dates:
        earliest = dates[0][:4]
        latest = dates[-1][:4]
        if int(earliest) > 2018:
            warnings.append(f"Earliest post is from {earliest}. Expected posts from 2017.")
        if int(latest) < 2025:
            warnings.append(f"Latest post is from {latest}. Expected posts from 2025-2026.")

    # CHECK 4: Both sources represented
    sources = set(p.get("source") for p in posts)
    if "wordpress" not in sources and "both" not in sources:
        errors.append("No WordPress posts found. WordPress scraping likely failed.")
    if "substack" not in sources and "both" not in sources:
        warnings.append("No Substack posts found. Substack scraping may have failed.")

    # CHECK 5: Content is substantive (not just titles or stubs)
    short_posts = [p for p in posts if len(p.get("content", "")) < 200]
    if len(short_posts) > len(posts) * 0.2:
        errors.append(f"{len(short_posts)} posts have <200 chars of content. Content extraction may be broken.")

    # CHECK 6: No duplicate URLs
    urls = [p["url"] for p in posts]
    dupes = [u for u in set(urls) if urls.count(u) > 1]
    if dupes:
        errors.append(f"{len(dupes)} duplicate URLs found. Dedup incomplete.")

    # CHECK 7: Internal links are well-formed URLs
    total_links = sum(len(p.get("internal_links", [])) for p in posts)
    bad_links = 0
    for p in posts:
        for link in p.get("internal_links", []):
            if not link.startswith("http"):
                bad_links += 1
    if bad_links > 0:
        warnings.append(f"{bad_links} internal links are not full URLs.")

    # REPORT
    print(f"\n{'='*60}")
    print(f"PHASE 1 VERIFICATION REPORT")
    print(f"{'='*60}")
    print(f"Total posts: {len(posts)}")
    print(f"WordPress: {sum(1 for p in posts if p['source'] in ('wordpress','both'))}")
    print(f"Substack: {sum(1 for p in posts if p['source'] in ('substack','both'))}")
    print(f"Both: {sum(1 for p in posts if p['source'] == 'both')}")
    print(f"Date range: {dates[0][:10] if dates else 'N/A'} to {dates[-1][:10] if dates else 'N/A'}")
    print(f"Total internal links: {total_links}")
    print(f"Avg content length: {sum(len(p.get('content','')) for p in posts)//max(len(posts),1)} chars")
    print(f"\nErrors: {len(errors)}")
    for e in errors:
        print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")

    return len(errors) == 0


if __name__ == "__main__":
    sys.exit(0 if verify_phase1() else 1)
