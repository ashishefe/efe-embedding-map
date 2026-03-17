# EconForEverybody Blog Embedding Map — Claude Code Instruction Set

## 0. Project Identity

**What**: An interactive embedding visualization of every blog post from econforeverybody.com — a blog by Ashish Kulkarni spanning 2017–2026 across economics, education, philosophy, AI, and alignment.

**Why**: Not just "here are my posts clustered by topic." This is a visual argument for integrative thinking — the map reveals how economics connects to alignment, how Pirsig meets Coase, how pedagogy bridges to AI. The most interesting features are the *bridges between clusters*, not the clusters themselves.

**Who sees this**: Intellectually curious readers, potential collaborators, students. It will eventually live at a subdomain of econforeverybody.com. It must look like something a thoughtful writer would be proud to have on their site — not like a data science notebook output.

**Inspiration**: [S Anand's blog embedding map](http://www.s-anand.net/blog/blog-embeddings-map/). We are building something richer: time animation, internal link graph, and a "journey" mode for readers.

---

## 1. Architecture Overview

```
Phase 1: Scrape & Extract ──→ posts.json
Phase 2: Embed & Reduce   ──→ posts_with_coords.json
Phase 3: Interactive Map   ──→ index.html (core visualization)
Phase 4: Time Animation    ──→ adds time slider + playback
Phase 5: Edge Overlay      ──→ adds internal link graph
Phase 6: Journey Mode      ──→ adds guided reading paths
```

Each phase has:
- **Clear inputs and outputs** (file names, data shapes)
- **A verification agent** that runs automated checks before the phase is considered complete
- **A human checkpoint** (where the user should review before proceeding)

**CRITICAL RULE: Build and verify each phase before starting the next. Do NOT skip verification. Do NOT combine phases.**

---

## 2. Skill & Tool Guidance

Before writing ANY frontend code, read the frontend-design skill. In Claude Code's environment, look for a frontend-design skill in your available skills (typically at a path like `/mnt/skills/public/frontend-design/SKILL.md` or similar — run `find / -name "SKILL.md" 2>/dev/null | grep frontend` if unsure). If no such skill exists in your environment, follow the design direction below with extra diligence.

This is non-negotiable. The visualization must avoid generic AI aesthetics. Specifically:

### Design Direction: "Editorial Cartography"

The aesthetic is **a beautifully designed editorial map** — think of the visual language of The Pudding, Observable notebooks at their best, or the New York Times interactive features. NOT a Plotly default scatter plot. NOT a Jupyter notebook.

**Typography**: Use a distinctive display font for titles/headers (e.g., Playfair Display, Fraunces, or Newsreader — something with editorial character) paired with a clean sans-serif for UI elements and body text (e.g., DM Sans, Source Sans 3, Outfit). Load from Google Fonts CDN. NEVER use Inter, Roboto, Arial, or system defaults.

**Color**: 
- Background: A warm, slightly off-white or very dark charcoal (NOT pure white, NOT pure black). Think aged paper or dark ink.
- Cluster colors: Use a carefully curated qualitative palette — not D3 defaults. Consider palettes from ColorBrewer "Set2" or "Dark2", or hand-pick 10–12 colors that feel cohesive. Test for colorblind accessibility (no red-green pairs). Each color should feel like it belongs in the same room.
- Accent color: One strong accent (warm gold, deep teal, or burnt orange) for highlights, active states, and the search feature.
- Edges: Subtle, desaturated. Cross-cluster edges get the accent color.

**Layout**: The map should take center stage — full viewport width, with UI controls overlaid as floating panels with soft shadows and blur backgrounds (glassmorphism, done tastefully). The legend should be a collapsible sidebar, not a separate block.

**Micro-interactions**: 
- Points should have subtle hover scaling (1.0 → 1.3x) with a smooth ease-out.
- Tooltip appears with a slight fade-in, positioned to avoid viewport edges.
- Clicking a point should produce a brief pulse animation before opening the post.
- The time slider should feel physical — smooth, with momentum.

**Overall vibe**: This should feel like a piece of data journalism, not a dashboard. Someone should look at it and think "this was made by someone who cares about both ideas and craft."

---

## 3. Data Sources

The blog lives on TWO platforms that must be merged:

| Platform | URL | Era | Metadata |
|----------|-----|-----|----------|
| WordPress | `econforeverybodyblog.wordpress.com` | 2017–2025 | Categories, tags, rich HTML |
| Substack | `www.econforeverybody.com` | ~2024–2026 | Minimal taxonomy |

Expected total: 1,000–2,000+ posts.

---

## 4. Phase Specifications

### PHASE 1: Scrape & Extract

**Output**: `data/posts.json`

#### 1a: WordPress Scraping

The WordPress blog is on wordpress.com (free tier), not self-hosted. There is no authenticated REST API.

**Strategy** (try in order):
1. Fetch sitemap at `econforeverybodyblog.wordpress.com/sitemap.xml` or `wp-sitemap.xml`
2. If sitemap is inaccessible, use the WordPress.com REST API v1.1 (public, no auth needed):
   `https://public-api.wordpress.com/rest/v1.1/sites/econforeverybodyblog.wordpress.com/posts/?number=100&offset=0`
   Paginate by incrementing `offset` by 100 until `found` is exhausted.
3. If API fails, crawl month archives: `econforeverybodyblog.wordpress.com/YYYY/MM/` from `2017/05/` through `2025/09/`

**For each post, extract:**
```json
{
  "id": "wp-123",
  "title": "On The Economics of Line Cutting",
  "url": "https://econforeverybodyblog.wordpress.com/2022/06/09/on-the-economics-of-line-cutting/",
  "date": "2022-06-09T00:00:00Z",
  "content": "Full post text, HTML stripped, navigation/boilerplate removed. Keep prose, block quotes, and embedded text. Strip share buttons, related posts, author bios.",
  "categories": ["Intro", "Micro"],
  "tags": ["demand and supply", "behavioral economics"],
  "internal_links": ["https://econforeverybodyblog.wordpress.com/2017/06/14/complements-and-substitutes/"],
  "source": "wordpress",
  "word_count": 1247
}
```

**Internal links**: Extract all `<a href>` within the post body that point to either `econforeverybodyblog.wordpress.com` or `econforeverybody.com` or `www.econforeverybody.com`. Normalize URLs (strip query params, trailing slashes). Only include links to blog posts (not pages like "About" or "What is EFE?").

**Rate limiting**: 1-second delay between requests. Log progress every 50 posts.

#### 1b: Substack Scraping

**Strategy** (try in order):
1. Substack API: `https://www.econforeverybody.com/api/v1/archive?sort=new&limit=50&offset=0`. Paginate by incrementing `offset`.
2. If API fails, fetch sitemap at `www.econforeverybody.com/sitemap.xml`
3. If sitemap fails, scrape the archive page at `www.econforeverybody.com/archive`

Same field extraction as WordPress. Substack posts will likely have empty `categories` and `tags` arrays — that's fine.

#### 1c: Merge & Deduplicate

Posts may exist on both platforms (cross-posted during migration ~2024-2025).

**Dedup rules** (in order):
1. Exact title match (case-insensitive, stripped of leading/trailing whitespace)
2. Same-day publication date + >80% overlap in first 500 characters (use difflib.SequenceMatcher)

When merging a duplicate: keep Substack URL as primary, WordPress URL as `alt_url`, merge categories/tags from WordPress, keep whichever content is longer, set `source: "both"`.

#### PHASE 1 VERIFICATION AGENT

After completing scraping and merging, run the following checks automatically. **Do NOT proceed to Phase 2 until ALL checks pass.**

```python
# verification_phase1.py
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
    if "wordpress" not in sources:
        errors.append("No WordPress posts found. WordPress scraping likely failed.")
    if "substack" not in sources:
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
    print(f"Avg content length: {sum(len(p.get('content','')) for p in posts)//len(posts)} chars")
    print(f"\nErrors: {len(errors)}")
    for e in errors: print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings: print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase1() else 1)
```

**Human checkpoint**: After verification passes, show the user the report and a sample of 5 random posts (title + date + first 100 chars + source). Ask: "Does this look right? Any posts you know are missing?"

---

### PHASE 2: Embed & Reduce

**Inputs**: `data/posts.json`
**Outputs**: `data/embeddings.npy`, `data/posts_with_coords.json`

#### 2a: Generate Embeddings

- Use the **Gemini Embedding API**.
  - Model: `gemini-embedding-exp-03-07` (or latest available; check docs at `https://ai.google.dev/gemini-api/docs/embeddings`)
  - API key from environment variable: `GEMINI_API_KEY`
- For each post, embed: `"{title}\n\n{content[:8000]}"` (title-prefixed, truncated to 8000 chars)
- Batch in groups of 50–100 (check Gemini batch limits). Retry with exponential backoff on rate limits (start 2s, max 60s, 5 retries).
- **SAVE PROGRESS INCREMENTALLY**: After each batch, append the new embeddings to a running file. If the process crashes at post 800 of 1500, you must be able to resume from post 801. Implement this by:
  1. Maintaining a `data/embedding_progress.json` that tracks which post IDs have been embedded
  2. On startup, check this file and skip already-embedded posts
  3. After all posts are done, assemble the final `data/embeddings.npy`
- Save as `data/embeddings.npy` (numpy float32 array, shape `[n_posts, embedding_dim]`)
- Also save `data/embedding_order.json` — list of post IDs in the same order as rows in the numpy array, so we can always match them back.

#### 2b: UMAP Reduction

```python
import umap
import numpy as np

embeddings = np.load("data/embeddings.npy")

reducer = umap.UMAP(
    n_neighbors=15,
    min_dist=0.1,
    metric='cosine',
    random_state=42
)
coords_2d = reducer.fit_transform(embeddings)
```

Normalize the 2D coordinates to a [0, 1000] range for both x and y (makes frontend rendering simpler).

#### 2c: Topic Clustering

Use HDBSCAN on the **high-dimensional** embeddings (NOT the 2D UMAP output — that loses information):

```python
import hdbscan

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=15,
    min_samples=5,
    metric='euclidean'
)
labels = clusterer.fit_predict(embeddings)
```

For each cluster (excluding noise label -1), generate a human-readable label:
1. Find the 10 posts closest to the cluster centroid.
2. Send their titles to an LLM with the prompt:
   ```
   These are blog post titles from the same thematic cluster on an economics/AI/philosophy blog:
   {titles}
   Give this cluster a short, evocative 2–4 word label. It should feel like a section heading in a thoughtful magazine, not a database category. Examples: "Behavioral Nudges", "India's AI Strategy", "Philosophy of Consciousness", "Teaching With AI", "Coase & Transaction Costs".
   Return ONLY the label, nothing else.
   ```
3. Posts with label -1 (HDBSCAN noise) → label "Miscellaneous"

**Color assignment**: Hand-assign or algorithmically assign colors from this curated palette (designed for colorblind accessibility on both light and dark backgrounds):

```
#4E79A7  (steel blue)
#F28E2B  (tangerine)
#E15759  (coral red)
#76B7B2  (teal)
#59A14F  (forest green)
#EDC948  (gold)
#B07AA1  (lavender)
#FF9DA7  (pink)
#9C755F  (sienna)
#BAB0AC  (warm gray)
#AF7AA1  (mauve)
#86BCB6  (sage)
```

If more than 12 clusters, extend by lightening/darkening these base colors.

#### 2d: Assemble Final Dataset

Merge coordinates, cluster info, and metadata into `data/posts_with_coords.json`:

```json
[
  {
    "id": "wp-123",
    "title": "On The Economics of Line Cutting",
    "url": "https://econforeverybodyblog.wordpress.com/2022/06/09/on-the-economics-of-line-cutting/",
    "alt_url": null,
    "date": "2022-06-09",
    "x": 342.7,
    "y": 618.2,
    "cluster_id": 3,
    "cluster_label": "Behavioral Economics",
    "cluster_color": "#F28E2B",
    "source": "wordpress",
    "word_count": 1247,
    "internal_links": ["wp-45", "wp-88"],
    "snippet": "First 150 characters of the post for tooltip display..."
  }
]
```

**IMPORTANT**: The `internal_links` field should now be a list of post **IDs** (not URLs), resolved from the URL-based links in Phase 1. Links to posts not in the dataset should be dropped.

#### PHASE 2 VERIFICATION AGENT

```python
# verification_phase2.py
import json
import numpy as np
import sys

def verify_phase2():
    posts = json.load(open("data/posts_with_coords.json"))
    embeddings = np.load("data/embeddings.npy")
    
    errors = []
    warnings = []
    
    # CHECK 1: Dimensions match
    if embeddings.shape[0] != len(posts):
        errors.append(f"Embedding count ({embeddings.shape[0]}) != post count ({len(posts)})")
    
    # CHECK 2: No NaN in coordinates
    nan_count = sum(1 for p in posts if p.get("x") is None or p.get("y") is None)
    if nan_count > 0:
        errors.append(f"{nan_count} posts have null coordinates")
    
    # CHECK 3: Coordinates are in expected range
    xs = [p["x"] for p in posts if p.get("x") is not None]
    ys = [p["y"] for p in posts if p.get("y") is not None]
    if max(xs) - min(xs) < 10:
        errors.append("X coordinate range is suspiciously narrow. UMAP may have collapsed.")
    
    # CHECK 4: Cluster distribution is reasonable
    from collections import Counter
    cluster_counts = Counter(p.get("cluster_id") for p in posts)
    n_clusters = len([k for k in cluster_counts if k != -1])
    noise_pct = cluster_counts.get(-1, 0) / len(posts) * 100
    
    if n_clusters < 4:
        warnings.append(f"Only {n_clusters} clusters found. Consider lowering min_cluster_size.")
    if n_clusters > 25:
        warnings.append(f"{n_clusters} clusters found. Consider raising min_cluster_size.")
    if noise_pct > 40:
        warnings.append(f"{noise_pct:.0f}% of posts are noise. Consider lowering min_cluster_size.")
    
    # CHECK 5: Every cluster has a label and color
    for p in posts:
        if p.get("cluster_id") is not None and p["cluster_id"] != -1:
            if not p.get("cluster_label"):
                errors.append(f"Post {p['id']} in cluster {p['cluster_id']} has no cluster_label")
            if not p.get("cluster_color"):
                errors.append(f"Post {p['id']} in cluster {p['cluster_id']} has no cluster_color")
    
    # CHECK 6: Internal links resolve to valid post IDs
    valid_ids = set(p["id"] for p in posts)
    broken_links = 0
    for p in posts:
        for link_id in p.get("internal_links", []):
            if link_id not in valid_ids:
                broken_links += 1
    if broken_links > 0:
        warnings.append(f"{broken_links} internal links point to posts not in the dataset (already dropped, just noting).")
    
    # CHECK 7: Snippet exists for tooltip
    no_snippet = sum(1 for p in posts if not p.get("snippet"))
    if no_snippet > len(posts) * 0.1:
        warnings.append(f"{no_snippet} posts have no snippet for tooltip display.")
    
    # REPORT
    print(f"\n{'='*60}")
    print(f"PHASE 2 VERIFICATION REPORT")
    print(f"{'='*60}")
    print(f"Posts: {len(posts)}")
    print(f"Embedding dimensions: {embeddings.shape[1]}")
    print(f"Clusters: {n_clusters} (+ noise: {cluster_counts.get(-1, 0)} posts)")
    print(f"Cluster sizes: {dict(sorted(cluster_counts.items(), key=lambda x: -x[1]))}")
    print(f"Coordinate range: x=[{min(xs):.1f}, {max(xs):.1f}], y=[{min(ys):.1f}, {max(ys):.1f}]")
    
    print(f"\nCluster labels:")
    labels_seen = {}
    for p in posts:
        cid = p.get("cluster_id")
        if cid not in labels_seen and cid != -1:
            labels_seen[cid] = p.get("cluster_label", "???")
    for cid, label in sorted(labels_seen.items()):
        print(f"  {cid}: {label} ({cluster_counts[cid]} posts)")
    
    print(f"\nErrors: {len(errors)}")
    for e in errors: print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings: print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase2() else 1)
```

**Human checkpoint**: Show the user the cluster labels and their sizes. Ask: "Do these clusters make sense given your blog? Any that should be split or merged?"

---

### PHASE 3: Interactive Map (Core Visualization)

**Input**: `data/posts_with_coords.json`
**Output**: `viz/index.html` — a single, self-contained HTML file

#### Technology Choice

Build as a **single HTML file** with vanilla JS + Canvas (for performance with 1000+ points) + D3.js (for scales, zoom behavior, and force layout if needed). Load D3 from CDN.

Do NOT use: Plotly (too opinionated, hard to customize), React (unnecessary build step), chart.js (wrong tool for scatter with this many interactions).

**Before writing any code, read:**
```
/mnt/skills/public/frontend-design/SKILL.md
```
Apply the design direction from Section 2 of this document rigorously.

#### Core Features

**A. The Map**
- Full viewport canvas, edge-to-edge
- Each post is a circle at its UMAP (x, y) coordinates
- Circle radius: 4px default, 6px on hover, 8px when search-highlighted
- Color = cluster color (from data)
- Canvas zoom + pan (D3 zoom behavior on canvas)
- On zoom, dynamically adjust point size to maintain visual density

**B. Hover Tooltip**
- Appears on hover near the cursor (offset so it doesn't occlude the point)
- Shows: **Title** (bold, display font) / Date / Cluster label / Snippet (first 150 chars)
- Styled as a card with subtle shadow and backdrop blur
- Fades in (150ms), repositions to stay within viewport
- On mobile: triggered by tap (first tap = tooltip, second tap = open link)

**C. Click → Open Post**
- Clicking a point opens the post URL in a new tab (`window.open(url, '_blank')`)
- Before opening, play a brief pulse animation on the clicked point (scale up + fade, 300ms)
- If the post has an `alt_url` (exists on both platforms), prefer the Substack URL
- **CRITICAL UX DETAIL**: The click target must be generous — not just the 4px circle, but a 20px radius hitbox around it. On dense areas of the map, clicking should open the NEAREST post to the click point. Use a spatial index (quadtree via D3) for efficient nearest-neighbor lookup.
- **Mobile**: First tap shows tooltip, second tap on the same point opens the URL. A tap on a different point shows that point's tooltip. Implement this as a two-state interaction: tap → select (highlight + tooltip), tap same → open. This avoids the problem of accidentally opening links while trying to explore.
- **Accessibility**: Each point should have an aria-label with the post title. The tooltip should be reachable via keyboard (Tab to navigate points, Enter to open).

**D. Legend (Collapsible Sidebar)**
- Left sidebar, collapsible to a small icon
- Lists each cluster: color swatch + label + post count
- Clicking a cluster label toggles that cluster's visibility (fade to 5% opacity, don't remove — the user should still see the ghost of where those posts are)
- "Show all" / "Hide all" buttons
- Current filter state displayed as "Showing X of Y posts"

**E. Search**
- Search input at top of sidebar (or as a floating bar)
- Filters in real-time as the user types (debounced, 200ms)
- Matching posts: full opacity + enlarged (6px)
- Non-matching posts: 10% opacity
- Search matches against: title (primary), snippet (secondary)
- Show match count: "12 posts match 'Coase'"
- Clear button to reset

**F. Source Indicator**
- Posts from WordPress: circle
- Posts from Substack: circle with a subtle ring/outline
- Posts from both: circle with a dot in the center
- This is a subtle distinction, not primary. Don't overdesign it.

**G. "About This Map" Explainer**
- A small "?" or "About" button in the corner that opens a modal/overlay
- The explainer should be written for a smart non-technical reader. It should explain:
  - What the map is: "Each dot is a blog post. Posts that are about similar topics are placed closer together."
  - How it was made: "An AI model read every post and converted it into a numerical 'fingerprint' of its meaning. A technique called UMAP arranged these fingerprints on a 2D plane so that similar posts land near each other."
  - What the colors mean: "Posts are automatically grouped into thematic clusters by another algorithm (HDBSCAN). The colors represent these discovered themes — they weren't chosen by hand."
  - What the connecting lines mean (if edges are visible): "Lines connect posts that explicitly link to each other. Colored lines bridge different topic clusters — these are the intellectual connections between ideas."
- Style this as a clean, readable card with generous line-height. Use the display font for the heading, body font for the text.
- Include a "Built with ♦ inspired by S Anand's blog embedding map" credit line at the bottom.

#### Data Loading

The HTML file must support TWO modes:
1. **Standalone** (local file): Data inlined as `const POSTS = [...]` in a `<script>` tag
2. **Hosted** (web server): Data loaded via `fetch("posts_with_coords.json")` from same directory

Use a pattern like:
```javascript
const POSTS = window.__INLINE_DATA__ || null;
async function loadData() {
    if (POSTS) return POSTS;
    const resp = await fetch("posts_with_coords.json");
    return resp.json();
}
```

For the local version, generate a version with the data inlined. For the hosted version, generate a version that fetches externally. Provide a simple build script that switches between modes.

#### PHASE 3 VERIFICATION AGENT

This is more complex because we're verifying a UI. Run these checks:

```python
# verification_phase3.py
import os, sys, json, re

def verify_phase3():
    errors = []
    warnings = []
    
    html_path = "viz/index.html"
    
    # CHECK 1: File exists and is substantial
    if not os.path.exists(html_path):
        errors.append("viz/index.html does not exist")
        return False
    
    size = os.path.getsize(html_path)
    if size < 50000:
        warnings.append(f"HTML file is only {size} bytes. Might be missing data or features.")
    
    with open(html_path) as f:
        html = f.read()
    
    # CHECK 2: No default/generic fonts
    generic_fonts = ["Inter", "Roboto", "Arial", "system-ui", "sans-serif"]
    for font in generic_fonts:
        # Only flag if it's used as a PRIMARY font (not in a fallback stack after a distinctive font)
        if re.search(rf'font-family:\s*["\']?{font}', html, re.IGNORECASE):
            warnings.append(f"Generic font '{font}' may be used as primary font. Ensure a distinctive display font is primary.")
    
    # CHECK 3: Google Fonts loaded (evidence of custom typography)
    if "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html:
        warnings.append("No Google Fonts detected. Custom typography may be missing.")
    
    # CHECK 4: Core features present (heuristic — look for telltale strings)
    features = {
        "canvas": "<canvas" in html.lower(),
        "zoom": "zoom" in html.lower(),
        "search": "search" in html.lower(),
        "tooltip": "tooltip" in html.lower() or "tip" in html.lower(),
        "legend": "legend" in html.lower() or "sidebar" in html.lower(),
        "cluster": "cluster" in html.lower(),
    }
    for feature, found in features.items():
        if not found:
            warnings.append(f"Feature '{feature}' not obviously present in HTML.")
    
    # CHECK 5: Data is present (either inline or fetch)
    has_inline = "__INLINE_DATA__" in html or "const POSTS" in html or "const posts" in html
    has_fetch = "fetch(" in html
    if not has_inline and not has_fetch:
        errors.append("No data loading mechanism found (neither inline nor fetch).")
    
    # CHECK 6: Not using banned libraries
    if "plotly" in html.lower():
        warnings.append("Plotly detected. This project should use Canvas + D3, not Plotly.")
    
    # CHECK 7: Responsive meta tag
    if 'viewport' not in html:
        warnings.append("Missing viewport meta tag. May not be mobile-friendly.")
    
    # REPORT
    print(f"\n{'='*60}")
    print(f"PHASE 3 VERIFICATION REPORT")
    print(f"{'='*60}")
    print(f"File size: {size:,} bytes")
    print(f"Features detected: {sum(features.values())}/{len(features)}")
    for feat, found in features.items():
        print(f"  {'✓' if found else '✗'} {feat}")
    print(f"\nErrors: {len(errors)}")
    for e in errors: print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings: print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase3() else 1)
```

**Additionally: Manual visual smoke test.** After generating index.html, open it in a browser (or take a screenshot via headless Chrome) and verify:
1. Points are visible and colored (not all one color, not all black)
2. Hovering shows a styled tooltip (not a browser default title)
3. Clicking opens a URL
4. Search narrows visible points
5. The overall look feels editorial, not generic

**Note on frontend verification**: The automated checks for Phases 3–6 are heuristic string-matching on HTML source — they catch structural omissions but cannot evaluate visual quality, interaction smoothness, or design taste. For frontend phases, **the human checkpoint is the real quality gate**. Do not treat a passing verification agent as proof the phase is done — always get user sign-off.

**Human checkpoint**: "Here's the visualization. Open it in your browser and try: hover a few points, search for 'Coase', search for 'AI', click a post to verify it opens. Does the design feel right? Anything that needs polish?"

---

### PHASE 4: Time Animation

**Adds to**: `viz/index.html`

#### Features

**A. Time Slider**
- Horizontal range slider below the map (full width, styled to match — not a default HTML range input)
- Range: earliest post date → latest post date
- Displays current date prominently (month + year, display font)
- Posts with `date > slider_value` are hidden (opacity 0, not removed from DOM/canvas)
- Draggable for manual exploration

**B. Play/Pause**
- Play button auto-advances the slider
- Default speed: 1 month per 0.5 seconds (configurable via a speed control — 0.25x, 0.5x, 1x, 2x)
- During playback, newly appearing posts get a brief glow animation (2-frame: appear at 2x size, settle to 1x over 400ms)
- Pause button stops advancement

**C. Running Stats**
- During animation, display: "March 2019 — 247 of 1,432 posts"
- Optionally: a small sparkline showing cumulative post count over time (this is a nice editorial touch)

**D. Interaction with Other Features**
- Search still works during animation (filters within visible-by-time posts)
- Legend still works during animation
- Clicking a point still opens the post

#### PHASE 4 VERIFICATION AGENT

```python
# verification_phase4.py
# Check that time-related features exist in the HTML
import os, sys

def verify_phase4():
    errors = []
    
    with open("viz/index.html") as f:
        html = f.read()
    
    time_features = {
        "slider": "range" in html.lower() or "slider" in html.lower(),
        "play": "play" in html.lower(),
        "pause": "pause" in html.lower(),
        "animation": "requestAnimationFrame" in html or "setInterval" in html or "animation" in html.lower(),
        "date_display": "month" in html.lower() or "year" in html.lower(),
    }
    
    for feat, found in time_features.items():
        if not found:
            errors.append(f"Time feature '{feat}' not detected in HTML.")
    
    print(f"\n{'='*60}")
    print(f"PHASE 4 VERIFICATION REPORT")
    print(f"{'='*60}")
    for feat, found in time_features.items():
        print(f"  {'✓' if found else '✗'} {feat}")
    print(f"\nErrors: {len(errors)}")
    for e in errors: print(f"  ❌ {e}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase4() else 1)
```

**Human checkpoint**: "Play the animation from start to finish. Watch for the moment when AI/LLM posts start appearing — does it feel like a visible shift on the map? Is the animation smooth or jerky?"

---

### PHASE 5: Edge Overlay (Internal Link Graph)

**Adds to**: `viz/index.html`

#### Features

**A. Edge Rendering**
- Edges are quadratic bezier curves between linked posts (not straight lines — curves reduce visual clutter)
- Control point offset: perpendicular to the line between the two points, offset by 15% of the distance between them
- Base opacity: 0.08 (barely visible until toggled on)
- Toggled-on opacity: 0.25 for same-cluster edges, 0.5 for cross-cluster edges
- Same-cluster edges: warm gray (#BAB0AC)
- Cross-cluster edges: accent color (this is the highlight — these are the intellectual bridges)

**B. Toggle**
- "Show connections" toggle button (off by default — edges are visually heavy)
- When toggled on, edges appear with a staggered fade-in (100ms delay between each, sorted by date of source post — so you see the link network build up chronologically)

**C. Interaction with Time**
- Edge only appears if BOTH connected posts are visible (respects time slider)
- During time animation with edges toggled on, you see the link network grow

**D. Edge Hover**
- Hovering near an edge highlights it (full opacity) and shows both post titles in a small tooltip: "From: [Title A] → To: [Title B]"
- Hovering a POST with edges toggled on should highlight all edges connected to that post

#### PHASE 5 VERIFICATION AGENT

```python
# verification_phase5.py
import json, os, sys

def verify_phase5():
    errors = []
    
    # Check edge data exists
    posts = json.load(open("data/posts_with_coords.json"))
    total_links = sum(len(p.get("internal_links", [])) for p in posts)
    
    if total_links == 0:
        errors.append("No internal links found in data. Edge overlay will be empty.")
    
    with open("viz/index.html") as f:
        html = f.read()
    
    edge_features = {
        "bezier": "bezier" in html.lower() or "quadratic" in html.lower() or "arcTo" in html.lower(),
        "edge_toggle": "connection" in html.lower() or "edge" in html.lower(),
        "cross_cluster": "cross" in html.lower() or "bridge" in html.lower() or "different" in html.lower(),
    }
    
    for feat, found in edge_features.items():
        if not found:
            errors.append(f"Edge feature '{feat}' not detected.")
    
    print(f"\n{'='*60}")
    print(f"PHASE 5 VERIFICATION REPORT")
    print(f"{'='*60}")
    print(f"Total internal links in data: {total_links}")
    for feat, found in edge_features.items():
        print(f"  {'✓' if found else '✗'} {feat}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase5() else 1)
```

**Human checkpoint**: "Toggle edges on and zoom into a region where you see cross-cluster edges. Do the connected posts make sense? Do you remember linking those posts to each other?"

---

### PHASE 6: Journey Mode

**Adds to**: `viz/index.html`

This is the feature that goes beyond Anand's version — it turns the map from a static snapshot into a reading tool.

#### Concept

A "journey" is a guided path through related posts. The reader can:
1. Click any post to start a journey from that post
2. The map highlights a recommended reading path: a sequence of posts connected by internal links and/or semantic similarity
3. The reader follows the path, clicking through posts in order

Think of it like: you're at a museum, and instead of wandering randomly, a curator hands you a route card.

#### Features

**A. Journey Panel**
- When a post is clicked WITH the journey mode toggle active, a panel slides in from the right
- The panel shows: **Starting point: [Post Title]**
- Below it, a **numbered reading list** of 5–8 posts, ordered as a narrative path:
  1. Start with the clicked post
  2. Follow internal links first (where available) — these are the author's own chosen connections
  3. Fill remaining slots with the nearest posts in embedding space that are NOT in the same cluster (cross-cluster neighbors are more interesting than within-cluster ones)
  4. Order the final list chronologically (oldest to newest) — this creates a narrative of intellectual development

**B. Path Visualization**
- The journey posts are highlighted on the map (full opacity, enlarged)
- Non-journey posts fade to 10% opacity
- A dashed line connects journey posts in order (the "reading path")
- Each journey post gets a numbered label (1, 2, 3...) visible on the map

**C. Post Cards in the Panel**
- Each journey post shown as a card: number / title / date / cluster label / snippet
- Clicking the card opens the post in a new tab
- A "Next →" button advances to the next post in the journey (scrolls the panel and centers the map on that point)

**D. Journey Suggestions**
- Pre-compute 3–5 "curated journeys" during Phase 2 (not at runtime). To compute these:
  1. Identify the post with the earliest date in each of the 3 largest clusters
  2. For each, compute a journey path using the algorithm in section A above
  3. Use the Gemini API to generate a compelling journey title from the post titles in the path. Prompt: "These blog posts form an intellectual journey across economics, AI, and philosophy. Give this reading path a compelling 4–8 word title that would make someone want to follow it. Return ONLY the title."
  4. Store these as a `curated_journeys` array in `posts_with_coords.json`
- Example curated journeys:
  - "From Elasticity to AI Alignment" (the full arc)
  - "The Coasean Thread" (all posts touching transaction costs, firms, and AI)
  - "Teaching and Learning" (pedagogy posts across eras)
- These appear as clickable suggestions when journey mode is first toggled on

#### Interaction with Other Modes

Journey mode is a MODAL state — when active, it changes how clicks work. This creates state management complexity. Handle it explicitly:

- **Normal mode** (default): Click opens post, hover shows tooltip, search filters, time slider works
- **Journey mode** (toggled): Click starts/extends a journey, hover shows tooltip, search filters WITHIN the journey, time slider is DISABLED (journeys span time periods)
- **Edge mode** can be ON in either normal or journey mode. In journey mode, only show edges between journey posts.

Use a simple state machine:
```
currentMode: "normal" | "journey"
edgesVisible: true | false
timeSliderActive: true | false (auto-disabled in journey mode)
activeJourney: null | [postId, postId, ...]
searchQuery: "" | "search string"
```

Display the current mode clearly in the UI (e.g., a mode indicator in the top-right: "Exploring" vs "Journey Mode ✦").

---

#### PHASE 6 VERIFICATION AGENT
import os, sys

def verify_phase6():
    errors = []
    
    with open("viz/index.html") as f:
        html = f.read()
    
    journey_features = {
        "journey_mode": "journey" in html.lower(),
        "reading_path": "path" in html.lower() or "route" in html.lower(),
        "panel": "panel" in html.lower() or "sidebar" in html.lower(),
        "curated": "curated" in html.lower() or "suggestion" in html.lower(),
        "numbered": any(str(i) in html for i in range(1, 9)),
    }
    
    for feat, found in journey_features.items():
        if not found:
            errors.append(f"Journey feature '{feat}' not detected.")
    
    print(f"\n{'='*60}")
    print(f"PHASE 6 VERIFICATION REPORT")
    print(f"{'='*60}")
    for feat, found in journey_features.items():
        print(f"  {'✓' if found else '✗'} {feat}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")
    
    return len(errors) == 0

if __name__ == "__main__":
    sys.exit(0 if verify_phase6() else 1)
```

**Human checkpoint**: "Start a journey from your earliest economics post. Does the suggested reading path feel like a real intellectual journey? Try one of the curated journeys. Would you send this to a student?"

---

## 5. File Structure

```
efe-embedding-map/
├── README.md
├── requirements.txt
├── .env.example                    # GEMINI_API_KEY=your-key-here
├── scrape/
│   ├── scrape_wordpress.py
│   ├── scrape_substack.py
│   └── merge_and_dedup.py
├── embed/
│   ├── generate_embeddings.py
│   ├── run_umap.py
│   └── cluster_and_label.py
├── verify/
│   ├── verification_phase1.py
│   ├── verification_phase2.py
│   ├── verification_phase3.py
│   ├── verification_phase4.py
│   ├── verification_phase5.py
│   └── verification_phase6.py
├── data/
│   ├── posts.json
│   ├── embeddings.npy
│   ├── embedding_order.json
│   └── posts_with_coords.json
├── viz/
│   ├── index.html                  # The visualization (single file, hosted version)
│   ├── index_standalone.html       # With data inlined (local version)
│   └── posts_with_coords.json      # Copy of data for hosted version
└── deploy/
    ├── deploy.sh                   # Script to deploy to Vercel/GitHub Pages
    └── rebuild.sh                  # Re-runs full pipeline (scrape → embed → UMAP → cluster → build HTML)
```

### rebuild.sh Must Handle

When new posts are published, the map needs updating. `rebuild.sh` should:
1. Re-run scraping (both sources)
2. Detect which posts are NEW (not in existing `embeddings.npy`)
3. Generate embeddings ONLY for new posts (append to existing)
4. Re-run UMAP on the full set (UMAP must re-fit on all embeddings — you can't add points incrementally)
5. Re-run clustering
6. Rebuild the HTML

This should be runnable with a single command: `bash deploy/rebuild.sh`

### README.md Must Include

1. **One-line description** of what this is
2. **Screenshot or GIF** of the visualization (take a screenshot after Phase 3, update after Phase 6)
3. **Quick start**: How to open the standalone version locally (just double-click `viz/index_standalone.html`)
4. **Rebuild instructions**: How to re-run the pipeline from scratch (install deps, set API key, run each phase script in order)
5. **Update instructions**: How to add new posts (re-run scrape → embed → UMAP → rebuild HTML)
6. **Credits**: Mention S Anand's blog embedding map as inspiration. Mention Gemini for embeddings, UMAP for dimensionality reduction, HDBSCAN for clustering, D3.js for visualization.

---

## 6. Dependencies

```
# requirements.txt
requests>=2.31
beautifulsoup4>=4.12
numpy>=1.24
umap-learn>=0.5
hdbscan>=0.8.33
google-generativeai>=0.5
python-dotenv>=1.0
```

Frontend: D3.js v7 loaded from CDN (`https://cdn.jsdelivr.net/npm/d3@7`). No other external JS dependencies.

---

## 7. Agentic Orchestration Guide

This section tells Claude Code HOW to execute this project most effectively.

### Execution Strategy

**Use a phased, verify-before-advancing workflow.** For each phase:

1. **Read** the phase specification
2. **Plan** the implementation (write pseudocode or outline in comments before coding)
3. **Build** the code
4. **Run** the verification agent
5. **Fix** any errors the verification agent catches
6. **Show** the human checkpoint to the user
7. **Only then** proceed to the next phase

### Parallelization Opportunities

- Phase 1a (WordPress scraping) and 1b (Substack scraping) can run in parallel
- Phase 2a (embedding) is sequential (API calls) but can be batched
- Phase 2b (UMAP) and 2c (clustering) are both fast and sequential
- Phases 3–6 are sequential (each adds to the same HTML file)

### Context Management

- When working on the frontend (Phases 3–6), keep the `frontend-design/SKILL.md` guidance in context
- When working on scraping (Phase 1), you do NOT need the frontend skill
- The verification scripts are self-contained — they only need access to the data files
- **HTML file size warning**: By Phase 6, `index.html` will be 2,000–5,000+ lines. Do NOT try to hold the entire file in context for edits. Instead:
  - Structure the JS code into clearly named functions/sections with comment headers
  - When editing, load only the relevant section (e.g., "the journey mode section")
  - Use search/replace for targeted edits, not full-file rewrites
  - Consider building Phases 4–6 as separate JS functions that are appended to the base Phase 3 file, rather than interleaving code throughout

### Error Recovery

- If WordPress scraping fails entirely: try the WordPress.com public REST API first, then fall back to month-archive crawling
- If Substack API fails: fall back to sitemap, then to HTML scraping of the archive page
- If Gemini embedding API hits rate limits: implement exponential backoff, and save progress after each batch so you can resume
- If HDBSCAN produces too few clusters (<4): lower `min_cluster_size` to 10. If too many (>20): raise to 25.
- If the HTML file exceeds 10MB (due to inlined data): split into index.html + posts_with_coords.json and use the fetch pattern

### Run All Verifications

Create a `verify/run_all.sh` script:
```bash
#!/bin/bash
set -e
echo "Running all verification agents..."
for phase in 1 2 3 4 5 6; do
    echo ""
    echo "━━━ Phase $phase ━━━"
    python verify/verification_phase${phase}.py
done
echo ""
echo "All phases verified ✓"
```
This is useful for re-verifying after making changes that might affect multiple phases.

### What "Done" Looks Like

The project is done when:
1. All 6 verification agents pass
2. The user has approved each human checkpoint
3. The `viz/index.html` file opens in a browser and delivers:
   - A visually striking, editorially designed map of 1000+ posts
   - Hover tooltips that make you want to click
   - Search that helps you find what you're looking for
   - A time animation that tells the story of an intellectual journey
   - Edge overlays that reveal hidden connections
   - Journey mode that turns exploration into guided reading
4. The `viz/index_standalone.html` works when double-clicked from a file browser (no server needed)

---

## 8. Constraints & Non-Negotiables

- **Single HTML file** for the visualization. No build step, no npm, no webpack for the frontend.
- **Custom typography** loaded from Google Fonts. Never Inter, Roboto, Arial, or system defaults.
- **No Plotly, no Chart.js** for the map. Canvas + D3 for performance and design control.
- **Colorblind-safe palette**. No red-green pairs as the only distinguishing factor.
- **Mobile-friendly**. Viewport meta tag, touch-friendly tap targets, responsive sidebar.
- **Every click on a post must reliably open the correct blog URL in a new tab.** This is the most basic user promise. Test it.
- **Verification agents must pass before advancing.** No exceptions. If a verification fails, fix the issue, don't skip the check.
