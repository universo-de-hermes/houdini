"""Schemas package"""
from schemas.tools import (
    TOOL_REGISTRY, ToolCategory,
    SendEmailInput, SearchEmailsInput, ReadEmailInput,
    CreateEventInput, ListEventsInput, UpdateEventInput, FindFreeSlotsInput,
    ReadRangeInput, WriteRangeInput,
    UploadFileInput, SearchFilesInput, DownloadFileInput,
    SendMessageInput, ScheduleReminderInput,
    SendWhatsAppInput, SpeakInput,
    CreateHTMLInput, ListTemplatesInput,
)

__all__ = [
    "TOOL_REGISTRY", "ToolCategory",
    "SendEmailInput", "SearchEmailsInput", "ReadEmailInput",
    "CreateEventInput", "ListEventsInput", "UpdateEventInput", "FindFreeSlotsInput",
    "ReadRangeInput", "WriteRangeInput",
    "UploadFileInput", "SearchFilesInput", "DownloadFileInput",
    "SendMessageInput", "ScheduleReminderInput",
    "SendWhatsAppInput", "SpeakInput",
    "CreateHTMLInput", "ListTemplatesInput",
]
