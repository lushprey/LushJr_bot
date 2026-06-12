# LushJr Bot — Arquitectura Modular

Bot de Telegram con IA + Calendario Notion, diseñado para ser **fácilmente intercambiable** en cada capa.

## Estructura

```
LushJr_bot/
├── main.py                          ← Composition Root (ensambla todo)
│
├── core/                            ← Lógica de negocio (sin dependencias externas)
│   ├── ai_provider.py               ← Interfaz abstracta de IA
│   ├── data_integration.py          ← Interfaz abstracta de datos
│   └── processor.py                 ← Pipeline central (orquestador)
│
├── integrations/                    ← Implementaciones concretas
│   ├── nvidia_ai.py                 ← IA: Nvidia NIM (compatible OpenAI)
│   ├── notion_calendar.py           ← Calendario: Notion
│   ├── notion_actions.py            ← Acciones atómicas de Notion
│   ├── notion_actions_registry.py   ← Decorador @action y registro
│   ├── notion_executor.py           ← Ejecutor genérico de acciones
│   └── notion_introspection.py      ← Descubrimiento de schemas
│
└── platforms/
    └── telegram_bot.py              ← Plataforma: Telegram
```

## Flujo de un mensaje

```
Usuario → Telegram → TelegramBot
                         ↓
                    MessageProcessor
                    ┌────┴────┐
                 AIProvider  CalendarIntegration
                 (Nvidia)    (Notion)
```

## Cómo cambiar una pieza

### Cambiar proveedor de IA (Nvidia → Anthropic)
```python
# integrations/anthropic_ai.py
class AnthropicAIProvider(AIProvider):
    def detect_intent(self, message, context): ...
    def chat(self, message, system_prompt): ...

# main.py — solo cambias esta línea:
ai = AnthropicAIProvider(api_key=env["ANTHROPIC_API_KEY"])
```

### Cambiar integración de datos (Notion → Google Calendar)
```python
# integrations/google_calendar.py
class GoogleCalendarIntegration(CalendarIntegration):
    def query_events(self, date_start, date_end): ...
    def create_event(self, title, date_start, date_end=None): ...

# main.py — solo cambias esta línea:
calendar = GoogleCalendarIntegration(credentials=env["GOOGLE_CREDS"])
```

### Cambiar plataforma (Telegram → Discord)
```python
# platforms/discord_bot.py
class DiscordBot:
    def __init__(self, token: str, processor: MessageProcessor): ...
    def run(self): ...

# main.py — solo cambias esta línea:
bot = DiscordBot(token=env["DISCORD_TOKEN"], processor=processor)
```

## Variables de entorno

```env
TELEGRAM_TOKEN=...
NVIDIA_API_KEY=...
NOTION_TOKEN=...
DATABASE_ID=...
```

## Comandos

```bash
pip install python-telegram-bot openai notion-client python-dotenv
python main.py
```
