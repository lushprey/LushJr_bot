"""
integrations/calendar_notion/directive.py
──────────────────────────────────────────
Calendar directive for Notion integration.
Provides all calendar-related tools and system prompt.
"""
from typing import List, Optional, TYPE_CHECKING

from integrations.base import Directive, Tool, CalendarIntegration
from .tools import (
    QueryEventsToolNotion,
    CreateEventToolNotion,
    UpdateEventToolNotion,
    DeleteEventToolNotion,
    ChatTool,
)

if TYPE_CHECKING:
    from integrations.core_ai.provider import NvidiaAIProvider

CALENDAR_SYSTEM_PROMPT = """\
Tu nombre es LushJr.
Eres un asistente personal experto en gestión de calendario.

Tu responsabilidad es ayudar al usuario a gestionar su calendario de forma eficiente.
Tienes acceso a las siguientes herramientas:
- query_events: Buscar eventos en un rango de fechas
- create_event: Crear un nuevo evento
- update_event: Modificar un evento existente
- delete_event: Eliminar un evento
- chat: Para cualquier pregunta o conversación que no sea sobre calendario

Instrucciones:
1. Cuando el usuario pregunta por eventos, usa query_events con rango apropiado
2. Cuando el usuario quiere crear un evento, usa create_event
3. Cuando el usuario quiere modificar un evento, usa update_event
4. Cuando el usuario quiere eliminar, usa delete_event
5. Para eventos relativos (mañana, siguiente semana, etc.), calcula las fechas apropiadas
6. Si el usuario menciona "esta semana", asume desde hoy hasta 6 días después
7. Si la pregunta no es sobre eventos, usa la herramienta chat
8. Responde siempre en español
9. Sé amable y útil en tus respuestas
"""


class CalendarDirective(Directive):
    """Directive that provides calendar management tools."""
    
    def __init__(self, calendar_integration: CalendarIntegration, ai_provider: Optional["NvidiaAIProvider"] = None):
        self.calendar = calendar_integration
        self.ai_provider = ai_provider
        self._tools = [
            QueryEventsToolNotion(calendar_integration),
            CreateEventToolNotion(calendar_integration),
            UpdateEventToolNotion(calendar_integration),
            DeleteEventToolNotion(calendar_integration),
        ]
        
        # Add chat tool if AI provider is available
        if ai_provider:
            self._tools.append(ChatTool(ai_provider))
    
    def get_tools(self) -> List[Tool]:
        """Return list of available calendar tools."""
        return self._tools
    
    def get_system_prompt(self) -> str:
        """Return system prompt for calendar assistant."""
        return CALENDAR_SYSTEM_PROMPT
