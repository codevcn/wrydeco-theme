from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import sys

class SaveHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        relpath = qs.get("relpath", ["test.png"])[0]
        
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        
        dest = Path(r"D:\D-Temps\wrydeco-data-san-pham-guong") / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        msg = f"Saved: {relpath} ({len(body)} bytes)"
        self.wfile.write(msg.encode("utf-8"))
        print(f"[SAVED] {relpath} ({len(body) / 1024:.1f} KB)", flush=True)

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    server = HTTPServer(("127.0.0.1", 8765), SaveHandler)
    print("Receiver server listening on 127.0.0.1:8765", flush=True)
    server.serve_forever()
