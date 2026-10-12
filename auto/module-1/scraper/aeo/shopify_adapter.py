"""Empty-only write policy; depends on a client protocol, not AGY or core IO."""
from ..errors import ShopifyError


def apply_html(client, product_id: str, value: str) -> dict:
    for attempt in range(2):
        current = client.read_aeo_metafield(product_id)
        if current and current["type"] != "multi_line_text_field":
            raise ShopifyError("custom.aeo_html has an incompatible metafield type; no type was changed.")
        existing = (current or {}).get("value", "")
        if existing.strip():
            return {"verified": True, "status": "verified" if existing == value else "preserved", "value": existing}
        client.ensure_aeo_definition()
        try:
            client.write_aeo_metafield(product_id, value, (current or {}).get("compareDigest"))
        except ShopifyError:
            # A concurrent edit/unknown write outcome must never trigger an overwrite.
            latest = client.read_aeo_metafield(product_id)
            if latest and latest.get("value", "").strip() and latest["type"] == "multi_line_text_field":
                return {"verified": True, "status": "verified" if latest["value"] == value else "preserved", "value": latest["value"]}
            raise
        after = client.read_aeo_metafield(product_id)
        if after and after["type"] == "multi_line_text_field" and after["value"] == value:
            return {"verified": True, "status": "written", "value": value}
        if after and after.get("value", "").strip():
            raise ShopifyError("AEO read-back differs from the written HTML; review the saved evidence.")
    raise ShopifyError("AEO metafield read-back did not converge.")
