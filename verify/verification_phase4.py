import os, sys


def verify_phase4():
    errors = []

    with open("viz/index.html") as f:
        html = f.read()

    time_features = {
        "slider": "range" in html.lower() or "slider" in html.lower(),
        "play": "play" in html.lower(),
        "pause": "pause" in html.lower() or "stop" in html.lower(),
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
    for e in errors:
        print(f"  ❌ {e}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")

    return len(errors) == 0


if __name__ == "__main__":
    sys.exit(0 if verify_phase4() else 1)
