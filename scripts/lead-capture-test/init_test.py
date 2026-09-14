import re
from pathlib import Path
from remove_test import clean_lead_capture_popup

HTML_BLOCK = """<!-- [DEV-TEST-START:HTML] -->
<button
  type="button"
  class="lead-capture-test-toggle"
  data-lead-capture-test-toggle
  aria-controls="LeadCaptureDialog"
  aria-expanded="false"
  hidden
>
  Test lead popup
</button>

<button
  type="button"
  class="lead-capture-test-toggle lead-capture-test-toggle--success"
  data-lead-capture-test-success-toggle
  aria-controls="LeadCaptureDialog"
  aria-expanded="false"
  hidden
>
  Test success popup
</button>
<!-- [DEV-TEST-END:HTML] -->
"""

CSS_BLOCK = """  /* [DEV-TEST-START:CSS] */
  .lead-capture-test-toggle[hidden] {
    display: none;
  }

  .lead-capture-test-toggle {
    position: fixed;
    z-index: calc(var(--z-drawer) + 11);
    bottom: var(--sp-12);
    left: var(--sp-4);
    min-height: var(--sp-7);
    padding: var(--sp-2) var(--sp-4);
    border: var(--border-width) solid var(--color-clay);
    border-radius: var(--radius-full);
    background: var(--color-brown-dark);
    box-shadow: var(--shadow-elevation-2);
    color: var(--text-inverse);
    cursor: pointer;
    font-family: var(--font-body);
    font-size: var(--font-size-body-sm);
    font-weight: var(--font-weight-semibold);
  }

  .lead-capture-test-toggle--success {
    bottom: calc(var(--sp-4) * 2 + var(--sp-7));
  }

  .lead-capture-test-toggle:hover {
    background: var(--color-brown);
  }

  .lead-capture-test-toggle:focus-visible {
    outline: var(--border-width) solid var(--color-sage);
    outline-offset: var(--sp-1);
  }
  /* [DEV-TEST-END:CSS] */
"""

JS_BLOCK = """    /* [DEV-TEST-START:JS] */
    (function initDevTestControls() {
      var testToggle = document.querySelector('[data-lead-capture-test-toggle]');
      var testSuccessToggle = document.querySelector('[data-lead-capture-test-success-toggle]');
      if (!testToggle) return;

      if (new URLSearchParams(window.location.search).get('lead_popup_test') === '1') {
        testToggle.hidden = false;
        testToggle.addEventListener('click', function () {
          if (isOpen) {
            closePopup();
            testToggle.setAttribute('aria-expanded', 'false');
          } else {
            openPopup(true);
            testToggle.setAttribute('aria-expanded', 'true');
          }
        });

        if (testSuccessToggle) {
          testSuccessToggle.hidden = false;
          testSuccessToggle.addEventListener('click', function () {
            showSuccess();
            if (!isOpen) {
              openPopup(true);
              testToggle.setAttribute('aria-expanded', 'true');
            }
          });
        }
      }
    })();
    /* [DEV-TEST-END:JS] */
"""

def inject_test_controls():
    clean_lead_capture_popup()
    root_dir = Path(__file__).resolve().parent.parent.parent
    target_file = root_dir / 'snippets' / 'lead-capture-popup.liquid'

    if not target_file.exists():
        print(f'[ERROR] File not found: {target_file}')
        return False

    text = target_file.read_text(encoding='utf-8')

    # 1. Inject HTML before <div class="lead-capture"
    if '<div\n  class="lead-capture"' in text:
        text = text.replace('<div\n  class="lead-capture"', HTML_BLOCK + '\n<div\n  class="lead-capture"', 1)
    elif '<div class="lead-capture"' in text:
        text = text.replace('<div class="lead-capture"', HTML_BLOCK + '\n<div class="lead-capture"', 1)
    else:
        print('[ERROR] Could not find HTML injection point <div class="lead-capture">')
        return False

    # 2. Inject CSS right after {% stylesheet %}
    css_target = '{% stylesheet %}'
    if css_target in text:
        text = text.replace(css_target, css_target + '\n' + CSS_BLOCK, 1)
    else:
        print('[ERROR] Could not find CSS injection point {% stylesheet %}')
        return False

    # 3. Inject JS right before responseParameters
    js_target = '    var responseParameters = new URLSearchParams(window.location.search);'
    if js_target in text:
        text = text.replace(js_target, JS_BLOCK + '\n' + js_target, 1)
    elif 'var responseParameters = new URLSearchParams(window.location.search);' in text:
        target_alt = 'var responseParameters = new URLSearchParams(window.location.search);'
        text = text.replace(target_alt, JS_BLOCK + '\n    ' + target_alt, 1)
    else:
        print('[ERROR] Could not find JS injection point responseParameters')
        return False

    target_file.write_text(text, encoding='utf-8')
    print('[OK] Test controls successfully injected into snippets/lead-capture-popup.liquid')
    return True

if __name__ == '__main__':
    inject_test_controls()
