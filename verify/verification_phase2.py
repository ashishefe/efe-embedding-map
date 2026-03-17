import json
import numpy as np
import sys
from collections import Counter


def verify_phase2():
    raw = json.load(open("data/posts_with_coords.json"))
    posts = raw["posts"] if isinstance(raw, dict) and "posts" in raw else raw
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
    for e in errors:
        print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")

    return len(errors) == 0


if __name__ == "__main__":
    sys.exit(0 if verify_phase2() else 1)
