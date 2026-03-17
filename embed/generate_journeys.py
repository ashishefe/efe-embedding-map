"""
Generate curated journeys for EFE Viz.

For each of the 3 largest real clusters:
1. Find the earliest post
2. Build a journey of 5-8 posts: start with that post, follow internal links,
   fill remaining with cross-cluster nearest neighbors (Euclidean on x,y)
3. Order chronologically
4. Title via Gemini API
5. Save curated_journeys into posts_with_coords.json
"""

import json
import math
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from collections import Counter

# Load env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "posts_with_coords.json"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    sys.exit(1)

# Excluded cluster IDs (not real thematic clusters)
EXCLUDED_CLUSTERS = {-1, 5}
TARGET_JOURNEY_SIZE = 7  # aim for 7, allow 5-8
MIN_JOURNEY_SIZE = 5
MAX_JOURNEY_SIZE = 8


def load_posts():
    with open(DATA_PATH) as f:
        return json.load(f)


def euclidean(p1, p2):
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def find_largest_clusters(posts, n=3):
    """Find the n largest clusters, excluding non-thematic ones."""
    counts = Counter(
        p["cluster_id"] for p in posts if p["cluster_id"] not in EXCLUDED_CLUSTERS
    )
    return [cid for cid, _ in counts.most_common(n)]


def find_earliest_post(posts, cluster_id):
    """Find the post with the earliest date in a cluster."""
    cluster_posts = [p for p in posts if p["cluster_id"] == cluster_id]
    return min(cluster_posts, key=lambda p: p["date"])


def build_journey(start_post, posts, posts_by_id, cluster_id):
    """
    Build a journey starting from start_post:
    1. Follow internal links (if they exist and aren't in same cluster)
    2. Fill with cross-cluster nearest neighbors
    3. Order chronologically
    """
    journey_ids = {start_post["id"]}
    journey_posts = [start_post]

    # Step 1: Follow internal links from the start post
    for link_id in start_post.get("internal_links", []):
        if link_id in posts_by_id and len(journey_ids) < MAX_JOURNEY_SIZE:
            linked = posts_by_id[link_id]
            if linked["id"] not in journey_ids:
                journey_ids.add(linked["id"])
                journey_posts.append(linked)

    # Also follow internal links from posts already in the journey
    for jp in list(journey_posts):
        for link_id in jp.get("internal_links", []):
            if link_id in posts_by_id and len(journey_ids) < MAX_JOURNEY_SIZE:
                linked = posts_by_id[link_id]
                if linked["id"] not in journey_ids:
                    journey_ids.add(linked["id"])
                    journey_posts.append(linked)

    # Step 2: Fill remaining slots with cross-cluster nearest neighbors
    # Cross-cluster = NOT in the same cluster as start_post
    cross_cluster_posts = [
        p
        for p in posts
        if p["cluster_id"] != cluster_id
        and p["cluster_id"] not in EXCLUDED_CLUSTERS
        and p["id"] not in journey_ids
    ]

    while len(journey_posts) < TARGET_JOURNEY_SIZE and cross_cluster_posts:
        # Find nearest to the centroid of current journey
        cx = sum(p["x"] for p in journey_posts) / len(journey_posts)
        cy = sum(p["y"] for p in journey_posts) / len(journey_posts)
        centroid = {"x": cx, "y": cy}

        nearest = min(cross_cluster_posts, key=lambda p: euclidean(centroid, p))
        journey_ids.add(nearest["id"])
        journey_posts.append(nearest)
        cross_cluster_posts.remove(nearest)

    # Step 3: Order chronologically
    journey_posts.sort(key=lambda p: p["date"])

    return journey_posts


def generate_title(posts_in_journey):
    """Call Gemini API to generate a journey title."""
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    titles_list = "\n".join(
        f"- {p['title']} ({p['date']})" for p in posts_in_journey
    )

    prompt = (
        "These blog posts form an intellectual journey across economics, AI, and philosophy. "
        "Give this reading path a compelling 4-8 word title that would make someone want to follow it. "
        "Return ONLY the title.\n\n"
        f"Posts in order:\n{titles_list}"
    )

    response = model.generate_content(prompt)
    return response.text.strip().strip('"').strip("'").replace("**", "").strip()


def main():
    posts = load_posts()
    posts_by_id = {p["id"]: p for p in posts}

    print(f"Loaded {len(posts)} posts")

    # Find 3 largest clusters
    largest_clusters = find_largest_clusters(posts, n=3)
    print(f"3 largest clusters: {largest_clusters}")
    for cid in largest_clusters:
        label = next(p["cluster_label"] for p in posts if p["cluster_id"] == cid)
        count = sum(1 for p in posts if p["cluster_id"] == cid)
        print(f"  Cluster {cid}: \"{label}\" ({count} posts)")

    curated_journeys = []

    for cid in largest_clusters:
        earliest = find_earliest_post(posts, cid)
        print(f"\nCluster {cid}: earliest post = \"{earliest['title']}\" ({earliest['date']})")

        journey_posts = build_journey(earliest, posts, posts_by_id, cid)
        print(f"  Journey has {len(journey_posts)} posts:")
        for jp in journey_posts:
            print(f"    [{jp['date']}] {jp['title']} (cluster {jp['cluster_id']})")

        # Generate title via Gemini
        title = generate_title(journey_posts)
        print(f"  Gemini title: \"{title}\"")

        curated_journeys.append(
            {
                "title": title,
                "post_ids": [p["id"] for p in journey_posts],
                "description": f"A journey starting from the {next(p['cluster_label'] for p in posts if p['cluster_id'] == cid)} cluster, weaving across topics.",
            }
        )

    # Save back to JSON - convert list to dict with posts + curated_journeys
    output = {"posts": posts, "curated_journeys": curated_journeys}

    with open(DATA_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(curated_journeys)} curated journeys to {DATA_PATH}")
    print("Done!")


if __name__ == "__main__":
    main()
