from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from mcp.server.fastmcp import FastMCP


ICONIFY_API_BASE = os.getenv("ICONIFY_API_BASE", "https://api.iconify.design").rstrip("/")

mcp = FastMCP("Iconify MCP")


def parse_icon_name(icon: str) -> tuple[str, str]:
    """
    Parse icon name in Iconify format: "prefix:name".

    Examples:
        mdi:home
        lucide:search
        tabler:brand-github
    """
    icon = icon.strip()

    if ":" not in icon:
        raise ValueError(
            "Invalid icon name. Expected format: 'prefix:name', for example 'mdi:home'."
        )

    prefix, name = icon.split(":", 1)

    if not prefix or not name:
        raise ValueError(
            "Invalid icon name. Expected format: 'prefix:name', for example 'mdi:home'."
        )

    return prefix, name


async def iconify_get_json(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """Call Iconify API and return JSON."""
    url = f"{ICONIFY_API_BASE}{path}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def iconify_get_text(path: str, params: Optional[dict[str, Any]] = None) -> str:
    """Call Iconify API and return raw text."""
    url = f"{ICONIFY_API_BASE}{path}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.text


@mcp.tool()
async def search_icons(
    query: str,
    limit: int = 64,
    start: int = 0,
    prefix: Optional[str] = None,
    prefixes: Optional[str] = None,
    category: Optional[str] = None,
) -> dict[str, Any]:
    """
    Search Iconify icons by keyword.

    Args:
        query: Search keyword, for example "home", "cart", "github".
        limit: Number of results. Iconify supports 32-999.
        start: Start index for pagination.
        prefix: Limit result to one icon set, for example "mdi", "lucide", "tabler".
        prefixes: Comma-separated icon set prefixes, for example "mdi,lucide,tabler".
        category: Optional Iconify category filter.

    Returns:
        Iconify search response with icons, total, limit, start, collections.
    """
    if not query.strip():
        raise ValueError("query is required.")

    normalized_limit = max(32, min(limit, 999))

    params: dict[str, Any] = {
        "query": query,
        "limit": normalized_limit,
        "start": max(0, start),
    }

    if prefix:
        params["prefix"] = prefix

    if prefixes:
        params["prefixes"] = prefixes

    if category:
        params["category"] = category

    return await iconify_get_json("/search", params)


@mcp.tool()
async def get_icon_svg(
    icon: str,
    color: Optional[str] = None,
    width: Optional[str] = None,
    height: Optional[str] = None,
    rotate: Optional[str] = None,
    flip: Optional[str] = None,
    box: bool = False,
) -> str:
    """
    Get SVG markup for an Iconify icon.

    Args:
        icon: Icon name in format "prefix:name", for example "mdi:home".
        color: Optional color, for example "#111827" or "red".
        width: Optional SVG width, for example "24", "24px", "1em".
        height: Optional SVG height, for example "24", "24px", "1em".
        rotate: Optional rotation, for example "90deg", "180deg", "270deg".
        flip: Optional flip: "horizontal", "vertical", or "horizontal,vertical".
        box: If true, adds empty rectangle matching viewBox.

    Returns:
        SVG string.
    """
    prefix, name = parse_icon_name(icon)

    params: dict[str, Any] = {}

    if color:
        params["color"] = color

    if width:
        params["width"] = width

    if height:
        params["height"] = height

    if rotate:
        params["rotate"] = rotate

    if flip:
        params["flip"] = flip

    if box:
        params["box"] = "1"

    return await iconify_get_text(f"/{prefix}/{name}.svg", params)


@mcp.tool()
async def get_icon_svg_url(
    icon: str,
    color: Optional[str] = None,
    width: Optional[str] = None,
    height: Optional[str] = None,
    rotate: Optional[str] = None,
    flip: Optional[str] = None,
    box: bool = False,
) -> str:
    """
    Build direct Iconify SVG URL for use in HTML, CSS, markdown, or downloads.

    Args:
        icon: Icon name in format "prefix:name", for example "mdi:home".
        color: Optional color, for example "#111827".
        width: Optional width.
        height: Optional height.
        rotate: Optional rotation.
        flip: Optional flip.
        box: Whether to add box=1.

    Returns:
        Direct SVG URL.
    """
    prefix, name = parse_icon_name(icon)

    params: dict[str, Any] = {}

    if color:
        params["color"] = color

    if width:
        params["width"] = width

    if height:
        params["height"] = height

    if rotate:
        params["rotate"] = rotate

    if flip:
        params["flip"] = flip

    if box:
        params["box"] = "1"

    query = f"?{urlencode(params)}" if params else ""
    return f"{ICONIFY_API_BASE}/{prefix}/{name}.svg{query}"


@mcp.tool()
async def get_icon_data(icons: list[str]) -> dict[str, Any]:
    """
    Get raw Iconify JSON data for one or more icons.

    Args:
        icons: List of icon names in format "prefix:name".
               Example: ["mdi:home", "mdi:account", "lucide:search"]

    Returns:
        A dict grouped by prefix. Each value is the Iconify JSON response.
    """
    if not icons:
        raise ValueError("icons must not be empty.")

    grouped: dict[str, list[str]] = {}

    for icon in icons:
        prefix, name = parse_icon_name(icon)
        grouped.setdefault(prefix, []).append(name)

    result: dict[str, Any] = {}

    for prefix, names in grouped.items():
        unique_names = sorted(set(names))
        result[prefix] = await iconify_get_json(
            f"/{prefix}.json",
            {"icons": ",".join(unique_names)},
        )

    return result


@mcp.tool()
async def list_icon_collections() -> dict[str, Any]:
    """
    List available Iconify icon collections/icon sets.

    Returns:
        Dict of Iconify collections keyed by prefix.
    """
    return await iconify_get_json("/collections")


@mcp.tool()
async def list_collection_icons(prefix: str) -> dict[str, Any]:
    """
    List icons inside one Iconify collection.

    Args:
        prefix: Icon set prefix, for example "mdi", "lucide", "tabler".

    Returns:
        Iconify collection response with icon names and metadata.
    """
    if not prefix.strip():
        raise ValueError("prefix is required.")

    return await iconify_get_json("/collection", {"prefix": prefix.strip()})


@mcp.tool()
async def get_icons_css(
    prefix: str,
    icons: list[str],
    icon_selector: str = ".icon--{prefix}--{name}",
) -> str:
    """
    Get generated CSS for icons from one collection.

    Args:
        prefix: Icon set prefix, for example "mdi".
        icons: Icon names without prefix, for example ["home", "account"].
        icon_selector: Optional selector template supported by Iconify API.

    Returns:
        CSS string.
    """
    if not prefix.strip():
        raise ValueError("prefix is required.")

    if not icons:
        raise ValueError("icons must not be empty.")

    clean_icons = [name.strip() for name in icons if name.strip()]

    if not clean_icons:
        raise ValueError("icons must contain at least one valid icon name.")

    return await iconify_get_text(
        f"/{prefix}.css",
        {
            "icons": ",".join(sorted(set(clean_icons))),
            "icon-selector": icon_selector,
        },
    )


@mcp.resource("iconify://svg/{prefix}/{name}")
async def icon_svg_resource(prefix: str, name: str) -> str:
    """
    MCP resource for reading an Iconify icon as SVG.

    Example resource URI:
        iconify://svg/mdi/home
    """
    return await iconify_get_text(f"/{prefix}/{name}.svg")


if __name__ == "__main__":
    mcp.run(transport="stdio")
