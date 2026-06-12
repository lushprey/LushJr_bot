"""
core/processor.py
──────────────────
Pipeline central: orquesta IA + integración de datos.
"""
import logging
from datetime import datetime

from .ai_provider import AIProvider, IntentResult
from .data_integration import CalendarIntegration, CalendarEvent

logger = logging.getLogger(__name__)


class MessageProcessor:

    def __init__(self, ai: AIProvider, calendar: CalendarIntegration):
        self.ai = ai
        self.calendar = calendar

    def process(self, message: str) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        context = {
            "fecha_hoy": today,
            "dia_semana": datetime.now().strftime("%A"),
        }

        try:
            batch = self.ai.detect_intent(message, context)
            logger.info(f"Intención: {intent}")
        except Exception as e:
            logger.warning(f"Fallo al detectar intención, fallback a chat: {e}")
            return self.ai.chat(message, self._system_chat_prompt())

        responses = []
        
        for intent in batch.actions:
        
            if intent.action == "consultar":
                responses.append(
                    self._handle_query(intent, today)
                )
        
            elif intent.action == "crear":
                responses.append(
                    self._handle_create(intent, today)
                )
        
            elif intent.action == "editar":
                responses.append(
                    self._handle_update(intent)
                )
        
            elif intent.action == "eliminar":
                responses.append(
                    self._handle_delete(intent)
                )
        
            else:
                responses.append(
                    self._handle_chat(intent, message)
                )
        
        return "\n\n".join(responses)

    # ── Handlers ────────────────────────────────────────────────────────────

    def _handle_query(self, intent: IntentResult, today: str) -> str:
        fecha_inicio = intent.fecha_inicio or today
        fecha_fin = intent.fecha_fin or fecha_inicio

        try:
            events = self.calendar.query_events(fecha_inicio, fecha_fin)
        except Exception as e:
            logger.exception("Error al consultar calendario")
            return f"❌ No pude consultar el calendario: {e}"

        if not events:
            if fecha_inicio == fecha_fin:
                return f"📭 No tienes eventos el {fecha_inicio}."
            return f"📭 No tienes eventos entre {fecha_inicio} y {fecha_fin}."

        header = (
            f"📅 Eventos del {fecha_inicio}:"
            if fecha_inicio == fecha_fin
            else f"📆 Eventos del {fecha_inicio} al {fecha_fin}:"
        )
        lines = [self._format_event(e) for e in events]
        return header + "\n\n" + "\n".join(lines)

    def _handle_create(self, intent: IntentResult, today: str) -> str:
        titulo = (intent.titulo or "").strip()
        if not titulo:
            return "⚠️ No entendí el nombre del evento. ¿Puedes repetirlo con más detalle?"

        try:
            event = self.calendar.create_event(
                title=titulo,
                date_start=intent.fecha_inicio or today,
                date_end=intent.fecha_fin,
                time_start=intent.time_start,
                time_end=intent.time_end,
                location=intent.location,
                description=intent.description,
            )
        except Exception as e:
            logger.exception("Error al crear evento")
            return f"❌ No pude crear el evento: {e}"

        return self._confirm_create(event)

    def _handle_update(self, intent: IntentResult) -> str:
        if not intent.event_id:
            return "⚠️ No supe qué evento editar. ¿Puedes indicarlo con más detalle?"

        try:
            event = self.calendar.update_event(
                event_id=intent.event_id,
                title=intent.titulo,
                date_start=intent.fecha_inicio,
                date_end=intent.fecha_fin,
                time_start=intent.time_start,
                time_end=intent.time_end,
                location=intent.location,
                description=intent.description,
            )
        except Exception as e:
            logger.exception("Error al editar evento")
            return f"❌ No pude editar el evento: {e}"

        return f"✏️ Evento actualizado: *{event.title}* — {event.date_start}" + (
            f" a las {event.time_start}" if event.time_start else ""
        )

    def _handle_delete(self, intent: IntentResult) -> str:
        if not intent.event_id:
            return "⚠️ No supe qué evento eliminar. ¿Puedes indicarlo con más detalle?"

        try:
            self.calendar.delete_event(intent.event_id)
        except Exception as e:
            logger.exception("Error al eliminar evento")
            return f"❌ No pude eliminar el evento: {e}"

        return "🗑️ Evento eliminado."

    def _handle_chat(self, intent: IntentResult, original_message: str) -> str:
        if intent.respuesta_directa:
            return intent.respuesta_directa
        return self.ai.chat(original_message, self._system_chat_prompt())

    # ── Formato de eventos ───────────────────────────────────────────────────

    def _format_event(self, event: CalendarEvent) -> str:
        parts = [f"• *{event.title}*"]
        date_line = event.date_start
        if event.time_start:
            date_line += f" a las {event.time_start}"
            if event.time_end:
                date_line += f"–{event.time_end}"
        parts.append(f"  📅 {date_line}")
        if event.location:
            parts.append(f"  📍 {event.location}")
        if event.description:
            parts.append(f"  📝 {event.description}")
        return "\n".join(parts)

    def _confirm_create(self, event: CalendarEvent) -> str:
        lines = [f"✅ Agendado: *{event.title}*"]
        date_line = event.date_start
        if event.time_start:
            date_line += f" a las {event.time_start}"
            if event.time_end:
                date_line += f"–{event.time_end}"
        lines.append(f"📅 {date_line}")
        if event.location:
            lines.append(f"📍 {event.location}")
        if event.description:
            lines.append(f"📝 {event.description}")
        return "\n".join(lines)

    def _system_chat_prompt(self) -> str:
        return (
            "Eres un asistente personal amigable integrado en Telegram.\n"
            "Tu nombre es LushJr.\n"
            "Responde de forma natural, fluida y en español.\n"
            "Usa emojis con moderación."
        )
