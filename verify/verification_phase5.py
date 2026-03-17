import json, os, sys


def verify_phase5():
    errors = []

    # Check edge data exists
    raw = json.load(open("data/posts_with_coords.json"))
    posts = raw["posts"] if isinstance(raw, dict) and "posts" in raw else raw
    total_links = sum(len(p.get("internal_links", [])) for p in posts)

    if total_links == 0:
        errors.append("No internal links found in data. Edge overlay will be empty.")

    with open("viz/index.html") as f:
        html = f.read()

    edge_features = {
        "bezier": "bezier" in html.lower() or "quadratic" in html.lower() or "quadraticCurveTo" in html,
        "edge_toggle": "connection" in html.lower() or "edge" in html.lower(),
        "cross_cluster": "cross" in html.lower() or "isCrossCluster" in html,
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
    print(f"\nErrors: {len(errors)}")
    for e in errors:
        print(f"  ❌ {e}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")

    return len(errors) == 0


if __name__ == "__main__":
    sys.exit(0 if verify_phase5() else 1)
