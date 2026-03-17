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
