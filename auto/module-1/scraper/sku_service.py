"""Shared SKU planning and read-after-write verification for both apply paths."""
from __future__ import annotations

import threading
from typing import Any, Callable

from .errors import ShopifyError
from .sku import build_sku_plan, load_rules, option_key

SKU_MUTATION_LOCK = threading.RLock()


def plan_for_product(client: Any, product_id: str, variants: list[dict[str, Any]], *,
                     tags: list[str] | str, asin: str, handle: str,
                     existing: list[dict[str, Any]], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = load_rules()
    seed = build_sku_plan(variants, tags=tags, asin=asin, handle=handle,
                          existing=existing, previous=previous, rules=rules)
    owners = client.variant_sku_owners(seed["prefix"], seed["identity"], product_id)
    return build_sku_plan(variants, tags=tags, asin=asin, handle=handle, existing=existing,
                          previous=previous, occupied=owners, rules=rules)


def verify_and_repair(client: Any, product_id: str, plan: dict[str, Any], *,
                      tags: list[str] | str, asin: str, handle: str,
                      save: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """Resume old checkpoints and repair collisions without replaying productSet."""
    for attempt in range(3):
        live = client.read_variants(product_id)
        by_key = {option_key(row["selectedOptions"]): row for row in live}
        expected = {option_key(row["options"]): row for row in plan["variants"]}
        if len(by_key) != len(live) or set(by_key) != set(expected):
            raise ShopifyError("Shopify variants differ from the saved SKU plan; no SKU was assigned by position.")
        owners = client.variant_sku_owners(plan["prefix"], plan["identity"], product_id)
        if any(row["sku"].casefold() in owners for row in plan["variants"]):
            plan = build_sku_plan([{"options": row["options"]} for row in plan["variants"]],
                                  tags=tags, asin=asin, handle=handle, existing=live,
                                  previous=plan, occupied=owners)
            save(plan)
        updates = [{"id": by_key[option_key(row["options"])]["id"], "sku": row["sku"]}
                   for row in plan["variants"]
                   if by_key[option_key(row["options"])]["sku"] != row["sku"]]
        if updates:
            client.update_variant_skus(product_id, updates)
            # Verify by an independent query, even after a successful mutation response.
            continue
        codes = [str(row.get("sku") or "").casefold() for row in live]
        if any(not code for code in codes) or len(codes) != len(set(codes)):
            raise ShopifyError("SKU verification found empty or duplicate codes.")
        return {"verified": True, "count": len(live), "repair_attempts": attempt, "plan": plan}
    raise ShopifyError("SKU verification did not converge after three passes; retry from the saved plan.")
