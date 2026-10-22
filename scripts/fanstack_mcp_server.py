import asyncio
import re
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

server = Server("fanstack-mcp")

PERSONA_FILE = "/home/james/sovereign_inbox/daily_05112026/sovereign_personas_export.md"
MLB_API_URL = "http://127.0.0.1:8000/api/mlb/boxscore/{}"

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_persona",
            description="Get the full personality matrix, system prompt, lore, and rules for a given persona (e.g., 'barf').",
            inputSchema={
                "type": "object",
                "properties": {
                    "persona_id": {
                        "type": "string",
                        "description": "The ID of the persona to look up, e.g., 'barf'."
                    }
                },
                "required": ["persona_id"]
            }
        ),
        Tool(
            name="get_mlb_live_stats",
            description="Get the current live box score for the active MLB game from FanStack.",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_pk": {
                        "type": "string",
                        "description": "The MLB Game PK (e.g., '823562')."
                    }
                },
                "required": ["game_pk"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_persona":
        persona_id = arguments.get("persona_id", "").lower()
        if not persona_id:
            return [TextContent(type="text", text="Error: persona_id is required.")]
        
        try:
            with open(PERSONA_FILE, "r") as f:
                content = f.read()
            
            # Simple markdown extraction: find "## persona_id" and read until the next "---" or EOF
            pattern = rf"(?i)(##\s+{persona_id}\b.*?)(?=\n---\n|\Z)"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                persona_data = match.group(1).strip()
                return [TextContent(type="text", text=persona_data)]
            else:
                return [TextContent(type="text", text=f"Error: Persona '{persona_id}' not found in the export file.")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading persona file: {str(e)}")]

    if name == "get_mlb_live_stats":
        game_pk = arguments.get("game_pk")
        if not game_pk:
            return [TextContent(type="text", text="Error: game_pk is required.")]
        
        try:
            resp = requests.get(MLB_API_URL.format(game_pk), timeout=10)
            if resp.ok:
                # Return the JSON text
                return [TextContent(type="text", text=resp.text)]
            else:
                return [TextContent(type="text", text=f"Error: API returned {resp.status_code} - {resp.text}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching live stats: {str(e)}")]

    return [TextContent(type="text", text=f"Error: Unknown tool {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
