"""Run-local IO adapter. Missing version metadata denotes a legacy SEO-only run."""
from pathlib import Path
from ..io_utils import atomic_write_json, load_json
from .core import schema, build_input


def enabled(options: dict) -> bool:
    return options.get("aeo_version") == 1


def prompt_text(package_root: Path) -> str:
    path = package_root / "aeo" / "PROMPT.md"
    if not path.is_file():
        path = Path(__file__).with_name("PROMPT.md")
    return path.read_text(encoding="utf-8-sig")


def freeze_contract(package_root: Path, run_root: Path) -> None:
    atomic_write_json(run_root / "aeo-contract.json", {"version": 1, "prompt": prompt_text(package_root), "schema": schema()})


def read_contract(run_root: Path) -> dict:
    return load_json(run_root / "aeo-contract.json")


def workspace_input(product: dict, workspace: Path) -> dict:
    source = load_json(workspace / "source.json")
    pricing_path = workspace / "pricing.json"
    visual_path = workspace / "visual_analysis.json"
    return build_input({"asin": product["asin"], "product_type": (product.get("overrides") or {}).get("product_type", "")},
                       source, load_json(pricing_path) if pricing_path.exists() else {},
                       load_json(visual_path) if visual_path.exists() else {})
