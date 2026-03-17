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
    generic_fonts = ["Inter", "Roboto", "Arial"]
    for font in generic_fonts:
        if re.search(rf'font-family:\s*["\']?{font}', html, re.IGNORECASE):
            warnings.append(f"Generic font '{font}' may be used as primary font.")

    # CHECK 3: Google Fonts loaded
    if "fonts.googleapis.com" not in html and "fonts.gstatic.com" not in html:
        warnings.append("No Google Fonts detected. Custom typography may be missing.")

    # CHECK 4: Core features present
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

    # CHECK 5: Data loading mechanism
    has_inline = "__INLINE_DATA__" in html or "const POSTS" in html or "const posts" in html
    has_fetch = "fetch(" in html
    if not has_inline and not has_fetch:
        errors.append("No data loading mechanism found (neither inline nor fetch).")

    # CHECK 6: Not using banned libraries
    if "plotly" in html.lower():
        warnings.append("Plotly detected. This project should use Canvas + D3, not Plotly.")

    # CHECK 7: Responsive meta tag
    if "viewport" not in html:
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
    for e in errors:
        print(f"  ❌ {e}")
    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  ⚠️  {w}")
    print(f"\n{'PASS ✓' if not errors else 'FAIL ✗'}")

    return len(errors) == 0


if __name__ == "__main__":
    sys.exit(0 if verify_phase3() else 1)
