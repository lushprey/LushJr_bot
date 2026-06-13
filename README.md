# LushJr Bot

A modular, language-agnostic Telegram bot with AI and calendar management.

The project uses a plugin architecture that allows components to be replaced independently (AI provider, calendar backend, messaging platform) without modifying the core logic.

---

## Project structure

```
LushJr_bot/
├── main.py                          # Composition root (wires everything together)
├── requirements.txt
│
├── core/
│   └── processor.py                 # MessageProcessor — orchestrates AI + tools
│
├── integrations/
│   ├── base.py                      # Abstract interfaces (Tool, Directive, AIProvider …)
│   │
│   ├── core_ai/                     # Plugin: Nvidia/OpenAI-compatible AI
│   │   ├── __init__.py              #   factory → create_ai_provider()
│   │   └── provider.py              #   NvidiaAIProvider
│   │
│   ├── calendar_notion/             # Plugin: Notion calendar
│   │   ├── __init__.py              #   factory → create_calendar_integration()
│   │   ├── integration.py           #   NotionCalendarIntegration
│   │   ├── directive.py             #   CalendarDirective (tools + system prompt)
│   │   └── tools.py                 #   QueryEventsTool, CreateEventTool, …
│   │
│   └── platform_telegram/           # Plugin: Telegram bot
│       ├── __init__.py              #   factory → create_platform_bot()
│       └── bot.py                   #   TelegramBot
│
├── agents/                          # Development utilities
│
└── test_plugin_system.py            # Test suite (no API keys required)
```

---

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env with your credentials
cp .env.example .env

# Run the bot
python main.py
```

---

## Environment variables

```
TELEGRAM_TOKEN   — Telegram bot token from @BotFather
NVIDIA_API_KEY   — NVIDIA API key
NOTION_TOKEN     — Notion integration token
DATABASE_ID      — Notion database ID
```

---

## Plugin architecture

LushJr separates its responsibilities into independent modules:

- **Core** → orchestration logic.
- **AI provider** → language model integration.
- **Calendar integration** → event management backend.
- **Platform integration** → communication channel.

The core never depends directly on a specific implementation.

---

## Adding a new tool

1. Create a class extending `Tool`.
2. Implement the required metadata and `execute()` method.
3. Register the tool inside the corresponding directive.

Example:

```python
class MyNewTool(Tool):
    name = "my_tool"
    description = "Does something useful."
    params = {
        "input": {
            "type": "string",
            "description": "The input",
            "required": True,
        }
    }

    def execute(self, params):
        result = do_something(params["input"])

        return ToolResult(
            success=True,
            message=result,
        )
```

---

## Adding a new plugin

To add a new integration:

1. Create a new folder inside `integrations/`.
2. Implement the required abstract interfaces from `integrations/base.py`.
3. Expose a factory function in `__init__.py`.
4. Register the plugin in the application bootstrap process.

Examples:

- Google Calendar
- Discord
- WhatsApp
- OpenAI
- Anthropic

---

## Chained actions

The AI can execute multiple tools during a single interaction.

Example:

```
"Delete all events this month."
```

may generate several consecutive tool calls automatically.

Flow:

```
User message
    ↓
AI.choose_tools()
    ↓
[ToolCall, ToolCall, ToolCall]
    ↓
Execute tools sequentially
    ↓
AI.chat(results)
    ↓
Natural-language response
```

---

## Running tests

```bash
python test_plugin_system.py
```

The tests run without external API keys by using mocks.

---

## Dependencies

```
python-telegram-bot==21.3
openai==1.42.0
httpx==0.27.2
notion-client==2.2.1
python-dotenv==1.0.0
```