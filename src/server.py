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
from mcp.types import Resource

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
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str | bytes:
    if uri == "tamper://menu":
        return get_menu_data()
    raise ValueError(f"Unknown resource URI: {uri}")

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
