import express from "express";
import cors from "cors";
import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { registerAppResource, registerAppTool, RESOURCE_MIME_TYPE } from "@modelcontextprotocol/ext-apps/server";
import { z } from "zod";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 2. Load the menu data
const DATA_DIR = join(__dirname, "..", "data");
const MENU_FILE = join(DATA_DIR, "menu.json");

function getMenuData(): string {
  if (!existsSync(MENU_FILE)) {
    return JSON.stringify({ error: "Menu data not found" });
  }
  return readFileSync(MENU_FILE, "utf-8");
}

function getMenuJson() {
  return JSON.parse(getMenuData());
}

// Read UI Widget HTML
const widgetPath = join(__dirname, "web", "tamper.html");
const widgetHtml = existsSync(widgetPath) ? readFileSync(widgetPath, "utf-8") : "<h1>Widget not found</h1>";

// 5. Express Server Setup
const app = express();
app.use(cors());

const transports = new Map<string, SSEServerTransport>();

app.get("/sse", async (req, res) => {
  // 1. Initialize MCP Server per connection
  const server = new McpServer({
    name: "tamper-mcp",
    version: "1.0.0"
  });

  // 3. Define Resources
  server.resource(
    "Tamper! Menu",
    "tamper://menu",
    { description: "The complete food and drink menu for Tamper! coffeeshop in Lille." },
    async (uri) => ({
      contents: [
        {
          uri: uri.href,
          text: getMenuData(),
          mimeType: "application/json"
        }
      ]
    })
  );

  // Register the UI Widget Resource using ext-apps SDK
  registerAppResource(
    server,
    "Tamper UI Widget",
    "ui://widget/tamper.html",
    {},
    async () => ({
      contents: [
        {
          uri: "ui://widget/tamper.html",
          mimeType: RESOURCE_MIME_TYPE,
          text: widgetHtml,
          _meta: {
            ui: {
              domain: "https://tamper-mcp.onrender.com",
              csp: {
                connectDomains: [],
                resourceDomains: ["https://fonts.googleapis.com", "https://fonts.gstatic.com"],
                frameDomains: ["https://www.google.com"]
              }
            }
          }
        }
      ]
    })
  );

  // 4. Define Tools using ext-apps SDK
  registerAppTool(
    server,
    "show_menu",
    {
      title: "show_menu",
      description: "Displays the menu of the Tamper! coffeeshop. Use this when the user asks for the menu, prices, or food options.",
      inputSchema: z.object({}),
      _meta: {
        ui: {
          resourceUri: "ui://widget/tamper.html"
        }
      }
    },
    async () => {
      return {
        structuredContent: getMenuJson(),
        content: [
          { type: "text", text: "Voici le menu de Tamper! (Lille)." }
        ],
        _meta: {}
      };
    }
  );

  const transport = new SSEServerTransport("/message", res);
  await server.connect(transport);
  
  if (transport.sessionId) {
    transports.set(transport.sessionId, transport);
    res.on("close", async () => {
      transports.delete(transport.sessionId!);
      await server.close();
    });
  }
});

app.post("/message", async (req, res) => {
  const sessionId = req.query.sessionId as string;
  const transport = sessionId ? transports.get(sessionId) : undefined;
  if (!transport) {
    res.sendStatus(400);
    return;
  }
  await transport.handlePostMessage(req, res);
});

const PORT = process.env.PORT || 8000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
