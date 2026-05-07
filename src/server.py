import json
import os
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Resource, Tool, TextContent, CallToolResult

# 1. Initialize MCP Server
server = Server("tamper-mcp")

# 2. Load the menu data
DATA_DIR = Path(__file__).parent.parent / "data"
MENU_FILE = DATA_DIR / "menu.json"

def get_menu_data() -> str:
    if not MENU_FILE.exists():
        return json.dumps({"error": "Menu data not found"})
    with open(MENU_FILE, "r", encoding="utf-8") as f:
        return f.read()

# 3. Define Resources
@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    return [
        Resource(
            uri="tamper://menu",
            name="Tamper! Menu",
            description="The complete food and drink menu for Tamper! coffeeshop in Lille.",
            mimeType="application/json",
        ),
        Resource(
            uri="ui://widget/tamper.html",
            name="Tamper UI Widget",
            mimeType="text/html;profile=mcp-app",
            **{
                "_meta": {
                    "ui": {
                        "domain": "https://tamper-mcp.onrender.com",
                        "csp": {
                            "connectDomains": [],
                            "resourceDomains": ["https://fonts.googleapis.com", "https://fonts.gstatic.com"],
                            "frameDomains": ["https://www.google.com"]
                        }
                    }
                }
            }
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str | bytes:
    if uri == "tamper://menu":
        return get_menu_data()
    if uri == "ui://widget/tamper.html":
        widget_path = Path(__file__).parent / "web" / "tamper.html"
        return widget_path.read_text(encoding="utf-8")
    raise ValueError(f"Unknown resource URI: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="show_menu",
            description="Displays the menu of the Tamper! coffeeshop. Use this when the user asks for the menu, prices, or food options.",
            inputSchema={
                "type": "object", 
                "properties": {},
                "additionalProperties": False
            },
            annotations={
                "readOnlyHint": True,
                "openWorldHint": False,
                "destructiveHint": False
            },
            **{
                "_meta": {
                    "ui": {
                        "resourceUri": "ui://widget/tamper.html"
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent] | CallToolResult:
    if name == "show_menu":
        menu_json = json.loads(get_menu_data())
        return CallToolResult(
            structuredContent=menu_json,
            content=[
                TextContent(type="text", text="Voici le menu de Tamper! (Lille).")
            ],
            **{
                "_meta": {
                    "ui": {
                        "resourceUri": "ui://widget/tamper.html"
                    }
                }
            }
        )
    raise ValueError(f"Unknown tool: {name}")

# 4. SSE Transport and Starlette
sse = SseServerTransport("/message")

async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await server.run(
            streams[0], streams[1], server.create_initialization_options()
        )
    return Response()

app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/message", app=sse.handle_post_message),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
)
