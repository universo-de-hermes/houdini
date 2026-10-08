"""
Houdini - CalendarAgent
Sub-agente para Google Calendar: crear, listar, actualizar eventos.
"""
import logging
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schemas.tools import (
    CreateEventInput, ListEventsInput, UpdateEventInput, FindFreeSlotsInput
)

logger = logging.getLogger("houdini.agents.calendar")


class CalendarAgent:
    """Sub-agente para Google Calendar."""

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build("calendar", "v3", credentials=credentials)

    def set_credentials(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("calendar", "v3", credentials=credentials)

    async def create_event(self, params: CreateEventInput) -> dict:
        """Crea un evento en Google Calendar."""
        if not self.service:
            return {"error": "Calendar no autenticado"}

        try:
            event = {
                "summary": params.title,
                "start": {"dateTime": params.start, "timeZone": "America/Bogota"},
                "end": {"dateTime": params.end, "timeZone": "America/Bogota"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 10},
                        {"method": "email", "minutes": 10},
                    ],
                },
            }
            if params.description:
                event["description"] = params.description
            if params.attendees:
                event["attendees"] = [{"email": e} for e in params.attendees]

            created = self.service.events().insert(
                calendarId="primary", body=event
            ).execute()
            logger.info(f"Evento creado: {created.get('id')}")
            return {
                "event_id": created.get("id"),
                "html_link": created.get("htmlLink", ""),
                "status": "created",
            }
        except HttpError as e:
            return {"error": str(e)}

    async def list_events(self, params: ListEventsInput) -> dict:
        """Lista eventos en un rango de fechas."""
        if not self.service:
            return {"error": "Calendar no autenticado"}

        try:
            # Asegurar que las fechas tengan zona horaria
            time_min = params.range_start
            time_max = params.range_end
            if "Z" not in time_min and "+" not in time_min and "T" in time_min:
                time_min += "-05:00"
            if "Z" not in time_max and "+" not in time_max and "T" in time_max:
                time_max += "-05:00"

            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = events_result.get("items", [])
            return {
                "count": len(events),
                "events": [
                    {
                        "id": e.get("id"),
                        "title": e.get("summary", ""),
                        "start": e.get("start", {}).get("dateTime", ""),
                        "end": e.get("end", {}).get("dateTime", ""),
                        "attendees": [a.get("email") for a in e.get("attendees", [])],
                    }
                    for e in events
                ],
            }
        except HttpError as e:
            return {"error": str(e)}

    async def update_event(self, params: UpdateEventInput) -> dict:
        """Actualiza un evento existente."""
        if not self.service:
            return {"error": "Calendar no autenticado"}

        try:
            event = self.service.events().get(
                calendarId="primary", eventId=params.event_id
            ).execute()

            if params.title:
                event["summary"] = params.title
            if params.start:
                event["start"] = {"dateTime": params.start, "timeZone": "America/Bogota"}
            if params.end:
                event["end"] = {"dateTime": params.end, "timeZone": "America/Bogota"}
            if params.description is not None:
                event["description"] = params.description

            updated = self.service.events().update(
                calendarId="primary", eventId=params.event_id, body=event
            ).execute()
            return {"event_id": updated.get("id"), "status": "updated"}
        except HttpError as e:
            return {"error": str(e)}

    async def find_free_slots(self, params: FindFreeSlotsInput) -> dict:
        """Encuentra espacios libres usando FreeBusy API."""
        if not self.service:
            return {"error": "Calendar no autenticado"}

        try:
            start = f"{params.date}T00:00:00-05:00"
            end = f"{params.date}T23:59:59-05:00"
            body = {
                "timeMin": start,
                "timeMax": end,
                "items": [{"id": "primary"}],
            }
            result = self.service.freebusy().query(body=body).execute()
            busy = result.get("calendars", {}).get("primary", {}).get("busy", [])

            # Calcular huecos libres
            free_slots = []
            day_start = datetime.fromisoformat(f"{params.date}T08:00:00-05:00")
            day_end = datetime.fromisoformat(f"{params.date}T18:00:00-05:00")
            current = day_start
            for b in busy:
                b_start = datetime.fromisoformat(b["start"])
                b_end = datetime.fromisoformat(b["end"])
                if b_start > current:
                    delta = (b_start - current).total_seconds() / 60
                    if delta >= params.duration_minutes:
                        free_slots.append({
                            "start": current.isoformat(),
                            "end": b_start.isoformat(),
                            "minutes": int(delta),
                        })
                current = max(current, b_end)
            if day_end > current:
                delta = (day_end - current).total_seconds() / 60
                if delta >= params.duration_minutes:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": day_end.isoformat(),
                        "minutes": int(delta),
                    })

            return {"free_slots": free_slots}
        except HttpError as e:
            return {"error": str(e)}
