"""
main.py
────────
Punto de entrada y raíz de composición (Composition Root).

Aquí se ensamblan las piezas:
  - Proveedor de IA        → NvidiaAIProvider  (intercambiable)
  - Integración de datos   → NotionCalendar    (intercambiable)
  - Procesador central     → MessageProcessor  (lógica de negocio)
  - Plataforma             → TelegramBot       (intercambiable)

Para cambiar alguna pieza, solo modifica las líneas de construcción aquí.
"""

import logging
import os

from dotenv import load_dotenv

from core.processor import MessageProcessor
from integrations.nvidia_ai import NvidiaAIProvider
from integrations.notion_calendar import NotionCalendarIntegration
from platforms.telegram_bot import TelegramBot

# ─── Setup ────────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(
    format="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Validación de entorno ────────────────────────────────────────────────────

REQUIRED_ENV_VARS = ["TELEGRAM_TOKEN", "NVIDIA_API_KEY", "NOTION_TOKEN", "DATABASE_ID"]


def _load_env() -> dict:
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Faltan variables de entorno: {', '.join(missing)}")
    return {v: os.getenv(v) for v in REQUIRED_ENV_VARS}


# ─── Composition Root ─────────────────────────────────────────────────────────

def build_bot(env: dict) -> TelegramBot:
    """
    Ensambla todas las dependencias.
    Cambia aquí para usar otro proveedor de IA o integración.
    """
    # Proveedor de IA (intercambiable: NvidiaAIProvider, OpenAIProvider, AnthropicProvider...)
    ai = NvidiaAIProvider(api_key=env["NVIDIA_API_KEY"])

    # Integración de datos (intercambiable: NotionCalendar, GoogleCalendar...)
    calendar = NotionCalendarIntegration(
        token=env["NOTION_TOKEN"],
        database_id=env["DATABASE_ID"],
        prop_titulo="Nombre",
        prop_fecha="Fecha",
    )

    # Procesador central (agnóstico de plataforma e integración)
    processor = MessageProcessor(ai=ai, calendar=calendar)

    # Plataforma (intercambiable: TelegramBot, DiscordBot, WhatsAppBot...)
    return TelegramBot(token=env["TELEGRAM_TOKEN"], processor=processor)


# ─── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    env = _load_env()
    bot = build_bot(env)
    bot.run()


if __name__ == "__main__":
    main()
