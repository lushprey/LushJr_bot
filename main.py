"""
main.py
────────
Punto de entrada y raíz de composición (Composition Root).

Usa el sistema de plugins para cargar integraciones:
  - Proveedor de IA        → load_plugin('ai')         (intercambiable)
  - Integración de datos   → load_plugin('calendar')   (intercambiable)
  - Plataforma             → load_plugin('platform')   (intercambiable)
  - Procesador central     → MessageProcessor          (lógica de negocio)

Para cambiar alguna pieza, modifica integrations/__init__.py DEFAULT_PLUGINS
o usa config.yaml (si se implementa).
"""

import logging
import os

from dotenv import load_dotenv

from core.processor import MessageProcessor
from integrations import load_plugin

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


# ─── Composition Root (usando plugins) ─────────────────────────────────────────

def build_bot() -> "TelegramBot":
    """
    Ensambla todas las dependencias usando el sistema de plugins.
    
    Flow:
    1. Load AI provider plugin
    2. Load calendar integration + directive plugin
    3. Create processor with AI + directive
    4. Create platform bot with processor
    5. Return bot ready to run
    """
    logger.info("🔌 Loading plugins...")
    
    # Load AI provider
    logger.info("  - Loading AI provider...")
    ai = load_plugin('ai')
    
    # Load calendar integration + directive
    logger.info("  - Loading calendar integration...")
    calendar_integration, calendar_directive = load_plugin('calendar')
    
    # Add chat tool to directive now that we have the AI provider
    from integrations.calendar_notion.tools import ChatTool
    if not any(tool.name == "chat" for tool in calendar_directive.get_tools()):
        calendar_directive._tools.append(ChatTool(ai))
    
    # Create processor (wires AI + directive together)
    logger.info("  - Creating message processor...")
    processor = MessageProcessor(ai=ai, directive=calendar_directive)
    
    # Load platform bot factory
    logger.info("  - Loading platform bot...")
    platform_factory = load_plugin('platform')
    
    # Instantiate bot with processor
    if callable(platform_factory):
        # If factory returns a lambda, call it with processor
        bot = platform_factory(processor)
    else:
        # If factory returns bot directly, use it as is
        bot = platform_factory
    
    logger.info("✅ All plugins loaded successfully")
    return bot


# ─── Entrada ──────────────────────────────────────────────────────────────────

def main() -> None:
    _load_env()  # Validate env vars exist
    bot = build_bot()
    bot.run()


if __name__ == "__main__":
    main()
