"""
core/data_integration.py
─────────────────────────
Interfaz abstracta para integraciones de calendario.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CalendarEvent:
    """Representación agnóstica de un evento de calendario."""
    id: str
    title: str
    date_start: str
    date_end: Optional[str] = None
    time_start: Optional[str] = None   # "HH:MM"
    time_end: Optional[str] = None     # "HH:MM"
    location: Optional[str] = None
    description: Optional[str] = None
    extra: dict = field(default_factory=dict)


class CalendarIntegration(ABC):

    @abstractmethod
    def query_events(self, date_start: str, date_end: str) -> list[CalendarEvent]:
        ...

    @abstractmethod
    def create_event(self, title: str, date_start: str, **kwargs) -> CalendarEvent:
        ...

    @abstractmethod
    def update_event(self, event_id: str, **kwargs) -> CalendarEvent:
        ...

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        ...