"""
Houdini - SheetsAgent
Sub-agente para Google Sheets: leer, escribir, append.
"""
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schemas.tools import ReadRangeInput, WriteRangeInput

logger = logging.getLogger("houdini.agents.sheets")


class SheetsAgent:
    """Sub-agente para Google Sheets."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build("sheets", "v4", credentials=credentials)

    def set_credentials(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("sheets", "v4", credentials=credentials)

    async def read_range(self, params: ReadRangeInput) -> dict:
        """Lee un rango de un spreadsheet."""
        if not self.service:
            return {"error": "Sheets no autenticado"}

        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=params.spreadsheet_id,
                range=params.range,
            ).execute()
            values = result.get("values", [])
            return {"rows": len(values), "values": values}
        except HttpError as e:
            return {"error": str(e)}

    async def write_range(self, params: WriteRangeInput) -> dict:
        """Escribe en un rango de un spreadsheet."""
        if not self.service:
            return {"error": "Sheets no autenticado"}

        try:
            if params.mode == "append":
                result = self.service.spreadsheets().values().append(
                    spreadsheetId=params.spreadsheet_id,
                    range=params.range,
                    valueInputOption="RAW",
                    body={"values": params.values},
                ).execute()
            else:
                result = self.service.spreadsheets().values().update(
                    spreadsheetId=params.spreadsheet_id,
                    range=params.range,
                    valueInputOption="RAW",
                    body={"values": params.values},
                ).execute()
            return {"updated_cells": result.get("updatedCells", 0), "status": "ok"}
        except HttpError as e:
            return {"error": str(e)}
