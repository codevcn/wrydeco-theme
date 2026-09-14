import re
from pathlib import Path

def clean_lead_capture_popup():
    root_dir = Path(__file__).resolve().parent.parent.parent
    target_file = root_dir / 'snippets' / 'lead-capture-popup.liquid'

    if not target_file.exists():
        print(f'[WARN] File not found: {target_file}')
        return False

    text = target_file.read_text(encoding='utf-8')
    original_text = text

    # 1. Remove marker-based blocks
    text = re.sub(r'[ \t]*<!-- \[DEV-TEST-START:HTML\] -->.*?<!-- \[DEV-TEST-END:HTML\] -->\n?', '', text, flags=re.DOTALL)
    text = re.sub(r'[ \t]*/\* \[DEV-TEST-START:CSS\] \*/.*?/\* \[DEV-TEST-END:CSS\] \*/\n?', '', text, flags=re.DOTALL)
    text = re.sub(r'[ \t]*/\* \[DEV-TEST-START:JS\] \*/.*?/\* \[DEV-TEST-END:JS\] \*/\n?', '', text, flags=re.DOTALL)

    # 2. Defensive fallback for legacy / unmarked buttons
    text = re.sub(r'<button[^>]*data-lead-capture-test-toggle.*?</button>\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'\.lead-capture-test-toggle\[hidden\],\s*', '', text)
    text = re.sub(r'\.lead-capture-test-toggle\s*{[^}]*}\s*', '', text)
    text = re.sub(r'\.lead-capture-test-toggle--success\s*{[^}]*}\s*', '', text)
    text = re.sub(r'\.lead-capture-test-toggle:hover\s*{[^}]*}\s*', '', text)
    text = re.sub(r'\.lead-capture-test-toggle:focus-visible,\s*', '', text)

    if text != original_text:
        target_file.write_text(text, encoding='utf-8')
        print('[OK] Test controls cleaned and removed from snippets/lead-capture-popup.liquid')
        return True
    else:
        print('[INFO] snippets/lead-capture-popup.liquid is already clean. No test controls found.')
        return False

if __name__ == '__main__':
    clean_lead_capture_popup()
