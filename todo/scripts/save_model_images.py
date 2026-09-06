import json
import base64
from pathlib import Path
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEST_ROOT = Path(r"D:\D-Temps\wrydeco-data-san-pham-guong")
JSON_PATH = Path(r"C:\Users\dell\AppData\Local\Programs\Antigravity\.playwright-mcp\model_data.json")

def process():
    if not JSON_PATH.exists():
        print(f"File not found: {JSON_PATH}")
        return 0

    try:
        content = JSON_PATH.read_text(encoding="utf-8")
        # In case the evaluate result is wrapped in quotes
        if content.startswith('"') and content.endswith('"'):
            content = json.loads(content)
        data = json.loads(content) if isinstance(content, str) else content
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return 0

    col = data.get("collection", "Rustic")
    model = data.get("model", "Model 1")
    items = data.get("items", [])

    model_dir = DEST_ROOT / col / model
    model_dir.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for item in items:
        fname = item["filename"]
        b64 = item["base64"]
        if "," in b64:
            b64 = b64.split(",", 1)[1]
        file_bytes = base64.b64decode(b64)
        out_path = model_dir / fname
        out_path.write_bytes(file_bytes)
        print(f"  [SAVED] {col}/{model}/{fname} ({len(file_bytes) / 1024:.1f} KB)")
        saved_count += 1

    JSON_PATH.unlink()
    return saved_count

if __name__ == "__main__":
    count = process()
    print(f"Total processed: {count} images.")
