"""
integrations/calendar_notion/tools.py
─────────────────────────────────────
Calendar tools for Notion integration.
Each tool wraps the NotionCalendarIntegration to provide the Tool interface.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, TYPE_CHECKING

from integrations.base import Tool, CalendarIntegration

if TYPE_CHECKING:
    from integrations.core_ai.provider import NvidiaAIProvider

logger = logging.getLogger(__name__)


# ─── Date conversion helpers ────────────────────────────────────────────────

def _convert_relative_date(date_str: str) -> str:
    """
    Convert relative date strings to ISO 8601 format.
    Supports Spanish and English relative date keywords.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO 8601 date string (YYYY-MM-DD)
    """
    today = datetime.now().date()
    date_lower = date_str.lower().strip()
    
    # Spanish keywords
    if date_lower in ("hoy", "today"):
        return today.isoformat()
    elif date_lower in ("mañana", "tomorrow"):
        return (today + timedelta(days=1)).isoformat()
    elif date_lower in ("ayer", "yesterday"):
        return (today - timedelta(days=1)).isoformat()
    elif "semana" in date_lower or "week" in date_lower:
        # "esta semana" or "this week" → until end of week
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        return (today + timedelta(days=days_until_sunday)).isoformat()
    elif "mes" in date_lower or "month" in date_lower:
        # "este mes" or "this month" → until end of month
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        return end_of_month.isoformat()
    
    # Try to parse as ISO 8601 already
    try:
        datetime.fromisoformat(date_str)
        return date_str
    except ValueError:
        pass
    
    # If nothing matches, return today as fallback
    logger.warning(f"Could not parse date '{date_str}', using today")
    return today.isoformat()


class QueryEventsToolNotion(Tool):
    """Tool for querying calendar events in a date range."""
    
    def __init__(self, calendar: CalendarIntegration):
        self.calendar = calendar
    
    @property
    def name(self) -> str:
        return "query_events"
    
    @property
    def description(self) -> str:
        return "Query calendar events between two dates"
    
    @property
    def required_params(self) -> list[str]:
        return ["date_start", "date_end"]
    
    def execute(self, params: Dict[str, Any]) -> str:
        try:
            date_start = params.get("date_start")
            date_end = params.get("date_end")
            
            if not date_start or not date_end:
                return "❌ Error: date_start and date_end are required"
            
            # Convert relative dates to ISO 8601 format
            date_start = _convert_relative_date(date_start)
            date_end = _convert_relative_date(date_end)
            
            # Ensure date_end is not before date_start
            if date_end < date_start:
                date_end = date_start
            
            events = self.calendar.query_events(date_start, date_end)
            
            if not events:
                return f"📅 No events found between {date_start} and {date_end}"
            
            response = f"📅 Events ({len(events)} found):\n"
            for event in events:
                time_str = ""
                if event.time_start:
                    time_str = f" at {event.time_start}"
                    if event.time_end:
                        time_str += f"-{event.time_end}"
                
                location_str = ""
                if event.location:
                    location_str = f"📍 {event.location}"
                
                response += f"\n• **{event.title}** ({event.date_start}{time_str}){location_str}"
                if event.description:
                    response += f"\n  _{event.description}_"
            
            return response
        except Exception as e:
            logger.error(f"Error querying events: {e}")
            return f"❌ Error querying events: {str(e)}"


class CreateEventToolNotion(Tool):
    """Tool for creating calendar events."""
    
    def __init__(self, calendar: CalendarIntegration):
        self.calendar = calendar
    
    @property
    def name(self) -> str:
        return "create_event"
    
    @property
    def description(self) -> str:
        return "Create a new calendar event"
    
    @property
    def required_params(self) -> list[str]:
        return ["title", "date_start"]
    
    def execute(self, params: Dict[str, Any]) -> str:
        try:
            title = params.get("title")
            date_start = params.get("date_start")
            
            if not title or not date_start:
                return "❌ Error: title and date_start are required"
            
            # Convert relative dates to ISO 8601 format
            date_start = _convert_relative_date(date_start)
            
            date_end = params.get("date_end")
            if date_end:
                date_end = _convert_relative_date(date_end)
            
            time_start = params.get("time_start")
            time_end = params.get("time_end")
            location = params.get("location")
            description = params.get("description")
            
            event = self.calendar.create_event(
                title=title,
                date_start=date_start,
                date_end=date_end,
                time_start=time_start,
                time_end=time_end,
                location=location,
                description=description,
            )
            
            time_str = ""
            if event.time_start:
                time_str = f" at {event.time_start}"
                if event.time_end:
                    time_str += f"-{event.time_end}"
            
            location_str = ""
            if event.location:
                location_str = f" 📍 {event.location}"
            
            return f"✅ Event created: **{event.title}** on {event.date_start}{time_str}{location_str}"
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return f"❌ Error creating event: {str(e)}"


class UpdateEventToolNotion(Tool):
    """Tool for updating calendar events."""
    
    def __init__(self, calendar: CalendarIntegration):
        self.calendar = calendar
    
    @property
    def name(self) -> str:
        return "update_event"
    
    @property
    def description(self) -> str:
        return "Update an existing calendar event"
    
    @property
    def required_params(self) -> list[str]:
        return ["event_id"]
    
    def execute(self, params: Dict[str, Any]) -> str:
        try:
            event_id = params.get("event_id")
            
            if not event_id:
                return "❌ Error: event_id is required"
            
            # All other params are optional
            title = params.get("title")
            date_start = params.get("date_start")
            date_end = params.get("date_end")
            
            # Convert relative dates to ISO 8601 format
            if date_start:
                date_start = _convert_relative_date(date_start)
            if date_end:
                date_end = _convert_relative_date(date_end)
            
            time_start = params.get("time_start")
            time_end = params.get("time_end")
            location = params.get("location")
            description = params.get("description")
            
            event = self.calendar.update_event(
                event_id=event_id,
                title=title,
                date_start=date_start,
                date_end=date_end,
                time_start=time_start,
                time_end=time_end,
                location=location,
                description=description,
            )
            
            time_str = ""
            if event.time_start:
                time_str = f" at {event.time_start}"
                if event.time_end:
                    time_str += f"-{event.time_end}"
            
            return f"✅ Event updated: **{event.title}** on {event.date_start}{time_str}"
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return f"❌ Error updating event: {str(e)}"


class DeleteEventToolNotion(Tool):
    """Tool for deleting calendar events."""
    
    def __init__(self, calendar: CalendarIntegration):
        self.calendar = calendar
    
    @property
    def name(self) -> str:
        return "delete_event"
    
    @property
    def description(self) -> str:
        return "Delete a calendar event"
    
    @property
    def required_params(self) -> list[str]:
        return ["event_id"]
    
    def execute(self, params: Dict[str, Any]) -> str:
        try:
            event_id = params.get("event_id")
            
            if not event_id:
                return "❌ Error: event_id is required"
            
            self.calendar.delete_event(event_id=event_id)
            return f"✅ Event deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return f"❌ Error deleting event: {str(e)}"


class ChatTool(Tool):
    """Tool for general conversation and non-calendar queries."""
    
    def __init__(self, ai_provider: "NvidiaAIProvider"):
        self.ai = ai_provider
    
    @property
    def name(self) -> str:
        return "chat"
    
    @property
    def description(self) -> str:
        return "Have a general conversation or answer questions not related to calendar events"
    
    @property
    def required_params(self) -> list[str]:
        return []
    
    def execute(self, params: Dict[str, Any]) -> str:
        """Execute chat - the message is handled by the user's request context."""
        # This tool is used when the user's message doesn't match calendar tools
        # The actual message should be available from the context
        return "Chat response ready (message context required)"

