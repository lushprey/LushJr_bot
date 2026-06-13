# Plugin Guide

This document explains how to extend LushJr through its plugin system.

---

# Overview

LushJr follows a modular architecture.

Each plugin is responsible for a single concern:

- AI providers
- Calendar integrations
- Messaging platforms
- Additional tool collections

Plugins communicate with the core only through abstract interfaces.

---

# Plugin structure

Example:

```
integrations/
└── my_plugin/
    ├── __init__.py
    ├── integration.py
    ├── directive.py
    └── tools.py
```

---

# Creating a Tool

All tools must inherit from `Tool`.

Example:

```python
class ExampleTool(Tool):
    name = "example_tool"

    description = "Example tool."

    params = {
        "text": {
            "type": "string",
            "description": "Input text.",
            "required": True,
        }
    }

    def execute(self, params):
        return ToolResult(
            success=True,
            message=params["text"],
        )
```

---

# Registering tools

Tools are exposed through directives.

Example:

```python
class ExampleDirective(Directive):

    def __init__(self):
        self.tools = [
            ExampleTool(),
        ]
```

---

# Creating an AI provider

AI providers must implement the `AIProvider` interface.

Responsibilities:

- Generate responses.
- Decide which tools should be executed.
- Return structured tool calls.

Example providers:

- NVIDIA
- OpenAI
- Anthropic

---

# Creating a calendar integration

Calendar integrations manage event persistence.

Examples:

- Notion
- Google Calendar
- iCal

Typical responsibilities:

- Create events.
- Query events.
- Delete events.
- Update events.

---

# Creating a messaging platform

Messaging platforms deliver messages to users.

Examples:

- Telegram
- Discord
- WhatsApp

Responsibilities:

- Receive messages.
- Pass messages to the processor.
- Send responses back.

---

# Plugin design principles

Plugins should:

- Remain independent.
- Avoid direct dependencies on other plugins.
- Use abstract interfaces.
- Handle their own configuration requirements.
- Keep business logic outside the core.

---

# Testing plugins

Each plugin should be testable in isolation.

Recommendations:

- Mock external APIs.
- Avoid network calls during tests.
- Validate tool outputs.
- Verify error handling.

---

# Best practices

✓ Single responsibility.

✓ Explicit interfaces.

✓ Defensive error handling.

✓ Comprehensive logging.

✓ Independent testing.

---

# Philosophy

The goal of LushJr is to keep the core stable while allowing integrations to evolve independently.

Adding new capabilities should require extending the system, not modifying its foundation.