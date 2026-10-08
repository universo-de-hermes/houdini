"""
Houdini - Schemas Pydantic para Tools
Define el contrato de cada tool que Houdini puede invocar.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum




# ──────────────────────────────────────────────
# SPOTIFY AGENT
# ──────────────────────────────────────────────
class SpotifyPlayInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Canción, artista o playlist a reproducir. Vacío = aleatorio")
    context_uri: Optional[str] = Field(default=None, description="URI de Spotify (playlist:xxx, album:xxx)")

class SpotifyControlInput(BaseModel):
    action: str = Field(..., description="Accion de control: play, pause, next, previous, shuffle_on, shuffle_off")
    device_id: Optional[str] = Field(default=None, description="ID del dispositivo Spotify. Vacío = activo")

class SpotifyVolumeInput(BaseModel):
    volume_percent: int = Field(..., ge=0, le=100, description="Volumen 0-100")

# ──────────────────────────────────────────────
# GMAIL AGENT
# ──────────────────────────────────────────────
class SendEmailInput(BaseModel):
    to: str = Field(..., description="Email destinatario")
    subject: str = Field(..., description="Asunto del correo")
    body: str = Field(..., description="Cuerpo del correo (texto plano o HTML)")
    attachments: list[str] = Field(default=[], description="Lista de rutas de archivos a adjuntar")


class SearchEmailsInput(BaseModel):
    query: str = Field(..., description="Término de búsqueda (ej: 'from:carlos subject:reunion')")
    max_results: int = Field(default=10, description="Máximo número de resultados")


class ReadEmailInput(BaseModel):
    message_id: str = Field(..., description="ID del mensaje a leer")


# ──────────────────────────────────────────────
# CALENDAR AGENT
# ──────────────────────────────────────────────
class CreateEventInput(BaseModel):
    title: str = Field(..., description="Título del evento")
    start: str = Field(..., description="Fecha/hora inicio ISO 8601 (ej: 2025-01-15T14:00:00)")
    end: str = Field(..., description="Fecha/hora fin ISO 8601")
    attendees: list[str] = Field(default=[], description="Lista de emails de asistentes")
    description: Optional[str] = Field(default=None, description="Descripción del evento")


class ListEventsInput(BaseModel):
    range_start: str = Field(..., description="Fecha inicio (ISO 8601)")
    range_end: str = Field(..., description="Fecha fin (ISO 8601)")


class UpdateEventInput(BaseModel):
    event_id: str = Field(..., description="ID del evento a actualizar")
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None


class FindFreeSlotsInput(BaseModel):
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    duration_minutes: int = Field(default=60, description="Duración deseada en minutos")


# ──────────────────────────────────────────────
# SHEETS AGENT
# ──────────────────────────────────────────────
class ReadRangeInput(BaseModel):
    spreadsheet_id: str = Field(..., description="ID del spreadsheet")
    range: str = Field(..., description="Rango a leer (ej: 'Hoja1!A1:D10')")


class WriteRangeInput(BaseModel):
    spreadsheet_id: str = Field(..., description="ID del spreadsheet")
    range: str = Field(..., description="Rango a escribir")
    values: list[list[str]] = Field(..., description="Valores 2D a escribir")
    mode: str = Field(default="overwrite", description="overwrite | append")


# ──────────────────────────────────────────────
# DRIVE AGENT
# ──────────────────────────────────────────────
class UploadFileInput(BaseModel):
    local_path: str = Field(..., description="Ruta local del archivo a subir")
    drive_folder_id: Optional[str] = Field(default=None, description="ID de carpeta en Drive")
    mime_type: Optional[str] = Field(default=None, description="MIME type del archivo")


class SearchFilesInput(BaseModel):
    query: str = Field(..., description="Término de búsqueda en Drive")


class DownloadFileInput(BaseModel):
    file_id: str = Field(..., description="ID del archivo en Drive")
    local_path: str = Field(..., description="Ruta local donde guardar")


# ──────────────────────────────────────────────
# TELEGRAM AGENT
# ──────────────────────────────────────────────
class SendMessageInput(BaseModel):
    chat_id: str = Field(..., description="Chat ID de Telegram")
    text: str = Field(..., description="Texto a enviar")
    parse_mode: Optional[str] = Field(default=None, description="Markdown | HTML | None")


class ScheduleReminderInput(BaseModel):
    chat_id: str = Field(..., description="Chat ID de Telegram")
    text: str = Field(..., description="Mensaje del recordatorio")
    run_at: str = Field(..., description="Fecha/hora ISO 8601 (ej: 2025-01-15T14:00:00)")


# ──────────────────────────────────────────────
# WHATSAPP AGENT (fase 2)
# ──────────────────────────────────────────────
class SendWhatsAppInput(BaseModel):
    phone: str = Field(..., description="Número de teléfono con código país (ej: 573001234567)")
    text: str = Field(..., description="Mensaje a enviar")


# ──────────────────────────────────────────────
# TTS AGENT (Salome voice)
# ──────────────────────────────────────────────
class SpeakInput(BaseModel):
    text: str = Field(..., description="Texto a convertir a voz")
    voice: Optional[str] = Field(default="es-CO-SalomeNeural", description="Voz a usar")
    rate: Optional[str] = Field(default="+0%", description="Velocidad (ej: +10%)")
    volume: Optional[str] = Field(default="+0%", description="Volumen (ej: +20%)")


# ──────────────────────────────────────────────
# DESIGN AGENT
# ──────────────────────────────────────────────
class CreateHTMLInput(BaseModel):
    title: str = Field(..., description="Título del documento HTML")
    content_html: str = Field(..., description="Contenido HTML del cuerpo (párrafos, listas, imágenes)")
    template: str = Field(default="modern-card", description="Plantilla: modern-card, corporate-report, invitation, minimal")
    subtitle: Optional[str] = Field(default=None, description="Subtítulo (usado en plantilla corporate-report)")
    filename: Optional[str] = Field(default=None, description="Nombre del archivo (opcional)")


class ListTemplatesInput(BaseModel):
    pass


class SendDashboardInput(BaseModel):
    recipient_email: Optional[str] = Field(default=None, description="Email del destinatario (opcional, por defecto jhotas96@gmail.com)")


# ──────────────────────────────────────────────
# TOOL REGISTRY - Formato OpenRouter function calling
# ──────────────────────────────────────────────
class ToolCategory(str, Enum):
    GMAIL = "gmail"
    CALENDAR = "calendar"
    SHEETS = "sheets"
    DRIVE = "drive"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    TTS = "tts"
    DESIGN = "design"
    DASHBOARD = "dashboard"
    SPOTIFY = "spotify"


# Diccionario con todas las tools disponibles
# Cada tool = {name, description, parameters (JSON schema), category}
TOOL_REGISTRY = {
    # Gmail
    "send_email": {
        "description": "Enviar un correo electrónico",
        "category": ToolCategory.GMAIL,
        "input_model": SendEmailInput,
    },
    "search_emails": {
        "description": "Buscar correos en Gmail",
        "category": ToolCategory.GMAIL,
        "input_model": SearchEmailsInput,
    },
    "read_email": {
        "description": "Leer un correo específico por ID",
        "category": ToolCategory.GMAIL,
        "input_model": ReadEmailInput,
    },
    # Calendar
    "create_event": {
        "description": "Crear un evento en Google Calendar",
        "category": ToolCategory.CALENDAR,
        "input_model": CreateEventInput,
    },
    "list_events": {
        "description": "Listar eventos en un rango de fechas",
        "category": ToolCategory.CALENDAR,
        "input_model": ListEventsInput,
    },
    "update_event": {
        "description": "Actualizar un evento existente",
        "category": ToolCategory.CALENDAR,
        "input_model": UpdateEventInput,
    },
    "find_free_slots": {
        "description": "Encontrar espacios libres en el calendario",
        "category": ToolCategory.CALENDAR,
        "input_model": FindFreeSlotsInput,
    },
    # Sheets
    "read_range": {
        "description": "Leer un rango de Google Sheets",
        "category": ToolCategory.SHEETS,
        "input_model": ReadRangeInput,
    },
    "write_range": {
        "description": "Escribir en un rango de Google Sheets",
        "category": ToolCategory.SHEETS,
        "input_model": WriteRangeInput,
    },
    # Drive
    "upload_file": {
        "description": "Subir un archivo a Google Drive",
        "category": ToolCategory.DRIVE,
        "input_model": UploadFileInput,
    },
    "search_files": {
        "description": "Buscar archivos en Google Drive",
        "category": ToolCategory.DRIVE,
        "input_model": SearchFilesInput,
    },
    "download_file": {
        "description": "Descargar un archivo de Google Drive",
        "category": ToolCategory.DRIVE,
        "input_model": DownloadFileInput,
    },
    # Telegram
    "send_message": {
        "description": "Enviar un mensaje por Telegram",
        "category": ToolCategory.TELEGRAM,
        "input_model": SendMessageInput,
    },
    "schedule_reminder": {
        "description": "Programar un recordatorio por Telegram",
        "category": ToolCategory.TELEGRAM,
        "input_model": ScheduleReminderInput,
    },
    # TTS
    "speak": {
        "description": "Convertir texto a voz (voz Salome)",
        "category": ToolCategory.TTS,
        "input_model": SpeakInput,
    },
    # Design
    "create_html": {
        "description": "Generar un archivo HTML con diseño Bootstrap (modern-card, corporate-report, invitation, minimal)",
        "category": ToolCategory.DESIGN,
        "input_model": CreateHTMLInput,
    },
    "list_templates": {
        "description": "Listar las plantillas de diseño HTML disponibles",
        "category": ToolCategory.DESIGN,
        "input_model": ListTemplatesInput,
    },
    # Dashboard
    "send_dashboard": {
        "description": "Generar el reporte del Dashboard de Membresias VIP y enviarlo por correo",
        "category": ToolCategory.DASHBOARD,
        "input_model": SendDashboardInput,
    # Spotify
    "spotify_play": {
        "description": "Reproducir música en Spotify (canción, playlist o aleatorio)",
        "category": ToolCategory.SPOTIFY,
        "input_model": SpotifyPlayInput,
    },
    "spotify_control": {
        "description": "Controlar reproducción de Spotify: play/pause/siguiente/anterior/shuffle/repeat",
        "category": ToolCategory.SPOTIFY,
        "input_model": SpotifyControlInput,
    },
    "spotify_volume": {
        "description": "Ajustar volumen de Spotify (0-100)",
        "category": ToolCategory.SPOTIFY,
        "input_model": SpotifyVolumeInput,
    },
    },
}
