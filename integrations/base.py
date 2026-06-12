"""
integrations/base.py
────────────────────
Shared abstract interfaces that all plugins must implement.
This is the fixed infrastructure for the plugin system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


# ═══════════════════════════════════════════════════════════════════════════
# TOOL ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════════

class Tool(ABC):
    """Abstract base class for all tools/actions the bot can perform."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool (e.g., 'create_event')."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the AI to understand what this tool does."""
        ...
    
    @property
    @abstractmethod
    def required_params(self) -> List[str]:
        """List of required parameter names."""
        ...
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> list[str | bool]:
        """
        Execute the tool with given parameters.
        
        Args:
            params: Dictionary of parameters for the tool
            
        Returns:
            List containing a human-readable response string and a boolean indicating success
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════
# DIRECTIVE ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════════

class Directive(ABC):
    """Abstract base class for directives that group related tools."""
    
    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return list of available tools for this directive."""
        ...
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return system prompt that explains the directive to the AI."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# CALENDAR INTEGRATION ABSTRACTION (existing, kept for compatibility)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CalendarEvent:
    """Platform-agnostic calendar event representation."""
    id: str
    title: str
    date_start: str  # ISO format: "2025-06-10"
    date_end: Optional[str] = None
    time_start: Optional[str] = None  # "14:00"
    time_end: Optional[str] = None    # "15:00"
    location: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, d: dict) -> "CalendarEvent":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            date_start=d.get("date_start", ""),
            date_end=d.get("date_end"),
            time_start=d.get("time_start"),
            time_end=d.get("time_end"),
            location=d.get("location"),
            description=d.get("description"),
        )


class CalendarIntegration(ABC):
    """Abstract base class for calendar data sources (Notion, Google Calendar, etc.)."""
    
    @abstractmethod
    def query_events(self, date_start: str, date_end: str) -> List[CalendarEvent]:
        """
        Query events between two dates.
        
        Args:
            date_start: ISO format date "2025-06-10"
            date_end: ISO format date "2025-06-15"
            
        Returns:
            List of CalendarEvent objects
        """
        ...
    
    @abstractmethod
    def create_event(
        self,
        title: str,
        date_start: str,
        date_end: Optional[str] = None,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        """Create a new calendar event."""
        ...
    
    @abstractmethod
    def update_event(self, event_id: str, **kwargs) -> CalendarEvent:
        """Update an existing calendar event."""
        ...
    
    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        """Delete a calendar event."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# AI PROVIDER ABSTRACTION (existing, extended with new method)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class IntentResult:
    """Legacy data class for backward compatibility."""
    action: str  # "consultar" | "crear" | "editar" | "eliminar" | "chat"
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    time_start: Optional[str] = None       # "HH:MM"
    time_end: Optional[str] = None         # "HH:MM"
    titulo: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    event_id: Optional[str] = None
    respuesta_directa: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "IntentResult":
        return cls(
            action=d.get("accion", "chat"),
            fecha_inicio=d.get("fecha_inicio"),
            fecha_fin=d.get("fecha_fin"),
            time_start=d.get("hora_inicio"),
            time_end=d.get("hora_fin"),
            titulo=d.get("titulo"),
            location=d.get("lugar"),
            description=d.get("descripcion"),
            event_id=d.get("event_id"),
            respuesta_directa=d.get("respuesta_directa"),
        )


@dataclass
class ToolCall:
    """Structured tool call returned by AI."""
    tool_name: str
    params: Dict[str, Any]


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def detect_intent(self, message: str, context: dict) -> IntentResult:
        """Detect user intent from message (legacy method, kept for compatibility)."""
        ...

    @abstractmethod
    def chat(self, message: str, system_prompt: str) -> str:
        """Generate a freeform chat response."""
        ...
    
    @abstractmethod
    def call_with_tools(
        self, 
        message: str,
        tools: List[Tool],
        system_prompt: str
    ) -> ToolCall:
        """
        Call AI with available tools and get structured tool call.
        
        Args:
            message: User message
            tools: List of available Tool objects
            system_prompt: System prompt explaining the directive
            
        Returns:
            ToolCall with tool_name and params
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════
# PLATFORM BOT ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════════

class PlatformBot(ABC):
    """Abstract base class for platform-specific bots."""
    
    @abstractmethod
    def run(self) -> None:
        """Start the bot and begin listening for messages."""
        ...
