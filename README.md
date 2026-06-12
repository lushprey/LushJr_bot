# LushJr_bot

_Auto-generated README - Last updated: 2026-06-12 10:44:33_

## Overview

Telegram bot with AI integration and calendar management.

## Project Structure

```
LushJr_bot/
├── config.yaml
├── core/
│   ├── __init__.py
│   └── processor.py
├── integrations/
│   ├── __init__.py
│   ├── base.py
│   ├── calendar_notion/
│   │   ├── __init__.py
│   │   ├── directive.py
│   │   ├── integration.py
│   │   └── tools.py
│   ├── core_ai/
│   │   ├── __init__.py
│   │   └── provider.py
│   └── platform_telegram/
│       ├── __init__.py
│       └── bot.py
├── main.py
├── README.md
├── readme_agent.py
├── requirements.txt
└── test_plugin_system.py
```

## Components

### Core

- **__init__.py**

- **processor.py**


### Integrations

- **__init__.py**

- **base.py**


### Integrations\Calendar_Notion

- **__init__.py**

- **directive.py**

- **integration.py**

- **tools.py**


### Integrations\Core_Ai

- **__init__.py**

- **provider.py**


### Integrations\Platform_Telegram

- **__init__.py**

- **bot.py**


### Root

- **main.py**
 — main.py

- **readme_agent.py**
 — readme_agent.py

- **test_plugin_system.py**
 — test_plugin_system.py


## Dependencies

```
python-telegram-bot==21.3
openai==1.42.0
httpx==0.27.2
notion-client==2.2.1
python-dotenv==1.0.0
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Configuration

Set up the following environment variables in a `.env` file:

- `TELEGRAM_TOKEN`
- `NVIDIA_API_KEY`
- `NOTION_TOKEN`
- `DATABASE_ID`
