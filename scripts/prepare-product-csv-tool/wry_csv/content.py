from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any

from .common import ROOT, require

sys.path.insert(0, str(ROOT / "auto/module-1"))
from scraper.aeo import build_input, validate_and_render
from scraper.content import (
    content_fingerprints, content_similarity, source_digest, validate_content,
    validate_content_grounding, validate_visual_analysis, validate_visual_keyword_usage,
)
from scraper.sku import build_sku_plan

# Matches Module 1 OrchestratorStore._content_collisions; covered by a drift test.
THRESHOLDS = {"title": .88, "seo_product_title": .88, "seo_title": .88,
              "seo_description": .85, "description_html": .82, "handle": 1., "aeo_html": .97}


def evidence_context(product: dict, gallery_paths: list[str]) -> tuple[dict, dict, dict]:
    evidence = product["evidence"]
    source = deepcopy(evidence["source"])
    require(bool(source.get("title")), "evidence.source.title must identify the sold product")
    require(isinstance(source.get("bullets", []), list), "source.bullets must be an array")
    visual = deepcopy(evidence["visual"])
    visual.update(task_id=product["id"], source_digest=source_digest(source))
    visual = validate_visual_analysis(visual, expected_task_id=product["id"],
                                     expected_source_digest=source_digest(source),
                                     allowed_evidence_ids=set(gallery_paths))
    context = build_input({"product_type": product["type"], "asin": product.get("asin", "")},
                          source, {"variants": product["variants"]}, visual)
    return source, visual, context


def check_content(product: dict, gallery_paths: list[str]) -> tuple[dict, dict]:
    source, visual, context = evidence_context(product, gallery_paths)
    actual = deepcopy(product["content"])
    require(actual["handle"] == product["handle"], "content.handle differs from product.handle")
    require(not re.search(r"<[^>]*>|https?://|[\r\n]", actual["title"]), "Title must be plain text")
    copy = deepcopy(actual)
    exceptions = []
    if product.get("approved_artwork_title") is not None:
        require(actual["title"] == product["approved_artwork_title"], "Approved artwork title was altered")
        copy["title"] = actual["seo_product_title"]
        exceptions.append("Artwork title preserved; commercial title validated separately")
    if not 50 <= len(actual["handle"]) <= 60:
        require(product.get("approved_handle") == actual["handle"], "Short/long handle requires approved_handle")
        copy["handle"] = "validation-only-" + "product-" * 4 + "handle"
        exceptions.append("Approved handle preserved; length check uses a validation-only handle")
    validate_content(copy, require_aeo=True)
    grounding_source = deepcopy(source)
    grounding_source["bullets"] = [*source.get("bullets", []),
                                   *visual["design_keywords"], *visual["shape_keywords"]]
    validate_content_grounding(copy, grounding_source)
    validate_visual_keyword_usage(copy, visual)
    aeo = validate_and_render(context, actual["aeo"])
    actual["aeo"] = aeo["draft"]
    actual["aeo_html"] = aeo["html"]
    return actual, {"product_id": product["id"], "seo_grounding": True, "visual": True, "aeo": aeo,
                    "aeo_context": context, "exceptions": exceptions,
                    "fingerprints": content_fingerprints(actual)}


def compare_content(products: list[dict], reports: list[dict], history: Path | None, prior_reports: list[Path] = ()) -> dict:
    prior = []
    coverage = {"source": str(history) if history else None, "records": 0, "complete_catalog": False}
    if history and history.is_file():
        try:
            with sqlite3.connect(history.resolve().as_uri() + "?mode=ro", uri=True) as db:
                rows = db.execute("SELECT product_id, field, normalized_text, sha256 FROM content_fingerprints WHERE active=1").fetchall()
            prior = [(str(pid), field, normalized, digest) for pid, field, normalized, digest in rows]
            coverage["records"] = len(prior)
        except sqlite3.Error:
            coverage["unavailable"] = "Existing history index could not be read"
    else:
        coverage["unavailable"] = "No existing Module 1 history index"
    coverage["prior_handoffs"] = []
    from .common import read_json
    for path in prior_reports:
        handoff = read_json(path)
        require(handoff.get("valid") and handoff.get("manifest_compared"), f"Prior report is not a validated handoff: {path}")
        old = handoff.get("content_validation", {}).get("content", [])
        require(old, f"Prior handoff has no content fingerprints: {path}")
        records = 0
        for product in old:
            for field, fingerprint in product["fingerprints"].items():
                prior.append((f'{path.name}:{product["product_id"]}', field, fingerprint["normalized"], fingerprint["sha256"]))
                records += 1
        coverage["prior_handoffs"].append({"path": str(path), "records": records})
    collisions = []
    for product, report in zip(products, reports):
        for field, fingerprint in report["fingerprints"].items():
            if field not in THRESHOLDS:
                continue
            for other, prior_field, normalized, digest in prior:
                if prior_field != field:
                    continue
                exact = digest == fingerprint["sha256"]
                score = 1. if exact else content_similarity(field, fingerprint["normalized"], normalized)
                if exact or score >= THRESHOLDS[field]:
                    collisions.append({"product": product["id"], "other": other, "field": field, "score": round(score, 4)})
        prior.extend((product["id"], field, fp["normalized"], fp["sha256"])
                     for field, fp in report["fingerprints"].items())
    return {"historical_coverage": coverage, "collisions": collisions}
