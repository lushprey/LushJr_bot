"""
integrations/platform_telegram/bot.py
─────────────────────────────────────
OPTIMIZADO: typing indicator persistente + executor con más workers.
"""
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from core.processor import MessageProcessor
from integrations.base import PlatformBot

logger = logging.getLogger(__name__)

# Executor dedicado para no bloquear el event loop de Telegram
_executor = ThreadPoolExecutor(max_workers=4)


class TelegramBot(PlatformBot):

    def __init__(self, token: str, processor: MessageProcessor):
        self.token = token
        self.processor = processor
        self._app = self._build_app()

    def run(self) -> None:
        logger.info("🤖 Bot iniciado")
        self._app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            bootstrap_retries=5,
        )

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

    async def _keep_typing(self, update: Update, stop_event: asyncio.Event) -> None:
        """Reenvía 'typing' cada 4s para que no desaparezca mientras la IA procesa."""
        while not stop_event.is_set():
            try:
                await update.message.chat.send_action("typing")
            except Exception:
                pass
            await asyncio.sleep(4)

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text
        user = update.effective_user.first_name if update.effective_user else "?"
        logger.info(f"[{user}] {text!r}")

        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(self._keep_typing(update, stop_typing))

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                _executor, self.processor.process, text
            )
        except Exception as e:
            logger.exception("Error inesperado procesando mensaje")
            response = f"❌ Algo salió mal: {e}"
        finally:
            stop_typing.set()
            typing_task.cancel()

        for i in range(0, len(response), 4096):
            await update.message.reply_text(
                response[i : i + 4096],
                parse_mode="Markdown",
            )