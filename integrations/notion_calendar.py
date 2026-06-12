"""
integrations/notion_calendar.py
────────────────────────────────
Implementación completa de CalendarIntegration usando Notion.
Soporta: consultar, crear, editar, eliminar eventos.
Campos opcionales: hora, lugar, descripción.
"""
import logging
import os
from typing import Optional

from notion_client import Client

from core.data_integration import CalendarIntegration, CalendarEvent

logger = logging.getLogger(__name__)

_schema_cache: dict[str, dict] = {}


class NotionCalendarIntegration(CalendarIntegration):

    def __init__(
        self,
        token: str,
        database_id: str,
        prop_titulo: str = "Nombre",
        prop_fecha: str = "Fecha",
        prop_hora: str = "Hora",
        prop_lugar: str = "Lugar",
        prop_descripcion: str = "Descripción",
    ):
        self.notion = Client(auth=token)
        self.database_id = database_id
        self.prop_titulo = prop_titulo
        self.prop_fecha = prop_fecha
        self.prop_hora = prop_hora
        self.prop_lugar = prop_lugar
        self.prop_descripcion = prop_descripcion

        # Detecta qué propiedades existen realmente en la base de datos
        self._available_props = self._load_available_props()

    # ── Interfaz pública ────────────────────────────────────────────────────

    def query_events(self, date_start: str, date_end: str) -> list[CalendarEvent]:
        response = self.notion.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {"property": self.prop_fecha, "date": {"on_or_after": date_start}},
                    {"property": self.prop_fecha, "date": {"on_or_before": date_end}},
                ]
            },
            sorts=[{"property": self.prop_fecha, "direction": "ascending"}],
        )
        return [self._to_event(item) for item in response.get("results", [])]

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
        properties = self._build_properties(
            title=title,
            date_start=date_start,
            date_end=date_end,
            time_start=time_start,
            time_end=time_end,
            location=location,
            description=description,
        )
        page = self.notion.pages.create(
            parent={"database_id": self.database_id},
            properties=properties,
        )
        return self._to_event(page)

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> CalendarEvent:
        # Obtiene el evento actual para no perder campos no mencionados
        current = self.notion.pages.retrieve(page_id=event_id)
        current_event = self._to_event(current)

        properties = self._build_properties(
            title=title or current_event.title,
            date_start=date_start or current_event.date_start,
            date_end=date_end or current_event.date_end,
            time_start=time_start or current_event.time_start,
            time_end=time_end or current_event.time_end,
            location=location or current_event.location,
            description=description or current_event.description,
        )
        page = self.notion.pages.update(page_id=event_id, properties=properties)
        return self._to_event(page)

    def delete_event(self, event_id: str) -> None:
        """Archiva la página (equivalente a eliminar en Notion)."""
        self.notion.pages.update(page_id=event_id, archived=True)

    # ── Construcción de propiedades ─────────────────────────────────────────

    def _build_properties(
        self,
        title: str,
        date_start: str,
        date_end: Optional[str] = None,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Construye el dict de propiedades para la API de Notion.
        Solo incluye propiedades que existen en la base de datos.
        """
        # Fecha: combina fecha + hora en formato ISO 8601 si hay hora
        start_value = f"{date_start}T{time_start}:00" if time_start else date_start
        end_value = None
        if date_end or time_end:
            end_date = date_end or date_start
            end_value = f"{end_date}T{time_end}:00" if time_end else end_date

        date_payload: dict = {"start": start_value}
        if end_value:
            date_payload["end"] = end_value

        properties: dict = {
            self.prop_titulo: {"title": [{"text": {"content": title}}]},
            self.prop_fecha: {"date": date_payload},
        }

        # Campos opcionales: solo se agregan si existen en la base de datos
        if location and self._prop_exists(self.prop_lugar):
            properties[self.prop_lugar] = {"rich_text": [{"text": {"content": location}}]}

        if description and self._prop_exists(self.prop_descripcion):
            properties[self.prop_descripcion] = {"rich_text": [{"text": {"content": description}}]}

        if time_start and self._prop_exists(self.prop_hora):
            hora_texto = f"{time_start}" + (f" – {time_end}" if time_end else "")
            properties[self.prop_hora] = {"rich_text": [{"text": {"content": hora_texto}}]}

        return properties

    # ── Conversión de páginas Notion → CalendarEvent ────────────────────────

    def _to_event(self, item: dict) -> CalendarEvent:
        props = item.get("properties", {})

        # Título
        title_parts = props.get(self.prop_titulo, {}).get("title", [])
        title = title_parts[0]["plain_text"] if title_parts else "(sin título)"

        # Fecha y hora (Notion guarda datetime como "2025-06-10T14:00:00")
        date_obj = props.get(self.prop_fecha, {}).get("date") or {}
        raw_start = date_obj.get("start", "Sin fecha")
        raw_end = date_obj.get("end")

        date_start, time_start = self._split_datetime(raw_start)
        date_end, time_end = self._split_datetime(raw_end) if raw_end else (None, None)

        # Lugar
        lugar_parts = props.get(self.prop_lugar, {}).get("rich_text", [])
        location = lugar_parts[0]["plain_text"] if lugar_parts else None

        # Descripción
        desc_parts = props.get(self.prop_descripcion, {}).get("rich_text", [])
        description = desc_parts[0]["plain_text"] if desc_parts else None

        return CalendarEvent(
            id=item.get("id", ""),
            title=title,
            date_start=date_start,
            date_end=date_end,
            time_start=time_start,
            time_end=time_end,
            location=location,
            description=description,
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _split_datetime(self, value: str) -> tuple[str, Optional[str]]:
        """Separa "2025-06-10T14:00:00" en ("2025-06-10", "14:00")."""
        if "T" in value:
            date_part, time_part = value.split("T", 1)
            return date_part, time_part[:5]  # "HH:MM"
        return value, None

    def _prop_exists(self, prop_name: str) -> bool:
        """Verifica si una propiedad existe en la base de datos."""
        return prop_name in self._available_props

    def _load_available_props(self) -> set[str]:
        """Carga los nombres de propiedades disponibles en la base de datos."""
        try:
            db = self.notion.databases.retrieve(self.database_id)
            return set(db.get("properties", {}).keys())
        except Exception as e:
            logger.warning(f"No se pudo cargar el schema de la base de datos: {e}")
            return set()

    def get_schema(self) -> dict:
        """Devuelve el schema de la base de datos (útil para debugging)."""
        db = self.notion.databases.retrieve(self.database_id)
        schema = {}
        for name, prop in db["properties"].items():
            info = {"type": prop["type"]}
            if prop["type"] in ("select", "multi_select", "status"):
                info["options"] = [x["name"] for x in prop[prop["type"]].get("options", [])]
            schema[name] = info
        return schema