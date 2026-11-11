---
name: shopify-import-proxy
description: Safely validate and import Shopify product-export CSV files into the WRYDECO Shopify store through the repository's enforced Windows proxy gate. Use only for WRYDECO CSV product imports that must not make direct WAN requests from the importer.
---

# WRYDECO Shopify CSV Import Through Enforced Proxy

## Purpose

Use this skill when the user asks to validate, dry-run, test, resume, or execute a Shopify product CSV import for the WRYDECO store.

The tool is located at:

`scripts\import-products-proxy-tool\`

The target store is locked to:

`wrydeco.myshopify.com`

The tool performs:

Shopify CSV
→ local importer
→ local proxy gate
→ configured upstream proxy
→ Shopify Admin GraphQL API

During real preflight/import, the tool activates a machine-wide WinDivert egress lockdown.

Only the local gate process may create a non-loopback connection, and even the gate may only connect to the pinned upstream proxy IPv4 address and port.

All other direct WAN traffic is blocked while enforcement is active.

---

# Security rules

These rules are mandatory.

1. NEVER print, read aloud, paste into chat, summarize, archive, copy, or expose:

   - `scripts\import-products-proxy-tool\.proxy.env`
   - proxy username
   - proxy password
   - proxy URL containing credentials
   - Shopify Admin access token
   - `admin\.env`

2. NEVER hardcode secrets in source code.

3. NEVER add `.proxy.env`, `admin\.env`, logs containing secrets, or token material to Git.

4. NEVER bypass the proxy gate for Shopify API requests.

5. NEVER disable the kill switch because a request is failing.

6. NEVER continue a real import when network verification fails.

7. NEVER disable Windows Defender, HVCI, Secure Boot, Driver Signature Enforcement, or antivirus automatically.

8. NEVER silently ignore unsupported Shopify CSV fields.

9. NEVER import to a store other than `wrydeco.myshopify.com`.

10. NEVER claim that the proxy makes the user's real-world location unknowable to Shopify. Report only the verified network-egress property.

---

# Before first use

From PowerShell:

```powershell
cd <repo>\scripts\import-products-proxy-tool
```

powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

Bootstrap must:

- use Python 3.12+
- install Python dependencies
- download the pinned official WinDivert release
- verify its SHA-256
- verify the WinDivert64.sys Authenticode signature

If bootstrap verification fails, STOP.

Do not work around the failure by using a random WinDivert binary from another source.

Commands

Assume:

```powershell
cd <repo>\scripts\import-products-proxy-tool
```

Python executable:

```powershell
.\.venv\Scripts\python.exe
1. Local CSV dry-run
```

This does NOT change machine networking and does NOT require Administrator rights.

```powershell
.\.venv\Scripts\python.exe .\run.py dry-run `
  --csv "<csv-path>"
```

If the CSV intentionally contains packed dimensions that the current stable Shopify API cannot write:

```powershell
.\.venv\Scripts\python.exe .\run.py dry-run `
  --csv "<csv-path>" `
  --ignore-packed-dimensions
```

Only use that switch after explicitly informing the user that packed dimensions will not be imported.

To generate only missing SKUs using the WRY convention:

```powershell
.\.venv\Scripts\python.exe .\run.py dry-run `
  --csv "<csv-path>" `
  --generate-missing-skus
```

Never overwrite an existing SKU automatically.

2. Network preflight

WARNING:

This temporarily blocks direct Internet traffic for the whole Windows machine.

Run from an Administrator PowerShell:

```powershell
.\.venv\Scripts\python.exe .\run.py preflight
```

Expected final output:

PREFLIGHT PASSED

Preflight verifies:

- upstream proxy connectivity
- local proxy gate
- proxy exit public IP
- expected proxy country
- expected proxy city when configured
- direct TCP leak blocked
- direct IPv6 leak blocked
- direct UDP DNS leak blocked
- process-level egress invariant
- pktmon leak-probe evidence
- authenticated Shopify store identity

If city geolocation is known to differ only because of IP geolocation database granularity, the user may explicitly approve:

```powershell
.\.venv\Scripts\python.exe .\run.py preflight --relax-city
```

Do not use --relax-city merely to make a failing check pass.

3. Safe live test with 1-2 products

Always obtain user approval before running a test that activates machine-wide lockdown or writes to Shopify.

Example:

```powershell
.\.venv\Scripts\python.exe .\run.py import `
  --csv "<csv-path>" `
  --limit 1
```

Then inspect the created/updated Shopify product.

Repeat the exact same command to test idempotency.

The second run MUST NOT:

- create another product with the same handle
- create duplicate variants
- create duplicate SKUs
- create duplicate images
- corrupt existing unrelated metafields
- 4. Full import
```powershell
.\.venv\Scripts\python.exe .\run.py import `
  --csv "<csv-path>"
```

If a previous import was interrupted:

```powershell
.\.venv\Scripts\python.exe .\run.py import `
  --csv "<csv-path>" `
  --resume
```

Resume is allowed only when the CSV SHA-256 matches the saved import state.

If the store has multiple active inventory locations and CSV contains inventory quantities, provide the exact Shopify Location GID:

```powershell
--location-id "gid://shopify/Location/..."
```

Never guess the location ID.

Emergency restore

Normal Ctrl+C or exceptions should restore networking automatically.

If the tool or shell appears stuck, run from an Administrator PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File `
  .\panic_restore.ps1
```

or:

```powershell
.\.venv\Scripts\python.exe .\run.py restore
```

The restore command may terminate only processes whose command line matches this tool's gate/watchdog modules.

Never terminate arbitrary WinDivert processes belonging to other software.

Exit codes
| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Unexpected internal failure |
| 2 | Configuration / CSV validation failure |
| 3 | Administrator / WinDivert / driver failure |
| 4 | Upstream proxy failure |
| 5 | Network verification / leak check failure |
| 6 | Shopify API failure |
| 7 | Partial import; resume state exists |
| 8 | Restore failure |
| 130 | User interrupted with Ctrl+C |

For any non-zero exit code:

- do not report the import as successful
- do not retry blindly
- inspect sanitized reports and logs
- confirm networking is restored
- report the exact failed gate to the user
- CSV validation rules

Before writes, ensure:

- Handle is present
- Title is present
- at least one variant exists
- every variant has a non-empty SKU
- SKUs are unique inside the CSV
- SKUs follow the store's WRY-/AMZ- naming convention
- there are no SKU collisions with another Shopify product
- max 250 variants per product in this v1
- max 250 product images per product in this v1
- non-manual fulfillment services are rejected
- packed dimensions are rejected on stable API 2026-10 unless user explicitly chooses to ignore them
- product categories resolve exactly to Shopify taxonomy
- unknown metafield definitions are rejected instead of guessing their type
- Shopify synchronization behavior

The CSV is authoritative for options and variants of each Handle.

The tool uses productSet by Handle.

Be aware:

productSet replaces option/variant list state. A variant omitted from the CSV may be deleted from Shopify.

Therefore never import an incomplete subset of rows belonging to a Handle.

Metafields are written separately with metafieldsSet so unrelated metafields are not deleted.

Required report to the user

After dry-run report:

- CSV filename
- SHA-256
- product count
- variant count
- image count
- validation error count
- no secret values

After preflight report:

- PASS / FAIL
- observed proxy exit IP
- observed country
- observed city
- TCP leak result
- IPv6 leak result
- DNS leak result
- process-egress result
- pktmon evidence path
- no proxy username/password

After import report:

- number completed
- handles completed
- failed handle if any
- whether resume state exists
- whether networking was restored
- no Shopify token
- no proxy credential

Never paste .proxy.env or admin\.env content into the report.

