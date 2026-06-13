# Plugin Guide

Step-by-step reference for adding a new integration to LushJr.
Works for any external API: Gmail, Google Calendar, Spotify, Stripe, GitHub, etc.

---

## Table of contents

1. [How the plugin system works](#1-how-the-plugin-system-works)
2. [Plugin anatomy](#2-plugin-anatomy)
3. [Step 1 — Create the folder](#3-step-1--create-the-folder)
4. [Step 2 — Write the Integration](#4-step-2--write-the-integration)
5. [Step 3 — Write the Tools](#5-step-3--write-the-tools)
6. [Step 4 — Write the Directive](#6-step-4--write-the-directive)
7. [Step 5 — Write the factory (`__init__.py`)](#7-step-5--write-the-factory-__init__py)
8. [Step 6 — Test without real credentials](#9-step-7--test-without-real-credentials)
10. [Reference: all abstract interfaces](#10-reference-all-abstract-interfaces)
11. [Common patterns and recipes](#11-common-patterns-and-recipes)
12. [Checklist](#12-checklist)

---

## 1. How the plugin system works

```
User message
    │
    ▼
MessageProcessor.process()
    │
    ├─ directive.system_prompt()  ──► injected into every AI call
    ├─ directive.tools()          ──► list of available actions
    │
    ▼
ai.choose_tools(message, tools, system_prompt)
    │
    │  returns list[ToolCall]   ← may be multiple (chained actions)
    │
    ▼
for each ToolCall:
    tool.execute(params)  ──► ToolResult(success, message, data)
    │
    ▼
ai.chat(combined_results, system_prompt)  ──► final reply to user
```

The processor knows nothing about Gmail, Notion, or any specific API.
It only speaks `Tool`, `ToolResult`, and `Directive` — the three interfaces
you implement when writing a plugin.

---

## 2. Plugin anatomy

Every integration plugin lives in its own folder under `integrations/`:

```
integrations/
└── my_plugin/
    ├── __init__.py       ← factory function (required)
    ├── integration.py    ← talks to the external API
    ├── tools.py          ← one class per action
    └── directive.py      ← bundles tools + system prompt
```

None of these files import from each other across plugins.
The only shared code is `integrations/base.py`.

---

## 3. Step 1 — Create the folder

```bash
mkdir integrations/gmail_plugin
touch integrations/gmail_plugin/__init__.py
touch integrations/gmail_plugin/integration.py
touch integrations/gmail_plugin/tools.py
touch integrations/gmail_plugin/directive.py
```

Use a descriptive name that includes the service: `gmail_plugin`, `github_plugin`,
`stripe_plugin`.  Avoid generic names like `email` or `api`.

---

## 4. Step 2 — Write the Integration

The Integration is the only layer that talks to the external API.
Everything else in your plugin goes through it.

**File:** `integrations/gmail_plugin/integration.py`

```python
"""
integrations/gmail_plugin/integration.py
─────────────────────────────────────────
Thin wrapper around the Gmail API.

All network calls live here.  Tools call methods on this class;
they never import google-api-python-client directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

# Your API client import goes here
# from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────
# Define a plain dataclass that represents one "item" from the API.
# Keep it flat and serialisable — no SDK objects, no raw dicts.

@dataclass
class Email:
    id:      str
    subject: str
    sender:  str
    body:    str
    read:    bool = False


# ── Integration class ─────────────────────────────────────────────────────────

class GmailIntegration:
    """
    Wraps the Gmail REST API.

    Parameters
    ----------
    credentials : OAuth2 credentials object (or API key, token, etc.)
    """

    def __init__(self, credentials) -> None:
        # Store your client / session / credentials here.
        # self._service = build("gmail", "v1", credentials=credentials)
        self._credentials = credentials

    # ── Public methods (called by tools) ─────────────────────────────────────
    # Name them after what they do, not after HTTP verbs.
    # One method = one API operation.

    def list_unread(self, max_results: int = 10) -> list[Email]:
        """Return the most recent unread emails."""
        # Call the API, map the response to Email dataclasses, return.
        raise NotImplementedError

    def send(self, to: str, subject: str, body: str) -> Email:
        """Send an email and return a representation of the sent message."""
        raise NotImplementedError

    def mark_read(self, email_id: str) -> None:
        """Mark a message as read."""
        raise NotImplementedError

    def delete(self, email_id: str) -> None:
        """Move a message to trash."""
        raise NotImplementedError


# ── Rules ─────────────────────────────────────────────────────────────────────
# ✅ Every public method returns a dataclass or None — never a raw SDK object.
# ✅ Catch API-specific exceptions here and re-raise as plain RuntimeError.
# ✅ Log at DEBUG level inside this file; tools handle user-facing errors.
# ❌ Never import Tool, Directive, or AIProvider here.
# ❌ Never format user-facing strings here (that's the tool's job).
```

**Key rules for the Integration layer:**

- It is the only file that imports the external SDK (e.g. `google-api-python-client`).
- Every method returns your own dataclass, never a raw SDK object or dict.
- Catch SDK-specific exceptions here and raise `RuntimeError` with a clean message.
- No formatting, no user-facing strings — just data.

---

## 5. Step 3 — Write the Tools

Each tool is one action the user can ask the bot to perform.
One class per action. Keep them small and focused.

**File:** `integrations/gmail_plugin/tools.py`

```python
"""
integrations/gmail_plugin/tools.py
────────────────────────────────────
One Tool subclass per Gmail action.

Add a new action here, then register it in directive.py.
Nothing else needs to change.
"""
from __future__ import annotations

import logging
from typing import Any

from integrations.base import Tool, ToolResult
from .integration import GmailIntegration

logger = logging.getLogger(__name__)


# ── Tool template ─────────────────────────────────────────────────────────────
#
# Copy this block for every new action.
# The three properties (name, description, params) are what the AI reads
# to decide whether and how to call this tool.

class ListUnreadEmailsTool(Tool):
    """List the most recent unread emails."""

    def __init__(self, gmail: GmailIntegration) -> None:
        self._gmail = gmail

    # ── What the AI sees ─────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        # snake_case, globally unique within the directive.
        return "list_unread_emails"

    @property
    def description(self) -> str:
        # One sentence. Be specific — this is what the AI uses to choose this tool.
        return "List the user's most recent unread emails."

    @property
    def params(self) -> dict:
        # Every param the AI may supply.
        # "required: True" means the AI MUST provide it.
        # "required: False" means the AI supplies it only when the user mentions it.
        return {
            "max_results": {
                "type":        "integer",
                "description": "Maximum number of emails to return (default 10).",
                "required":    False,
            },
        }

    # ── What actually runs ────────────────────────────────────────────────────

    def execute(self, params: dict[str, Any]) -> ToolResult:
        try:
            max_results = int(params.get("max_results", 10))
            emails = self._gmail.list_unread(max_results=max_results)

            if not emails:
                return ToolResult(success=True, message="📭 No unread emails.")

            lines = [f"📬 {len(emails)} unread email(s):"]
            for e in emails:
                lines.append(f"• **{e.subject}** — from {e.sender}")

            return ToolResult(
                success=True,
                message="\n".join(lines),
                data={"emails": [vars(e) for e in emails]},
            )
        except Exception as exc:
            logger.error("list_unread_emails failed: %s", exc)
            return ToolResult(success=False, message=f"❌ Could not fetch emails: {exc}")


class SendEmailTool(Tool):
    """Send an email."""

    def __init__(self, gmail: GmailIntegration) -> None:
        self._gmail = gmail

    @property
    def name(self) -> str:
        return "send_email"

    @property
    def description(self) -> str:
        return "Send an email to one recipient."

    @property
    def params(self) -> dict:
        return {
            "to": {
                "type":        "string",
                "description": "Recipient email address.",
                "required":    True,
            },
            "subject": {
                "type":        "string",
                "description": "Email subject line.",
                "required":    True,
            },
            "body": {
                "type":        "string",
                "description": "Plain-text email body.",
                "required":    True,
            },
        }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        to      = params.get("to")
        subject = params.get("subject")
        body    = params.get("body")

        # Validate required params defensively (the AI should always supply them,
        # but network/parsing issues can strip them).
        if not all([to, subject, body]):
            return ToolResult(success=False, message="❌ to, subject, and body are required.")

        try:
            email = self._gmail.send(to=to, subject=subject, body=body)
            return ToolResult(
                success=True,
                message=f'✅ Email "{email.subject}" sent to {email.sender}.',
                data={"email": vars(email)},
            )
        except Exception as exc:
            logger.error("send_email failed: %s", exc)
            return ToolResult(success=False, message=f"❌ Could not send email: {exc}")


# ── ToolResult contract ────────────────────────────────────────────────────────
#
# ToolResult(success, message, data)
#
#   success : bool  — True = the processor continues; False = chain stops here.
#   message : str   — Human-readable summary passed to ai.chat() for polishing.
#   data    : dict  — Raw structured data (IDs, objects) for downstream tools.
#                     Optional but useful when chaining (e.g. query → delete).
#
# Rules:
#   ✅ Always return ToolResult — never raise inside execute().
#   ✅ Write message as if you're talking to the user (emoji welcome).
#   ✅ Keep message short — ai.chat() will rewrite it into a natural reply.
#   ❌ Never call ai.chat() inside a tool — that's the processor's job.
```

**Naming conventions:**

| Pattern | Example |
|---|---|
| Tool class name | `SendEmailTool`, `ListUnreadEmailsTool` |
| `tool.name` | `send_email`, `list_unread_emails` |
| File | `tools.py` inside the plugin folder |

---

## 6. Step 4 — Write the Directive

The Directive is a simple container: it lists which tools are active and
defines the system prompt that shapes the AI's personality and language.

**File:** `integrations/gmail_plugin/directive.py`

```python
"""
integrations/gmail_plugin/directive.py
───────────────────────────────────────
Directive for the Gmail plugin.

To customise the bot's persona or language, pass a system_prompt
override to GmailDirective.__init__().
"""
from __future__ import annotations

from integrations.base import Directive, Tool
from .integration import GmailIntegration
from .tools import ListUnreadEmailsTool, SendEmailTool


# Write the system prompt in English and instruct the AI to reply in the
# user's language.  Avoid hardcoding Spanish, French, etc. — let the AI adapt.

DEFAULT_SYSTEM_PROMPT = """\
You are a personal email assistant.

Your responsibilities:
- Help the user read, send, and manage their Gmail inbox.
- Always reply in the same language the user writes in.
- Be concise and professional.

Available tools:
- list_unread_emails : Show recent unread messages.
- send_email         : Compose and send a message.

Guidelines:
- If the user asks to do something not covered by the tools, use the chat tool.
- Confirm before sending email if any required field is unclear.
- Never invent email addresses or subjects.
"""


class GmailDirective(Directive):
    """
    Bundles Gmail tools with a system prompt.

    Parameters
    ----------
    gmail         : GmailIntegration instance.
    system_prompt : Override to change persona, language rules, etc.
    extra_tools   : Additional Tool instances (e.g. MarkReadTool).
    """

    def __init__(
        self,
        gmail:         GmailIntegration,
        system_prompt: str | None   = None,
        extra_tools:   list[Tool] | None = None,
    ) -> None:
        self._tools: list[Tool] = [
            ListUnreadEmailsTool(gmail),
            SendEmailTool(gmail),
        ]
        if extra_tools:
            self._tools.extend(extra_tools)

        self._system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def tools(self) -> list[Tool]:
        return self._tools

    def system_prompt(self) -> str:
        return self._system_prompt
```

**System prompt tips:**

- List every tool by its exact `tool.name` — the AI won't hallucinate tools that aren't listed.
- Write "reply in the same language the user writes in" instead of a fixed language.
- Keep it under ~500 words; long prompts dilute the signal.
- You can inject dynamic context (current date, user name) at call time by overriding `system_prompt()` as a method that builds the string fresh each time.

---

## 7. Step 5 — Write the factory (`__init__.py`)

The factory is a single function that builds your plugin from environment variables
and returns everything `main.py` needs.

**File:** `integrations/gmail_plugin/__init__.py`

```python
"""
integrations/gmail_plugin/__init__.py
───────────────────────────────────────
Factory for the Gmail plugin.

Called by integrations.load_plugin("gmail").
Must expose a function named create_<type>_integration()
where <type> matches the key in config.yaml.
"""
import os

from .directive   import GmailDirective
from .integration import GmailIntegration


def create_gmail_integration() -> tuple[GmailIntegration, GmailDirective]:
    """
    Build and return (integration, directive).

    Raise ValueError for any missing required credential so the
    error is caught early at startup, not at the first API call.
    """
    # Read credentials from environment — never hardcode them.
    token = os.getenv("GMAIL_TOKEN")
    if not token:
        raise ValueError("GMAIL_TOKEN is not set.")

    # Build credentials object (SDK-specific)
    # credentials = build_credentials(token)

    integration = GmailIntegration(credentials=token)
    directive   = GmailDirective(integration)
    return integration, directive


__all__ = ["create_gmail_integration", "GmailIntegration", "GmailDirective"]
```

**Factory naming rule:**

The function name must match the pattern `create_<plugin_type>_integration`
where `<plugin_type>` is the key you use in `config.yaml`:

| config.yaml key | factory function name |
|---|---|
| `calendar` | `create_calendar_integration` |
| `gmail` | `create_gmail_integration` |
| `github` | `create_github_integration` |
| `ai` | `create_ai_provider` |
| `platform` | `create_platform_bot` |

---

## 8. Step 6 — Register

Load it in `main.py`:

```python
gmail, gmail_directive = load_plugin("gmail")
```

---

## 9. Step 7 — Test without real credentials

Write your tests using `unittest.mock.MagicMock`.
You do not need a live API connection to verify the plugin structure.

```python
from unittest.mock import MagicMock
from integrations.base import ToolResult
from integrations.gmail_plugin.integration import GmailIntegration, Email
from integrations.gmail_plugin.tools import ListUnreadEmailsTool, SendEmailTool
from integrations.gmail_plugin.directive import GmailDirective

# ── Tool contract ─────────────────────────────────────────────────────────────

mock_gmail = MagicMock(spec=GmailIntegration)
mock_gmail.list_unread.return_value = [
    Email(id="1", subject="Hello", sender="alice@example.com", body="Hi!")
]

tool = ListUnreadEmailsTool(mock_gmail)

# Verify schema
assert tool.name == "list_unread_emails"
assert "max_results" in tool.params
assert tool.required_params == []

# Verify execute
result = tool.execute({})
assert result.success is True
assert "Hello" in result.message

# ── Directive structure ───────────────────────────────────────────────────────

directive = GmailDirective(mock_gmail)
names = {t.name for t in directive.tools()}
assert "list_unread_emails" in names
assert "send_email"         in names
assert len(directive.system_prompt()) > 50

# ── Chained actions ───────────────────────────────────────────────────────────
# Simulate "delete all unread emails" as multiple delete calls.

from integrations.base import AIProvider, ToolCall
from core.processor import MessageProcessor

mock_ai = MagicMock(spec=AIProvider)
mock_ai.choose_tools.return_value = [
    ToolCall(tool_name="delete_email", params={"email_id": "1"}),
    ToolCall(tool_name="delete_email", params={"email_id": "2"}),
]
mock_ai.chat.return_value = "Deleted 2 emails."

# ... processor.process("delete all unread") should call delete twice
```

Run with:

```bash
python test_plugin_system.py
```

---

## 10. Reference: all abstract interfaces

### `Tool`

```
name          → str          unique snake_case action identifier
description   → str          one sentence for the AI
params        → dict         schema: {param_name: {type, description, required}}
required_params → list[str]  derived automatically
optional_params → list[str]  derived automatically
execute(params) → ToolResult run the action
```

### `ToolResult`

```
success  bool    True → chain continues; False → chain stops, message returned
message  str     human-readable summary (will be rewritten by ai.chat)
data     dict    optional structured payload (IDs, objects) for downstream tools
```

### `Directive`

```
tools()         → list[Tool]  all actions available in this context
system_prompt() → str         injected into every AI call
```

### `AIProvider`

```
chat(message, system_prompt)              → str            free-form reply
choose_tools(message, tools, system_prompt) → list[ToolCall]  may return multiple
```

### `ToolCall`

```
tool_name  str         must match Tool.name exactly
params     dict        values supplied by the AI
```

### `CalendarIntegration` (domain-specific base)

```
query_events(date_start, date_end)  → list[CalendarEvent]
create_event(title, date_start, …)  → CalendarEvent
update_event(event_id, …)           → CalendarEvent
delete_event(event_id)              → None
```

If your plugin doesn't manage calendar data, you don't need to extend this.
Define your own dataclass and integration class freely.

---

## 11. Common patterns and recipes

### Injecting dynamic context into the system prompt

When the AI needs live data (e.g. today's date, the user's name),
override `system_prompt()` as a method instead of a static string:

```python
class GmailDirective(Directive):
    def system_prompt(self) -> str:
        from datetime import datetime
        today = datetime.now().strftime("%A, %B %d %Y")
        return (
            f"Today is {today}.\n\n"
            "You are a personal email assistant. Reply in the user's language.\n"
            "Available tools: list_unread_emails, send_email."
        )
```

### Passing data between chained tool calls

Use `ToolResult.data` to carry structured payloads.
The processor collects `result.message` strings; for richer chaining,
tools can read IDs from a shared context object you inject at construction:

```python
class QueryThenDeleteDirective(Directive):
    def __init__(self, integration):
        self._ctx = {}   # shared mutable context
        self._tools = [
            QueryTool(integration, self._ctx),   # writes event IDs into ctx
            DeleteTool(integration, self._ctx),  # reads event IDs from ctx
        ]
```

### Lazy credential loading

If credentials expire and need refreshing, do it inside the Integration,
not in the factory:

```python
class GmailIntegration:
    def _get_client(self):
        if self._token_expired():
            self._refresh_token()
        return self._client
```

### Optional tools

Register a tool only when a feature flag or credential is present:

```python
class GmailDirective(Directive):
    def __init__(self, gmail, enable_send=True):
        self._tools = [ListUnreadEmailsTool(gmail)]
        if enable_send:
            self._tools.append(SendEmailTool(gmail))
```

### Adding a tool to an existing directive without modifying it

Use the `extra_tools` parameter:

```python
from integrations.calendar_notion import create_calendar_integration
from my_tools import MyCustomTool

calendar, directive = create_calendar_integration()
# Inject an extra tool at runtime
directive._tools.append(MyCustomTool())
```

---

## 12. Checklist

Before marking a plugin as done, verify each item:

**Structure**
- [ ] Folder name is `integrations/<service>_plugin/`
- [ ] Four files: `__init__.py`, `integration.py`, `tools.py`, `directive.py`
- [ ] Factory function is named `create_<type>_integration()` or `create_<type>_provider()`

**Integration layer**
- [ ] All network calls are inside `integration.py`
- [ ] Returns dataclasses, never raw SDK objects or dicts
- [ ] SDK exceptions are caught and re-raised as `RuntimeError`
- [ ] No user-facing strings formatted here

**Tools**
- [ ] One class per action
- [ ] `name` is snake_case and unique within the directive
- [ ] `description` is one clear sentence
- [ ] `params` has a `required` key for every entry
- [ ] `execute()` always returns `ToolResult`, never raises
- [ ] Required params are validated with an early `ToolResult(success=False, …)`

**Directive**
- [ ] `tools()` returns all tool instances
- [ ] `system_prompt()` lists every tool by its exact `name`
- [ ] System prompt says "reply in the user's language" (not a fixed language)
- [ ] Constructor accepts `system_prompt` and `extra_tools` overrides

**Config**
- [ ] Plugin key added to `config.yaml`
- [ ] Factory name added to `_FACTORIES` in `integrations/__init__.py`
- [ ] Required env vars documented (in `.env.example` or README)

**Tests**
- [ ] Tool `name`, `description`, `params` verified
- [ ] `execute()` tested with a `MagicMock` integration
- [ ] `ToolResult.success` and `ToolResult.message` asserted
- [ ] Directive `tools()` and `system_prompt()` structure verified
- [ ] At least one chained-action scenario mocked and asserted
- [ ] All tests pass without real API credentials