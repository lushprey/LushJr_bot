"""
platforms/telegram_bot.py
──────────────────────────
Capa de Telegram. Solo maneja I/O con la API de Telegram.
No contiene lógica de negocio — delega todo al MessageProcessor.

Para agregar Discord, WhatsApp, etc.: crea discord_bot.py o whatsapp_bot.py
que usen el mismo MessageProcessor.
"""
import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from core.processor import MessageProcessor

logger = logging.getLogger(__name__)


class TelegramBot:
    """Bot de Telegram. Solo sabe de Telegram y MessageProcessor."""

    def __init__(self, token: str, processor: MessageProcessor):
        self.token = token
        self.processor = processor
        self._app = self._build_app()

    def run(self) -> None:
        logger.info("🤖 Bot iniciado — modo lenguaje natural")
        self._app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            bootstrap_retries=5,
        )

    # ── Construcción de la app ───────────────────────────────────────────────

    def _build_app(self) -> Application:
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30,
            read_timeout=90,
            write_timeout=30,
            pool_timeout=30,
        )
        app = (
            Application.builder()
            .token(self.token)
            .request(request)
            .build()
        )
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        return app

    # ── Handler ──────────────────────────────────────────────────────────────

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text
        user = update.effective_user.first_name if update.effective_user else "?"
        logger.info(f"[{user}] {text!r}")

        try:
            await update.message.chat.send_action("typing")
        except Exception as e:
            logger.warning(f"No se pudo enviar 'typing': {e}")

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(None, self.processor.process, text)
        except Exception as e:
            logger.exception("Error inesperado procesando mensaje")
            response = f"❌ Algo salió mal: {e}"

        # Telegram: máx 4096 chars por mensaje
        for chunk in range(0, len(response), 4096):
            await update.message.reply_text(
                response[chunk : chunk + 4096],
                parse_mode="Markdown",
            )
