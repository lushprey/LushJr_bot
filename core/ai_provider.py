"""
core/ai_provider.py
────────────────────
Interfaz abstracta para proveedores de IA.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class IntentResult:
    action: str  # "consultar" | "crear" | "editar" | "eliminar" | "chat"
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    time_start: Optional[str] = None       # "HH:MM"
    time_end: Optional[str] = None         # "HH:MM"
    titulo: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    event_id: Optional[str] = None         # Para editar/eliminar
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
class IntentBatch:
    actions: List[IntentResult] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "IntentBatch":

        if "actions" in data:
            return cls(
                actions=[
                    IntentResult.from_dict(item)
                    for item in data["actions"]
                ]
            )

        return cls(
            actions=[IntentResult.from_dict(data)]
        )


class AIProvider(ABC):

    @abstractmethod
    def detect_intent(self, message: str, context: dict) -> IntentBatch:
        ...

    @abstractmethod
    def chat(self, message: str, system_prompt: str) -> str:
        ...
