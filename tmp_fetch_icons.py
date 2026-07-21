import asyncio
import sys
import os

# Add my-tools/iconify to path so we can import server
sys.path.append(os.path.join(os.path.dirname(__file__), 'my-tools', 'iconify'))

from server import get_icon_svg

async def main():
    icons = [
        "lucide:file-text",
        "lucide:ruler",
        "lucide:truck",
        "lucide:shield-check",
        "lucide:pen-tool"
    ]
    for icon in icons:
        try:
            svg = await get_icon_svg(icon)
            print(f"--- ICON: {icon} ---")
            print(svg)
        except Exception as e:
            print(f"Error fetching {icon}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
