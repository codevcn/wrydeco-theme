# Amazon–Shopify scraper

The scraper runs with a persistent Playwright Chromium profile and does not require the Chrome extension.

## Local dashboard

Install dependencies, then start the local-only dashboard:

```powershell
python -m pip install -r scraper/requirements.txt
python -m scraper serve --host 127.0.0.1 --port 5000
```

Open `http://127.0.0.1:5000`. The dashboard edits `scraper/input/products.json`, snapshots the editable
Antigravity prompt per execution, streams progress over SSE, and resumes from the same product checkpoints.
Only one batch runs at a time.

To let the server invoke Antigravity automatically, set `ANTIGRAVITY_COMMAND_JSON=["agy"]` in `scraper/.env`.
Opening the dashboard starts or resumes one persistent CLI conversation. Its `conversation_id`, turn count and
connection state are saved atomically under `scraper/.runtime/server/antigravity/state.json`, so restarting the
dashboard or Windows continues the same conversation with `--conversation`. The CLI uses `stream-json`; every
stdout/stderr event and heartbeat appears in the dashboard Event log. Every process uses `shell=False`. When no command
is configured, the dashboard safely stops at **waiting for Agent**; copy the prompt, create the requested
`content.json` files manually, then press **Resume checkpoint**.

The server owns crawl and Shopify operations. Antigravity only writes `content.json` and must not launch a
second scraper process.

## CLI

```powershell
python -m pip install -r scraper/requirements.txt
python -m playwright install chromium
Copy-Item scraper/input/products.example.json scraper/input/products.json
python -m scraper run --manifest scraper/input/products.json
```

The first run crawls Amazon, verifies every dynamic price combination, and writes one workspace per ASIN under `scraper/runs/<manifest-id>/<ASIN>/`. If `content.json` is absent, the product stops safely at `price_verified`. The AI Agent should read `source.json` and `evidence/`, write `content.json` according to `scraper/content.schema.json`, then run the same command again. The second run validates content and applies the product to Shopify.

For the content-authoring instruction used by the dashboard, see `scraper/AGENT_PROMPT.md`.

Use `--dry-run` to crawl/validate without Shopify mutations, `--headless` for unattended Chromium, and `--max-combinations` to lower the default safety cap of 100.
The browser sets Amazon's delivery location to ZIP `10001` by default so US offers and customization controls render; override it with `--amazon-postal-code`.

`auto` first attempts Amazon Dynamic Mode. If customization is unavailable, it only falls back when that manifest item contains a valid `preset`; it never guesses a price table. CAPTCHA/challenge evidence is saved and the item becomes `needs_attention` while the batch continues.
