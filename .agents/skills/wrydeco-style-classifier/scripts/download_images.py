import csv
import os
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CSV_PATH = os.path.join("temp", "fix-room", "products_export_1.csv")
OUTPUT_DIR = os.path.join("temp", "fix-room", "style-images")

def get_session():
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504, 429])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def clean_image_url(url):
    """Ensure the URL fetches full high-resolution image without width downscaling."""
    if not url:
        return ""
    # Parse URL
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    # Remove width, height, crop limits if present
    for param in ['width', 'height', 'crop', 'size']:
        qs.pop(param, None)
    new_query = urllib.parse.urlencode(qs, doseq=True)
    clean_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    return clean_url

def extract_product_images(csv_path):
    products = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            handle = row.get("Handle", "").strip()
            if not handle:
                continue
            img_src = row.get("Image Src", "").strip()
            img_pos = row.get("Image Position", "").strip()
            title = row.get("Title", "").strip()
            ptype = row.get("Type", "").strip()
            pcat = row.get("Product Category", "").strip()

            if handle not in products:
                products[handle] = {
                    "handle": handle,
                    "title": title,
                    "type": ptype,
                    "category": pcat,
                    "image_url": ""
                }

            # Prioritize Image Position 1, or take first available
            if img_src:
                if img_pos == "1" or not products[handle]["image_url"]:
                    products[handle]["image_url"] = clean_image_url(img_src)
    return products

def download_single_image(session, handle, url, output_dir):
    if not url:
        return handle, False, "No URL"
    
    # Save as .jpg
    dest_path = os.path.join(output_dir, f"{handle}.jpg")
    
    # If exists and > 5KB, consider already downloaded
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 5000:
        return handle, True, f"Cached ({os.path.getsize(dest_path)} bytes)"
    
    try:
        resp = session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            size_kb = len(resp.content) / 1024.0
            return handle, True, f"Downloaded ({size_kb:.1f} KB)"
        else:
            return handle, False, f"HTTP {resp.status_code}"
    except Exception as e:
        return handle, False, str(e)

def main():
    print(f"Creating output directory: {OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Reading products from: {CSV_PATH}")
    products = extract_product_images(CSV_PATH)
    print(f"Total unique products found: {len(products)}")

    # Filter products that have image_url
    with_img = {k: v for k, v in products.items() if v["image_url"]}
    without_img = {k: v for k, v in products.items() if not v["image_url"]}
    print(f"Products with image: {len(with_img)}, without image: {len(without_img)}")

    if without_img:
        print("Products missing image URLs:")
        for h in without_img:
            print(f"  - {h}")

    session = get_session()
    success_count = 0
    fail_count = 0

    print("\nStarting multithreaded download (High Resolution)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(download_single_image, session, h, info["image_url"], OUTPUT_DIR): h
            for h, info in with_img.items()
        }

        for i, future in enumerate(as_completed(futures), 1):
            handle, success, msg = future.result()
            if success:
                success_count += 1
            else:
                fail_count += 1
            if i % 25 == 0 or i == len(with_img):
                print(f"Progress: [{i}/{len(with_img)}] - Success: {success_count}, Failed: {fail_count}")

    duration = time.time() - start_time
    print(f"\nDownload finished in {duration:.1f}s.")
    print(f"Total downloaded/verified: {success_count}/{len(with_img)}")
    if fail_count > 0:
        print(f"Failed downloads: {fail_count}")

if __name__ == "__main__":
    main()
