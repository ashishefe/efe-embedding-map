"""
Generate embeddings for all posts using Gemini Embedding API.
Supports incremental save/resume via embedding_progress.json.
"""

import json
import os
import sys
import time

import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
POSTS_PATH = os.path.join(DATA_DIR, "posts.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "embedding_progress.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
ORDER_PATH = os.path.join(DATA_DIR, "embedding_order.json")
BATCHES_DIR = os.path.join(DATA_DIR, "embedding_batches")

MODEL = "gemini-embedding-001"
BATCH_SIZE = 50
MAX_CONTENT_CHARS = 8000
MAX_RETRIES = 5
INITIAL_BACKOFF = 2


def prepare_text(post):
    """Prepare embedding input: title + content truncated to 8000 chars."""
    title = post.get("title", "")
    content = post.get("content", "")[:MAX_CONTENT_CHARS]
    return f"{title}\n\n{content}"


def load_progress():
    """Load set of already-embedded post IDs."""
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            return set(json.load(f))
    return set()


def save_progress(embedded_ids):
    """Save set of embedded post IDs."""
    with open(PROGRESS_PATH, "w") as f:
        json.dump(sorted(embedded_ids), f)


def save_batch(batch_idx, embeddings, post_ids):
    """Save a batch of embeddings to disk."""
    os.makedirs(BATCHES_DIR, exist_ok=True)
    batch_path = os.path.join(BATCHES_DIR, f"batch_{batch_idx:04d}.npz")
    np.savez(batch_path, embeddings=np.array(embeddings, dtype=np.float32), post_ids=post_ids)


def embed_batch_with_retry(texts):
    """Embed a batch of texts with exponential backoff."""
    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            result = genai.embed_content(
                model=f"models/{MODEL}",
                content=texts,
                task_type="CLUSTERING",
            )
            return result["embedding"]
        except Exception as e:
            error_str = str(e)
            if attempt < MAX_RETRIES - 1 and ("429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower() or "resource" in error_str.lower()):
                print(f"    Rate limited (attempt {attempt+1}/{MAX_RETRIES}), waiting {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
            else:
                raise
    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")


def main():
    global MODEL

    # Configure API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Add it to .env file.")
        sys.exit(1)
    genai.configure(api_key=api_key)

    # Test API connection
    print(f"Testing Gemini API with model {MODEL}...")
    try:
        test_result = genai.embed_content(
            model=f"models/{MODEL}",
            content=["test"],
            task_type="CLUSTERING",
        )
        embedding_dim = len(test_result["embedding"][0])
        print(f"  API working. Embedding dimension: {embedding_dim}")
    except Exception as e:
        print(f"  API test failed: {e}")
        print("  Trying fallback model 'text-embedding-004'...")
        MODEL = "gemini-embedding-2-preview"
        try:
            test_result = genai.embed_content(
                model=f"models/{MODEL}",
                content=["test"],
                task_type="CLUSTERING",
            )
            embedding_dim = len(test_result["embedding"][0])
            print(f"  Fallback API working. Embedding dimension: {embedding_dim}")
        except Exception as e2:
            print(f"  Fallback also failed: {e2}")
            sys.exit(1)

    # Load posts
    with open(POSTS_PATH) as f:
        posts = json.load(f)
    print(f"Total posts: {len(posts)}")

    # Check progress
    embedded_ids = load_progress()
    print(f"Already embedded: {len(embedded_ids)}")

    # Filter to posts that still need embedding
    remaining = [(i, p) for i, p in enumerate(posts) if p["id"] not in embedded_ids]
    print(f"Remaining to embed: {len(remaining)}")

    if not remaining:
        print("All posts already embedded. Assembling final output...")
    else:
        # Process in batches
        batch_count = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
        for batch_idx in range(batch_count):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(remaining))
            batch_posts = remaining[start:end]

            texts = [prepare_text(p) for _, p in batch_posts]
            post_ids = [p["id"] for _, p in batch_posts]

            try:
                embeddings = embed_batch_with_retry(texts)
                save_batch(len(embedded_ids) // BATCH_SIZE + batch_idx, embeddings, post_ids)

                for pid in post_ids:
                    embedded_ids.add(pid)
                save_progress(embedded_ids)

                print(f"  Batch {batch_idx+1}/{batch_count}: embedded {len(embedded_ids)}/{len(posts)} posts")
            except Exception as e:
                print(f"  ERROR on batch {batch_idx+1}: {e}")
                print(f"  Progress saved. {len(embedded_ids)} posts embedded so far. Re-run to resume.")
                sys.exit(1)

            # Small delay between batches to avoid rate limits
            if batch_idx < batch_count - 1:
                time.sleep(1)

    # Assemble final embeddings from all batch files
    print("\nAssembling final embeddings...")
    batch_files = sorted([f for f in os.listdir(BATCHES_DIR) if f.endswith(".npz")])

    all_embeddings = {}
    for bf in batch_files:
        data = np.load(os.path.join(BATCHES_DIR, bf), allow_pickle=True)
        embs = data["embeddings"]
        pids = data["post_ids"]
        for pid, emb in zip(pids, embs):
            all_embeddings[str(pid)] = emb

    # Order embeddings to match posts.json order
    ordered_ids = []
    ordered_embs = []
    missing = []
    for p in posts:
        pid = p["id"]
        if pid in all_embeddings:
            ordered_ids.append(pid)
            ordered_embs.append(all_embeddings[pid])
        else:
            missing.append(pid)

    if missing:
        print(f"WARNING: {len(missing)} posts have no embeddings: {missing[:5]}...")

    embeddings_array = np.array(ordered_embs, dtype=np.float32)
    np.save(EMBEDDINGS_PATH, embeddings_array)

    with open(ORDER_PATH, "w") as f:
        json.dump(ordered_ids, f)

    print(f"\nDone!")
    print(f"  Embeddings shape: {embeddings_array.shape}")
    print(f"  Saved to: {EMBEDDINGS_PATH}")
    print(f"  Order saved to: {ORDER_PATH}")


if __name__ == "__main__":
    main()
