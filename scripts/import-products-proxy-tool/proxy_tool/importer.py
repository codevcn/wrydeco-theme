from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from .config import (
    DEFAULT_GATE_HOST,
    DEFAULT_GATE_PORT,
    LOG_DIR,
    REPORT_DIR,
    STATE_DIR,
    ProxyConfig,
    ShopifyConfig,
    ensure_runtime_dirs,
)
from .csv_model import (
    CsvCatalog,
    MetafieldValue,
    ProductRecord,
    VariantRecord,
    load_catalog,
    validate_catalog,
)
from .errors import (
    ConfigError,
    PartialImportError,
    PrivilegeError,
    ShopifyError,
    ToolError,
    VerificationError,
)
from .shopify import ShopifyClient
from .system import (
    PacketMonitor,
    atomic_json,
    cleanup_pktmon,
    get_logger,
    is_admin,
    pid_alive,
    read_json,
    runtime_file,
    snapshot_connections,
    terminate_if_ours,
    terminate_pid,
    write_network_snapshot,
)
from .verifier import (
    public_identity,
    verify,
)


CREATE_NO_WINDOW = getattr(
    subprocess,
    "CREATE_NO_WINDOW",
    0,
)


def wait_for_file(
    path: Path,
    process: subprocess.Popen,
    timeout: float,
) -> dict:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if path.exists():
            value = read_json(path)

            if value:
                return value

        if process.poll() is not None:
            raise RuntimeError(
                f"Child process exited early: {process.returncode}"
            )

        time.sleep(0.1)

    raise TimeoutError(
        f"Timed out waiting for {path.name}."
    )


def recover_stale_runtime() -> None:
    ensure_runtime_dirs()

    runtime = read_json(
        runtime_file(),
        {},
    )

    if not runtime:
        cleanup_pktmon()
        return

    watchdog_pid = int(
        runtime.get("watchdog_pid", 0) or 0
    )
    gate_pid = int(
        runtime.get("gate_pid", 0) or 0
    )

    if watchdog_pid:
        terminate_if_ours(
            watchdog_pid,
            "proxy_tool.watchdog",
        )

    time.sleep(0.25)

    if gate_pid:
        terminate_if_ours(
            gate_pid,
            "proxy_tool.gate_worker",
        )

    cleanup_pktmon()

    for name in [
        "stop.requested",
        "watchdog.ready.json",
        "watchdog.failure.json",
        "watchdog.stopped.json",
        "gate.ready.json",
    ]:
        (
            STATE_DIR / name
        ).unlink(missing_ok=True)

    runtime_file().unlink(
        missing_ok=True
    )


def manual_restore() -> None:
    recover_stale_runtime()


def deterministic_image_filename(
    handle: str,
    position: int,
    url: str,
) -> str:
    suffix = Path(
        urlsplit(url).path
    ).suffix.lower()

    if suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }:
        suffix = ".jpg"

    clean = "".join(
        char
        if char.isalnum() or char in {"-", "_"}
        else "-"
        for char in handle.lower()
    )

    return (
        f"wrydeco-{clean}-"
        f"{position:03d}{suffix}"
    )


def file_inputs(
    product: ProductRecord,
) -> tuple[list[dict], dict[str, dict]]:
    files = []
    by_url = {}

    for image in product.images:
        item = {
            "originalSource": image.url,
            "contentType": "IMAGE",
            "filename": deterministic_image_filename(
                product.handle,
                image.position,
                image.url,
            ),
            "duplicateResolutionMode": "REPLACE",
        }

        if image.alt:
            item["alt"] = image.alt

        files.append(item)
        by_url[image.url] = item

    return files, by_url


def metafield_inputs(
    values: list[MetafieldValue],
    owner_id: str,
    definitions: dict[tuple[str, str], str],
) -> list[dict]:
    output = []

    for item in values:
        definition_type = definitions.get(
            (
                item.namespace,
                item.key,
            )
        )

        if not definition_type:
            raise ShopifyError(
                "Metafield definition is missing for "
                f"{item.namespace}.{item.key}. "
                "Refusing to guess its data type."
            )

        output.append(
            {
                "ownerId": owner_id,
                "namespace": item.namespace,
                "key": item.key,
                "type": definition_type,
                "value": item.value,
            }
        )

    return output


def build_product_input(
    product: ProductRecord,
    category_id: str | None,
    location_id: str | None,
) -> dict:
    files, files_by_url = file_inputs(
        product
    )

    option_order = []
    option_values: dict[str, list[str]] = {}

    for variant in product.variants:
        for name, value in variant.options:
            if name not in option_values:
                option_order.append(name)
                option_values[name] = []

            if value not in option_values[name]:
                option_values[name].append(
                    value
                )

    variants = []

    for variant in product.variants:
        item = {
            "sku": variant.sku,
            "optionValues": [
                {
                    "optionName": name,
                    "name": value,
                }
                for name, value
                in variant.options
            ],
            "inventoryPolicy": (
                variant.inventory_policy
            ),
        }

        if variant.price:
            item["price"] = variant.price

        if variant.compare_at_price:
            item["compareAtPrice"] = (
                variant.compare_at_price
            )

        if variant.taxable is not None:
            item["taxable"] = variant.taxable

        if variant.barcode:
            item["barcode"] = variant.barcode

        inventory_item = {
            "sku": variant.sku,
            "tracked": (
                variant.inventory_tracked
            ),
        }

        if (
            variant.requires_shipping
            is not None
        ):
            inventory_item[
                "requiresShipping"
            ] = variant.requires_shipping

        if variant.cost:
            inventory_item["cost"] = (
                variant.cost
            )

        if variant.grams is not None:
            inventory_item[
                "measurement"
            ] = {
                "weight": {
                    "value": variant.grams,
                    "unit": "GRAMS",
                }
            }

        item["inventoryItem"] = (
            inventory_item
        )

        if variant.inventory_qty is not None:
            if not location_id:
                raise ShopifyError(
                    f"{product.handle}/{variant.sku}: "
                    "inventory quantity is present "
                    "but no Shopify location was selected."
                )

            item["inventoryQuantities"] = [
                {
                    "locationId": location_id,
                    "name": "available",
                    "quantity": (
                        variant.inventory_qty
                    ),
                }
            ]

        if variant.variant_image:
            file_item = files_by_url.get(
                variant.variant_image
            )

            if not file_item:
                raise ShopifyError(
                    f"{product.handle}/{variant.sku}: "
                    "variant image is not present "
                    "in product file set."
                )

            item["file"] = file_item

        variants.append(item)

    product_input = {
        "handle": product.handle,
        "title": product.title,
        "descriptionHtml": (
            product.description_html
        ),
        "vendor": product.vendor,
        "productType": product.product_type,
        "tags": product.tags,
        "status": product.status,
        "productOptions": [
            {
                "name": name,
                "position": index,
                "values": [
                    {
                        "name": value,
                    }
                    for value
                    in option_values[name]
                ],
            }
            for index, name
            in enumerate(
                option_order,
                start=1,
            )
        ],
        "variants": variants,
        "files": files,
    }

    if category_id:
        product_input[
            "category"
        ] = category_id

    seo = {}

    if product.seo_title:
        seo["title"] = product.seo_title

    if product.seo_description:
        seo[
            "description"
        ] = product.seo_description

    if seo:
        product_input["seo"] = seo

    return product_input


def select_inventory_location(
    client: ShopifyClient,
    catalog: CsvCatalog,
    requested_id: str | None,
) -> str | None:
    needs_inventory = any(
        variant.inventory_qty is not None
        for product in catalog.products
        for variant in product.variants
    )

    if not needs_inventory:
        return None

    locations = [
        location
        for location in client.locations()
        if location.get("isActive")
    ]

    if requested_id:
        if not any(
            location["id"] == requested_id
            for location in locations
        ):
            raise ShopifyError(
                "Requested --location-id "
                "is not an active Shopify location."
            )

        return requested_id

    if len(locations) == 1:
        return locations[0]["id"]

    raise ShopifyError(
        "CSV contains inventory quantities and the "
        f"store has {len(locations)} active locations. "
        "Pass --location-id explicitly."
    )


def validate_remote_sku_collisions(
    client: ShopifyClient,
    catalog: CsvCatalog,
) -> None:
    sku_to_handle = {
        variant.sku.casefold(): product.handle
        for product in catalog.products
        for variant in product.variants
    }

    owners = client.find_sku_owners(
        variant.sku
        for product in catalog.products
        for variant in product.variants
    )

    conflicts = []

    for sku, handles in owners.items():
        expected_handle = (
            sku_to_handle.get(sku)
        )

        unexpected = {
            handle
            for handle in handles
            if handle != expected_handle
        }

        if unexpected:
            conflicts.append(
                {
                    "sku": sku,
                    "expected": expected_handle,
                    "existing": sorted(
                        unexpected
                    ),
                }
            )

    if conflicts:
        raise ShopifyError(
            "SKU collision with existing Shopify "
            "products: "
            + json.dumps(
                conflicts,
                ensure_ascii=False,
            )
        )


@contextmanager
def enforced_proxy_session(
    relax_city: bool,
):
    ensure_runtime_dirs()
    recover_stale_runtime()

    if not is_admin():
        raise PrivilegeError(
            "This command requires an Administrator PowerShell."
        )

    proxy = ProxyConfig.load()
    shopify = ShopifyConfig.load()

    secrets = (
        proxy.secret_values()
        + shopify.secret_values()
    )

    log = get_logger(
        "proxy-tool",
        secrets,
    )

    proxy_ips = proxy.resolve_ipv4()

    baseline = snapshot_connections()

    write_network_snapshot(
        "preflight-before-lockdown"
    )

    gate_ready = (
        STATE_DIR / "gate.ready.json"
    )
    watchdog_ready = (
        STATE_DIR / "watchdog.ready.json"
    )
    stop_file = (
        STATE_DIR / "stop.requested"
    )

    gate_ready.unlink(
        missing_ok=True
    )
    watchdog_ready.unlink(
        missing_ok=True
    )
    stop_file.unlink(
        missing_ok=True
    )

    gate_log_path = (
        LOG_DIR / "gate-worker.log"
    )
    watchdog_log_path = (
        LOG_DIR / "watchdog.log"
    )

    gate_log = gate_log_path.open(
        "a",
        encoding="utf-8",
    )
    watchdog_log = (
        watchdog_log_path.open(
            "a",
            encoding="utf-8",
        )
    )

    gate_process = None
    watchdog_process = None
    pktmon = None

    try:
        gate_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "proxy_tool.gate_worker",
                "--host",
                DEFAULT_GATE_HOST,
                "--port",
                str(DEFAULT_GATE_PORT),
                "--proxy-ips",
                ",".join(proxy_ips),
                "--ready-file",
                str(gate_ready),
            ],
            cwd=str(
                Path(__file__)
                .resolve()
                .parents[1]
            ),
            stdout=gate_log,
            stderr=gate_log,
            creationflags=CREATE_NO_WINDOW,
        )

        wait_for_file(
            gate_ready,
            gate_process,
            timeout=20,
        )

        watchdog_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "proxy_tool.watchdog",
                "--parent-pid",
                str(os.getpid()),
                "--gate-pid",
                str(gate_process.pid),
                "--proxy-ips",
                ",".join(proxy_ips),
                "--proxy-port",
                str(proxy.port),
                "--state-dir",
                str(STATE_DIR),
            ],
            cwd=str(
                Path(__file__)
                .resolve()
                .parents[1]
            ),
            stdout=watchdog_log,
            stderr=watchdog_log,
            creationflags=CREATE_NO_WINDOW,
        )

        atomic_json(
            runtime_file(),
            {
                "parent_pid": os.getpid(),
                "gate_pid": gate_process.pid,
                "watchdog_pid": (
                    watchdog_process.pid
                ),
                "gate_port": (
                    DEFAULT_GATE_PORT
                ),
                "proxy_ips": proxy_ips,
                "proxy_port": proxy.port,
            },
        )

        wait_for_file(
            watchdog_ready,
            watchdog_process,
            timeout=15,
        )

        log.info(
            "Machine-wide network lockdown is active."
        )

        pktmon = PacketMonitor(
            prefix=(
                f"preflight-{int(time.time())}"
            )
        )
        pktmon.start()

        local_proxy = (
            f"http://{DEFAULT_GATE_HOST}:"
            f"{DEFAULT_GATE_PORT}"
        )

        result = verify(
            proxy_config=proxy,
            local_proxy_url=local_proxy,
            baseline_connections=baseline,
            gate_pid=gate_process.pid,
            proxy_ips=proxy_ips,
            relax_city=relax_city,
        )

        report_path = (
            REPORT_DIR
            / "latest-verification.json"
        )

        atomic_json(
            report_path,
            {
                **result.as_dict(),
                "proxy_transport": proxy.scheme,
                "proxy_endpoint_ips": (
                    proxy_ips
                ),
                "verified_at": time.time(),
            },
        )

        # Stop packet capture immediately after leak tests.
        # Never capture the subsequent Shopify token-bearing session.
        pktmon.stop()
        pktmon = None

        with ShopifyClient(
            shopify,
            local_proxy,
        ) as client:
            identity = (
                client.shop_identity()
            )

            if (
                identity[
                    "myshopifyDomain"
                ]
                != shopify.store
            ):
                raise VerificationError(
                    "Authenticated Shopify store "
                    "does not match expected WRYDECO store."
                )

        log.info(
            "Proxy verification passed. "
            f"Observed exit IP: {result.exit_ip}; "
            f"country: {result.country_code}; "
            f"city: {result.city or 'unknown'}."
        )

        yield {
            "proxy": proxy,
            "shopify": shopify,
            "local_proxy": local_proxy,
            "proxy_ips": proxy_ips,
            "gate_pid": gate_process.pid,
            "verification": result,
            "logger": log,
        }

    finally:
        if pktmon is not None:
            try:
                pktmon.stop()
            except Exception:
                pass

        # Ask watchdog to release enforcement first.
        try:
            stop_file.touch()
        except OSError:
            pass

        if watchdog_process is not None:
            try:
                watchdog_process.wait(
                    timeout=5
                )
            except subprocess.TimeoutExpired:
                terminate_pid(
                    watchdog_process.pid
                )

        # Once watchdog is gone, WinDivert handles are closed.
        if gate_process is not None:
            terminate_pid(
                gate_process.pid
            )

        gate_log.close()
        watchdog_log.close()

        cleanup_pktmon()

        runtime_file().unlink(
            missing_ok=True
        )
        stop_file.unlink(
            missing_ok=True
        )


def run_dry_run(args) -> int:
    path = Path(args.csv).resolve()

    catalog = load_catalog(path)

    errors = validate_catalog(
        catalog,
        generate_skus=args.generate_missing_skus,
        ignore_packed_dimensions=(
            args.ignore_packed_dimensions
        ),
    )

    report = {
        "csv": str(path),
        "sha256": catalog.sha256,
        "products": len(
            catalog.products
        ),
        "variants": sum(
            len(product.variants)
            for product in catalog.products
        ),
        "images": sum(
            len(product.images)
            for product in catalog.products
        ),
        "errors": errors,
    }

    ensure_runtime_dirs()

    atomic_json(
        REPORT_DIR / "latest-dry-run.json",
        report,
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0 if not errors else 2


def run_preflight(args) -> int:
    with enforced_proxy_session(
        relax_city=args.relax_city,
    ):
        pass

    print("PREFLIGHT PASSED")
    return 0


def run_import(args) -> int:
    path = Path(args.csv).resolve()

    catalog = load_catalog(path)

    errors = validate_catalog(
        catalog,
        generate_skus=args.generate_missing_skus,
        ignore_packed_dimensions=(
            args.ignore_packed_dimensions
        ),
    )

    if errors:
        raise ConfigError(
            "CSV validation failed:\n- "
            + "\n- ".join(errors)
        )

    if args.limit:
        catalog.products = (
            catalog.products[
                : args.limit
            ]
        )

    state_path = (
        STATE_DIR / "import-progress.json"
    )

    progress = (
        read_json(
            state_path,
            {},
        )
        if args.resume
        else {}
    )

    if progress:
        if (
            progress.get("csv_sha256")
            != catalog.sha256
        ):
            raise ConfigError(
                "--resume state belongs to "
                "a different CSV file."
            )
    else:
        progress = {
            "csv_sha256": (
                catalog.sha256
            ),
            "completed_handles": [],
            "failed_handles": {},
        }

    completed = set(
        progress[
            "completed_handles"
        ]
    )

    with enforced_proxy_session(
        relax_city=args.relax_city,
    ) as session:

        with ShopifyClient(
            session["shopify"],
            session["local_proxy"],
        ) as client:

            validate_remote_sku_collisions(
                client,
                catalog,
            )

            product_defs = (
                client.metafield_definitions(
                    "PRODUCT"
                )
            )

            variant_defs = (
                client.metafield_definitions(
                    "PRODUCTVARIANT"
                )
            )

            location_id = (
                select_inventory_location(
                    client,
                    catalog,
                    args.location_id,
                )
            )

            publication_id = None

            if any(
                product.published
                is not None
                for product
                in catalog.products
            ):
                publication_id = (
                    client.online_store_publication()
                )

            category_cache = {}

            failures = {}

            for index, product in enumerate(
                catalog.products,
                start=1,
            ):
                if product.handle in completed:
                    continue

                try:
                    category_id = None

                    if product.category:
                        if (
                            product.category
                            not in category_cache
                        ):
                            category_cache[
                                product.category
                            ] = (
                                client.resolve_category(
                                    product.category
                                )
                            )

                        category_id = (
                            category_cache[
                                product.category
                            ]
                        )

                        if not category_id:
                            raise ShopifyError(
                                f"{product.handle}: "
                                "Shopify taxonomy category "
                                f"{product.category!r} "
                                "could not be resolved exactly."
                            )

                    product_input = (
                        build_product_input(
                            product,
                            category_id=(
                                category_id
                            ),
                            location_id=(
                                location_id
                            ),
                        )
                    )

                    result = client.product_set(
                        product.handle,
                        product_input,
                    )

                    product_meta = (
                        metafield_inputs(
                            product.metafields,
                            result["id"],
                            product_defs,
                        )
                    )

                    client.set_metafields(
                        product_meta
                    )

                    variants_by_sku = {
                        (
                            node.get("sku")
                            or ""
                        ).casefold(): node
                        for node
                        in result["variants"]["nodes"]
                    }

                    variant_meta = []

                    for variant in product.variants:
                        node = variants_by_sku.get(
                            variant.sku.casefold()
                        )

                        if not node:
                            raise ShopifyError(
                                f"{product.handle}: "
                                "Shopify response did not "
                                f"return variant SKU "
                                f"{variant.sku!r}."
                            )

                        variant_meta.extend(
                            metafield_inputs(
                                variant.metafields,
                                node["id"],
                                variant_defs,
                            )
                        )

                    client.set_metafields(
                        variant_meta
                    )

                    if (
                        product.published
                        is not None
                        and publication_id
                    ):
                        client.set_publication(
                            product_id=(
                                result["id"]
                            ),
                            publication_id=(
                                publication_id
                            ),
                            published=(
                                product.published
                            ),
                        )

                    completed.add(
                        product.handle
                    )

                    progress[
                        "completed_handles"
                    ] = sorted(completed)

                    progress[
                        "failed_handles"
                    ].pop(
                        product.handle,
                        None,
                    )

                    atomic_json(
                        state_path,
                        progress,
                    )

                    session["logger"].info(
                        f"[{index}/"
                        f"{len(catalog.products)}] "
                        f"Imported {product.handle}"
                    )

                    # Periodic network-location re-check.
                    if index % 10 == 0:
                        exit_ip, country, _city = (
                            public_identity(
                                session[
                                    "local_proxy"
                                ],
                                session[
                                    "proxy"
                                ].timeout_seconds,
                            )
                        )

                        if (
                            country.upper()
                            != session[
                                "proxy"
                            ].country_code.upper()
                        ):
                            raise VerificationError(
                                "Proxy exit country changed "
                                "during import."
                            )

                except Exception as exc:
                    failures[
                        product.handle
                    ] = str(exc)

                    progress[
                        "failed_handles"
                    ][
                        product.handle
                    ] = str(exc)

                    atomic_json(
                        state_path,
                        progress,
                    )

                    # Stop immediately rather than continuing
                    # after a potentially destructive product error.
                    break

            if failures:
                raise PartialImportError(
                    "Import stopped after product failure: "
                    + json.dumps(
                        failures,
                        ensure_ascii=False,
                    )
                )

    report = {
        "csv_sha256": catalog.sha256,
        "completed": sorted(
            completed
        ),
        "count": len(completed),
        "finished_at": time.time(),
    }

    atomic_json(
        REPORT_DIR / "latest-import.json",
        report,
    )

    print(
        f"IMPORT PASSED: "
        f"{len(completed)} product(s)"
    )

    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "WRYDECO Shopify CSV importer "
            "with enforced proxy egress."
        )
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    dry = sub.add_parser(
        "dry-run",
        help=(
            "Validate CSV locally. "
            "Does not enable network lockdown."
        ),
    )
    dry.add_argument(
        "--csv",
        required=True,
    )
    dry.add_argument(
        "--generate-missing-skus",
        action="store_true",
    )
    dry.add_argument(
        "--ignore-packed-dimensions",
        action="store_true",
    )

    preflight = sub.add_parser(
        "preflight",
        help=(
            "Start the gate, activate machine-wide "
            "egress lockdown and run leak checks."
        ),
    )
    preflight.add_argument(
        "--relax-city",
        action="store_true",
    )

    imp = sub.add_parser(
        "import",
        help=(
            "Validate, enforce proxy egress, verify, "
            "then import."
        ),
    )
    imp.add_argument(
        "--csv",
        required=True,
    )
    imp.add_argument(
        "--limit",
        type=int,
    )
    imp.add_argument(
        "--resume",
        action="store_true",
    )
    imp.add_argument(
        "--location-id",
    )
    imp.add_argument(
        "--generate-missing-skus",
        action="store_true",
    )
    imp.add_argument(
        "--ignore-packed-dimensions",
        action="store_true",
    )
    imp.add_argument(
        "--relax-city",
        action="store_true",
    )

    sub.add_parser(
        "restore",
        help=(
            "Emergency recovery: terminate stale "
            "gate/watchdog processes and stop pktmon."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "dry-run":
            return run_dry_run(args)

        if args.command == "preflight":
            return run_preflight(args)

        if args.command == "import":
            return run_import(args)

        if args.command == "restore":
            manual_restore()
            print("RESTORE COMPLETE")
            return 0

        parser.error(
            "Unsupported command."
        )

    except ToolError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return exc.exit_code

    except KeyboardInterrupt:
        print(
            "Interrupted. Recovery cleanup executed.",
            file=sys.stderr,
        )
        return 130

    except Exception as exc:
        print(
            f"UNEXPECTED ERROR: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())