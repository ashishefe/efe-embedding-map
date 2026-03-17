"""
Cluster posts using HDBSCAN, label clusters via Gemini, assign colors,
and assemble the final posts_with_coords.json.
"""

import json
import os
import sys
import time

import numpy as np
import hdbscan
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
COORDS_PATH = os.path.join(DATA_DIR, "umap_coords.npy")
POSTS_PATH = os.path.join(DATA_DIR, "posts.json")
ORDER_PATH = os.path.join(DATA_DIR, "embedding_order.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "posts_with_coords.json")

# Curated colorblind-safe palette
PALETTE = [
    "#4E79A7",  # steel blue
    "#F28E2B",  # tangerine
    "#E15759",  # coral red
    "#76B7B2",  # teal
    "#59A14F",  # forest green
    "#EDC948",  # gold
    "#B07AA1",  # lavender
    "#FF9DA7",  # pink
    "#9C755F",  # sienna
    "#BAB0AC",  # warm gray
    "#AF7AA1",  # mauve
    "#86BCB6",  # sage
]

MISC_COLOR = "#BAB0AC"  # warm gray for noise/miscellaneous


def extend_palette(n_colors):
    """Extend palette if more than 12 clusters by lightening/darkening."""
    if n_colors <= len(PALETTE):
        return PALETTE[:n_colors]

    extended = list(PALETTE)
    # Lighten existing colors
    for i in range(n_colors - len(PALETTE)):
        base = PALETTE[i % len(PALETTE)]
        # Simple lighten: blend with white
        r, g, b = int(base[1:3], 16), int(base[3:5], 16), int(base[5:7], 16)
        r = min(255, r + 40)
        g = min(255, g + 40)
        b = min(255, b + 40)
        extended.append(f"#{r:02x}{g:02x}{b:02x}")
    return extended


def label_cluster(cluster_titles, genai_model):
    """Use Gemini to generate a cluster label from representative titles."""
    prompt = f"""These are blog post titles from the same thematic cluster on an economics/AI/philosophy blog:
{chr(10).join('- ' + t for t in cluster_titles)}
Give this cluster a short, evocative 2-4 word label. It should feel like a section heading in a thoughtful magazine, not a database category. Examples: "Behavioral Nudges", "India's AI Strategy", "Philosophy of Consciousness", "Teaching With AI", "Coase & Transaction Costs".
Return ONLY the label, nothing else."""

    try:
        response = genai_model.generate_content(prompt)
        label = response.text.strip().strip('"').strip("'")
        return label
    except Exception as e:
        print(f"  Warning: Gemini labeling failed: {e}")
        return "Unlabeled"


def main():
    # Configure Gemini for cluster labeling
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel("gemini-2.0-flash")

    # Load data
    print("Loading data...")
    embeddings = np.load(EMBEDDINGS_PATH)
    coords = np.load(COORDS_PATH)
    with open(POSTS_PATH) as f:
        posts = json.load(f)
    with open(ORDER_PATH) as f:
        embedding_order = json.load(f)

    print(f"  Embeddings: {embeddings.shape}")
    print(f"  Coords: {coords.shape}")
    print(f"  Posts: {len(posts)}")
    print(f"  Embedding order: {len(embedding_order)}")

    # Build ID -> index mapping for embeddings
    emb_id_to_idx = {pid: i for i, pid in enumerate(embedding_order)}

    # Run HDBSCAN on high-dimensional embeddings
    # Use UMAP 2D coords for clustering — high-dim HDBSCAN on 3072-dim
    # embeddings produces too much noise. The 2D UMAP preserves local structure
    # well enough for meaningful clusters.
    print("\nRunning HDBSCAN clustering on UMAP coordinates...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=12,
        min_samples=3,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(coords)

    from collections import Counter
    label_counts = Counter(labels)
    n_clusters = len([k for k in label_counts if k != -1])
    noise_count = label_counts.get(-1, 0)
    noise_pct = noise_count / len(labels) * 100
    print(f"  Clusters found: {n_clusters}")
    print(f"  Noise posts: {noise_count} ({noise_pct:.0f}%)")

    # Iteratively adjust if needed
    if noise_pct > 40 or n_clusters < 8:
        print(f"  Adjusting: trying min_cluster_size=8, min_samples=2...")
        clusterer = hdbscan.HDBSCAN(min_cluster_size=8, min_samples=2, metric="euclidean")
        labels = clusterer.fit_predict(coords)
        label_counts = Counter(labels)
        n_clusters = len([k for k in label_counts if k != -1])
        noise_count = label_counts.get(-1, 0)
        noise_pct = noise_count / len(labels) * 100
        print(f"  Now: {n_clusters} clusters, {noise_pct:.0f}% noise")

    if n_clusters > 25:
        print("  Too many clusters, retrying with min_cluster_size=20...")
        clusterer = hdbscan.HDBSCAN(min_cluster_size=20, min_samples=5, metric="euclidean")
        labels = clusterer.fit_predict(coords)
        label_counts = Counter(labels)
        n_clusters = len([k for k in label_counts if k != -1])
        print(f"  Now: {n_clusters} clusters")

    # Generate cluster labels
    print("\nGenerating cluster labels via Gemini...")
    cluster_labels = {}
    cluster_colors = {}
    colors = extend_palette(n_clusters)

    cluster_ids = sorted([k for k in label_counts if k != -1])
    for ci, cid in enumerate(cluster_ids):
        # Find posts in this cluster, get 10 nearest to centroid
        cluster_mask = labels == cid
        cluster_embeddings = embeddings[cluster_mask]
        centroid = cluster_embeddings.mean(axis=0)
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        nearest_indices = np.argsort(distances)[:10]

        # Map back to global indices
        global_indices = np.where(cluster_mask)[0]
        representative_ids = [embedding_order[global_indices[i]] for i in nearest_indices]

        # Get titles
        id_to_post = {p["id"]: p for p in posts}
        titles = [id_to_post[pid]["title"] for pid in representative_ids if pid in id_to_post]

        label = label_cluster(titles, llm)
        cluster_labels[cid] = label
        cluster_colors[cid] = colors[ci]
        print(f"  Cluster {cid}: {label} ({label_counts[cid]} posts)")
        time.sleep(2)  # Rate limiting for Gemini

    cluster_labels[-1] = "Miscellaneous"
    cluster_colors[-1] = MISC_COLOR

    # Build URL -> post ID mapping for internal link resolution
    url_to_id = {}
    for p in posts:
        url_to_id[p["url"]] = p["id"]
        if p.get("alt_url"):
            url_to_id[p["alt_url"]] = p["id"]

    # Assemble final dataset
    print("\nAssembling final dataset...")
    output_posts = []
    for p in posts:
        pid = p["id"]
        if pid not in emb_id_to_idx:
            continue  # Skip posts without embeddings

        idx = emb_id_to_idx[pid]
        cluster_id = int(labels[idx])

        # Resolve internal links from URLs to post IDs
        resolved_links = []
        for link_url in p.get("internal_links", []):
            linked_id = url_to_id.get(link_url)
            if linked_id and linked_id != pid:  # Don't self-link
                resolved_links.append(linked_id)
        resolved_links = list(set(resolved_links))

        # Generate snippet
        content = p.get("content", "")
        snippet = content[:150].strip()
        if len(content) > 150:
            snippet = snippet.rsplit(" ", 1)[0] + "..."

        output_post = {
            "id": pid,
            "title": p["title"],
            "url": p["url"],
            "alt_url": p.get("alt_url"),
            "date": p["date"][:10] if p.get("date") else "",
            "x": round(float(coords[idx, 0]), 1),
            "y": round(float(coords[idx, 1]), 1),
            "cluster_id": cluster_id,
            "cluster_label": cluster_labels.get(cluster_id, "Miscellaneous"),
            "cluster_color": cluster_colors.get(cluster_id, MISC_COLOR),
            "source": p["source"],
            "word_count": p.get("word_count", 0),
            "internal_links": resolved_links,
            "snippet": snippet,
        }
        output_posts.append(output_post)

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_posts, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(output_posts)} posts with coordinates saved to {OUTPUT_PATH}")
    print(f"Clusters: {n_clusters} + miscellaneous")


if __name__ == "__main__":
    main()
