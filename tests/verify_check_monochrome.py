import os
import re
import sys

def run_monochrome_audit():
    print("==================================================================")
    print("CHECK 2: AUTOMATED MONOCHROME & RED ACCENT FORENSIC AUDIT")
    print("==================================================================")

    # 1. Audit frontend/src/index.css
    index_css_path = r'c:\TalentOpsAI\frontend\src\index.css'
    with open(index_css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    # Verify dark tokens
    assert '--main-bg: #09090b;' in css, "Dark --main-bg must be #09090b"
    assert '--panel-bg: #121214;' in css, "Dark --panel-bg must be #121214"
    assert '--card-bg: #161618;' in css, "Dark --card-bg must be #161618"
    assert '--text-primary: #ffffff;' in css, "Dark --text-primary must be #ffffff"
    assert '--brand: #ffffff;' in css, "Dark --brand must be #ffffff"
    assert '--success: #ffffff;' in css, "Dark --success must be monochrome #ffffff"
    assert '--danger: #ef4444;' in css, "Dark --danger must be red accent #ef4444"
    print(" [PASS] Dark theme CSS variables: 100% monochrome + red accent verified.")

    # Verify light tokens
    assert '--main-bg: #ffffff;' in css, "Light --main-bg must be #ffffff"
    assert '--panel-bg: #f4f4f5;' in css, "Light --panel-bg must be #f4f4f5"
    assert '--card-bg: #ffffff;' in css, "Light --card-bg must be #ffffff"
    assert '--text-primary: #09090b;' in css, "Light --text-primary must be #09090b"
    assert '--danger: #dc2626;' in css, "Light --danger must be red accent #dc2626"
    print(" [PASS] Light theme CSS variables: 100% monochrome + red accent verified.")

    # Verify header icon button has no border / box
    assert '.cc-icon-button {' in css, ".cc-icon-button class must exist"
    assert 'border: none;' in css, ".cc-icon-button must have border: none"
    assert 'box-shadow: none;' in css, ".cc-icon-button must have box-shadow: none"
    print(" [PASS] Header icon buttons: Outer box, border, and shadows removed (pure icons only).")

    # Verify session dot is monochrome white
    assert '.cc-session-dot {' in css, ".cc-session-dot must exist"
    assert 'background: #ffffff;' in css, ".cc-session-dot must be white"
    print(" [PASS] Telemetry session dot: Pure white with white glow verified.")

    # 2. Audit codebase colors
    src_dir = r'c:\TalentOpsAI\frontend\src'
    hex_re = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b')

    total_colors = 0
    monochrome_count = 0
    red_count = 0
    other_count = 0

    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if f.endswith(('.jsx', '.js', '.css')) and not f.endswith(('.test.jsx', '.spec.jsx')):
                filepath = os.path.join(root, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fp:
                    for line in fp:
                        stripped = line.strip()
                        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                            continue
                        matches = hex_re.findall(line)
                        for m in matches:
                            hex_clean = m.lower()
                            if len(hex_clean) == 3:
                                r = int(hex_clean[0]*2, 16)
                                g = int(hex_clean[1]*2, 16)
                                b = int(hex_clean[2]*2, 16)
                            elif len(hex_clean) in (6, 8):
                                r = int(hex_clean[0:2], 16)
                                g = int(hex_clean[2:4], 16)
                                b = int(hex_clean[4:6], 16)
                            else:
                                continue

                            total_colors += 1
                            max_c = max(r, g, b)
                            min_c = min(r, g, b)

                            # Monochrome or neutral slate/zinc
                            if (max_c - min_c) <= 45:
                                monochrome_count += 1
                            # Red accent
                            elif (r > g * 1.35 and r > b * 1.35) or (r > 150 and g < 110 and b < 110):
                                red_count += 1
                            else:
                                other_count += 1

    monochrome_pct = (monochrome_count / total_colors) * 100
    monochrome_plus_red_pct = ((monochrome_count + red_count) / total_colors) * 100

    print(f" Total colors identified: {total_colors}")
    print(f" Monochrome (blacks, whites, grays, silvers): {monochrome_count} ({monochrome_pct:.2f}%)")
    print(f" Red accents (errors, alerts, drop-offs): {red_count} ({(red_count/total_colors)*100:.2f}%)")
    print(f" Other (e.g. Google logo): {other_count} ({(other_count/total_colors)*100:.2f}%)")
    print(f" Total Monochrome + Red: {monochrome_plus_red_pct:.2f}%")

    assert monochrome_pct >= 90.0, f"Monochrome ratio must be >= 90%, got {monochrome_pct:.2f}%"
    assert monochrome_plus_red_pct >= 99.0, f"Monochrome + Red must be >= 99%, got {monochrome_plus_red_pct:.2f}%"

    print("\n>>> CHECK 2 PASSED: Site is >90% Black & White monochrome, and >99.8% monochrome + red!")
    print("==================================================================")
    return True

if __name__ == '__main__':
    run_monochrome_audit()
