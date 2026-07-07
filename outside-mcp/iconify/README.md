# Iconify MCP Server - AI Agent Instruction Manual

<system_prompt>
You are an AI Agent equipped with the **Iconify MCP Server**.
This server gives you tools to search for, fetch, and format icons from the Iconify ecosystem (over 200,000 open-source vector icons).
When a user asks you to add an icon, find an icon, or generate an HTML/UI with icons, you MUST use the tools provided by this server.
</system_prompt>

## 🛠 Available Tools

The MCP Server exposes the following tools. Read their descriptions carefully:

1. `search_icons(query, limit=64, prefix=None, ...)`
   - **Purpose**: Search for icons by keyword.
   - **Agent Logic**: Always use this FIRST when you don't know the exact `prefix:name` of an icon.
   - **Example**: User asks for a "settings" icon. You call `search_icons(query="settings")`.

2. `get_icon_svg(icon, color=None, width=None, height=None, ...)`
   - **Purpose**: Get the raw `<svg>...</svg>` HTML code for a specific icon.
   - **Agent Logic**: Use this when you need to embed the icon directly inside HTML/React/Vue components.
   - **Important**: The `icon` parameter MUST be in the `prefix:name` format (e.g. `lucide:settings`, `mdi:home`). DO NOT pass just `settings`.

3. `get_icon_svg_url(icon, color=None, width=None, height=None, ...)`
   - **Purpose**: Get a direct URL (e.g., `https://api.iconify.design/mdi/home.svg`) for the icon.
   - **Agent Logic**: Use this when you need an `<img>` tag `src` attribute or CSS `background-image: url(...)`.

4. `get_icons_css(prefix, icons)`
   - **Purpose**: Generates CSS for using icons as CSS masks/backgrounds.
   - **Agent Logic**: Only pass the `prefix` in the `prefix` argument, and pass the icon names *without the prefix* in the `icons` array (e.g., `prefix="mdi"`, `icons=["home", "account"]`).

5. `list_icon_collections()` and `list_collection_icons(prefix)`
   - **Purpose**: Browse available icon sets.

6. `get_icon_data(icons)`
   - **Purpose**: Fetch raw Iconify JSON data for complex rendering or caching.

## 🧠 Reasoning Steps for Agents

When requested to use an icon:
**Step 1:** Do you know the exact icon name (like `tabler:user`)?
- Yes -> Go to Step 2.
- No -> Call `search_icons(query="keyword")` and pick an icon from the results. Remember its full name (e.g., `mdi:cart`).

**Step 2:** Decide how the icon will be used:
- If building an HTML page and the user wants inline SVGs: Call `get_icon_svg(icon="mdi:cart")`.
- If building an HTML page and using `<img src="...">`: Call `get_icon_svg_url(icon="mdi:cart")` and insert the returned URL.

## ⚙️ Setup for Users (Installation)

To configure this server in Claude Desktop, Cursor, or any MCP client, add the following to the MCP settings file:

```json
{
  "mcpServers": {
    "iconify": {
      "command": "python",
      "args": ["/absolute/path/to/iconify-mcp/server.py"]
    }
  }
}
```
*Note: replace `/absolute/path/to/iconify-mcp` with the actual folder path.*

**Prerequisites:** 
- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`
