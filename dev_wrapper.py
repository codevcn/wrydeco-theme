import subprocess
import sys
import threading
import re
import os

# Auto-install qrcode if missing
try:
    import qrcode
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "qrcode"])
    import qrcode


def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    sys.stdout.write(f"\n[SCAN TO PREVIEW: {url}]\n\n")
    sys.stdout.flush()
    qr.print_ascii(invert=True)
    sys.stdout.write("\n")
    sys.stdout.flush()


def read_output(process):
    # Pattern to match URLs
    url_pattern = re.compile(r"(https?://[a-zA-Z0-9\-\.\/\?\=\&\_]+)")
    generated_urls = set()

    # State to manage the debouncing timer
    state = {"pending": None, "timer": None}

    def print_pending():
        url = state["pending"]
        if url and url not in generated_urls:
            generate_qr(url)
            generated_urls.add(url)
        state["pending"] = None

    for line in iter(process.stdout.readline, ""):
        # Always output the CLI logs immediately
        sys.stdout.write(line)
        sys.stdout.flush()

        clean_line = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", line)

        # Detect the preview URL
        if "preview_theme_id=" in clean_line:
            match = url_pattern.search(clean_line)
            if match:
                url = match.group(1)
                if url not in generated_urls:
                    state["pending"] = url

        # If we have a pending URL, wait for 0.5s of silence before printing it
        # This prevents the QR code from breaking the middle of the Shopify CLI UI box!
        if state["pending"]:
            if state["timer"]:
                state["timer"].cancel()
            state["timer"] = threading.Timer(0.5, print_pending)
            state["timer"].daemon = True
            state["timer"].start()


def main():
    print("Starting Shopify theme development server with QR code...\n")

    cmd = "shopify theme dev --store wrydeco.myshopify.com"
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=sys.stdin,
        text=True,
        bufsize=1,
        env=env,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )

    output_thread = threading.Thread(target=read_output, args=(p,))
    output_thread.daemon = True
    output_thread.start()

    p.wait()


if __name__ == "__main__":
    main()
