from __future__ import annotations

import argparse
from pathlib import Path

from .common import ROOT, TOOL, Invalid, read_json, write_json
from .content import evidence_context
from .exporter import (load_manifest, prepare, render_rows, template_headers, verify_csv, build_csv)
from .shopify import Admin, stage


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="WRYDECO native Shopify Admin CSV tool (never imports/publishes products)")
    sub = root.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Write an editable JSON manifest skeleton, never a CSV")
    init.add_argument("--out", type=Path, required=True)
    snapshot = sub.add_parser("snapshot", help="Read live shop, choices, authors, collections, taxonomy, handles and SKUs")
    snapshot.add_argument("--manifest", type=Path, required=True)
    snapshot.add_argument("--out", type=Path, required=True)
    context = sub.add_parser("context", help="Compile AEO fact IDs from the supplied ledger and visual record")
    context.add_argument("--manifest", type=Path, required=True)
    context.add_argument("--out", type=Path, required=True)
    for name in ("check", "stage", "build", "verify"):
        cmd = sub.add_parser(name, help={"check": "Validate the entire manifest before uploads",
            "stage": "Upload approved local photos to Shopify Files with a resumable checkpoint",
            "build": "Build and double-check final 71-column CSV; all images must pass public GET",
            "verify": "Independently read and audit a saved CSV"}[name])
        cmd.add_argument("--manifest", type=Path, required=name != "verify")
        cmd.add_argument("--template", type=Path, default=ROOT / "temp/template_products_shopify_export.csv")
        cmd.add_argument("--snapshot", type=Path)
        cmd.add_argument("--checkpoint", type=Path)
        cmd.add_argument("--history", type=Path, default=ROOT / "auto/module-1/scraper/.runtime/orchestrator.sqlite3")
        cmd.add_argument("--prior-report", type=Path, action="append", default=[], help="Compare with a previous verified batch report; repeat for multiple handoffs")
        cmd.add_argument("--report", type=Path, required=True)
        if name == "stage":
            cmd.add_argument("--upload-files", action="store_true", help="Explicitly enable Shopify Files writes")
        if name == "build":
            cmd.add_argument("--out", type=Path, required=True)
        if name == "verify":
            cmd.add_argument("--csv", type=Path, required=True)
            cmd.add_argument("--offline", action="store_true", help="Local audit only; never marked ready for import")
    return root


def run(args) -> dict:
    if args.command == "init":
        if args.out.exists():
            raise Invalid("Manifest already exists; refusing to overwrite")
        write_json(args.out, read_json(TOOL / "manifest.example.json"))
        return {"valid": True, "manifest": str(args.out.resolve()), "next": "Replace example data; see references/tool.md"}
    manifest = load_manifest(args.manifest) if args.manifest else None
    if args.command == "snapshot":
        data = Admin().snapshot(manifest)
        write_json(args.out, data)
        return {"valid": True, "shop": data["shop"], "currency": data["currency"], "authors": len(data["authors"]),
                "collections": len(data["collections"]), "categories": len(data["categories"]), "snapshot": str(args.out.resolve())}
    if args.command == "context":
        contexts = {}
        for product in manifest["products"]:
            _, _, contexts[product["id"]] = evidence_context(product, [image["path"] for image in product["images"]])
        write_json(args.out, contexts)
        return {"valid": True, "products": len(contexts), "context": str(args.out.resolve())}
    template_headers(args.template)
    snapshot = read_json(args.snapshot) if args.snapshot else None
    checkpoint = read_json(args.checkpoint) if args.checkpoint and args.checkpoint.exists() else {}
    products, content_report = [], {}
    if manifest:
        if snapshot is None:
            raise Invalid("--snapshot from the live snapshot command is required with a manifest")
        products, content_report = prepare(manifest, args.manifest.resolve().parent, snapshot, checkpoint,
                                           args.history, require_urls=args.command in {"build", "verify"}, prior_reports=args.prior_report)
        if not content_report["valid"]:
            return {**content_report, "ready_for_import": False}
    if args.command == "check":
        # Structural check also covers defaults/overrides before any external mutation.
        from .exporter import serialize
        from .common import atomic_write
        from tempfile import TemporaryDirectory
        # Missing public URLs are allowed during pre-upload check. Use reserved
        # example URLs ONLY in this ephemeral internal validation copy, never output CSV.
        from copy import deepcopy
        preview = deepcopy(products)
        for product in preview:
            for index, image in enumerate(product["images"], 1):
                image["url"] = image.get("url") or f'https://example.invalid/{product["id"]}/{index}.png'
        rows = render_rows(preview, template_headers(args.template))
        with TemporaryDirectory(prefix="wry-csv-check-") as directory:
            path = Path(directory) / "check.csv"
            atomic_write(path, serialize(template_headers(args.template), rows))
            local = verify_csv(path, args.template, expected=rows, snapshot=snapshot, online=False)
        return {**local, "ready_for_import": False, "content_validation": content_report, "phase": "pre-upload check"}
    if args.command == "stage":
        if not args.upload_files or args.checkpoint is None:
            raise Invalid("stage requires --upload-files and --checkpoint; no product/theme mutations are supported")
        # Reuse full pre-upload structural validation, including field overrides.
        from copy import copy
        check_args = copy(args)
        check_args.command = "check"
        local = run(check_args)
        if not local["valid"]:
            return local
        data = stage(products, checkpoint, args.checkpoint, Admin())
        return {"valid": True, "ready_for_import": False, "files": len(data["files"]),
                "checkpoint": str(args.checkpoint.resolve()), "content_validation": content_report}
    if args.command == "build":
        return {**build_csv(args.out, products, args.template, snapshot), "content_validation": content_report,
                "output": str(args.out.resolve())}
    expected = render_rows(products, template_headers(args.template)) if manifest else None
    return {**verify_csv(args.csv, args.template, expected=expected, snapshot=snapshot, online=not args.offline),
            "content_validation": content_report}


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    report_path = getattr(args, "report", None)
    try:
        inputs = [getattr(args, name, None) for name in ("manifest", "template", "snapshot", "history", "csv")]
        inputs.extend(getattr(args, "prior_report", []))
        input_paths = {p.resolve() for p in inputs if p is not None}
        if report_path and report_path.resolve() in input_paths | {p.resolve() for p in (getattr(args, "out", None), getattr(args, "checkpoint", None)) if p is not None}:
            report_path = None
            raise Invalid("Report path must differ from all inputs, checkpoint and CSV output; no file overwritten")
        for name in ("out", "checkpoint"):
            path = getattr(args, name, None)
            if path and path.resolve() in input_paths:
                raise Invalid(f"--{name} must not overwrite an input")
        report = run(args)
    except Exception as exc:
        # API exceptions are sanitized at their boundary. No config/header dumps.
        report = {"valid": False, "ready_for_import": False, "errors": [{"error": str(exc)}]}
    if report_path:
        write_json(report_path, report)
    errors = len(report.get("errors", [])) + len(report.get("collisions", []))
    print(f"{args.command}: {'PASS' if report['valid'] else 'FAIL'}; errors={errors}; ready_for_import={report.get('ready_for_import', False)}")
    for error in report.get("errors", [])[:8]:
        print(str(error))
    if report_path:
        print("Report:", report_path.resolve())
    return 0 if report["valid"] else 1
