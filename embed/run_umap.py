"""
Run UMAP dimensionality reduction on embeddings.
Input: data/embeddings.npy
Output: data/umap_coords.npy (2D coordinates normalized to [0, 1000])
"""

import os
import numpy as np
import umap

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
COORDS_PATH = os.path.join(DATA_DIR, "umap_coords.npy")


def main():
    print("Loading embeddings...")
    embeddings = np.load(EMBEDDINGS_PATH)
    print(f"  Shape: {embeddings.shape}")

    print("Running UMAP...")
    reducer = umap.UMAP(
        n_neighbors=15,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
    )
    coords_2d = reducer.fit_transform(embeddings)
    print(f"  UMAP output shape: {coords_2d.shape}")

    # Normalize to [0, 1000]
    for dim in range(2):
        col = coords_2d[:, dim]
        col_min, col_max = col.min(), col.max()
        coords_2d[:, dim] = (col - col_min) / (col_max - col_min) * 1000

    print(f"  X range: [{coords_2d[:,0].min():.1f}, {coords_2d[:,0].max():.1f}]")
    print(f"  Y range: [{coords_2d[:,1].min():.1f}, {coords_2d[:,1].max():.1f}]")

    np.save(COORDS_PATH, coords_2d.astype(np.float32))
    print(f"  Saved to {COORDS_PATH}")


if __name__ == "__main__":
    main()
