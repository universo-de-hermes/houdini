"""
Houdini - DriveAgent
Sub-agente para Google Drive: subir, buscar, descargar archivos.
"""
import logging
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from schemas.tools import UploadFileInput, SearchFilesInput, DownloadFileInput

logger = logging.getLogger("houdini.agents.drive")


class DriveAgent:
    """Sub-agente para Google Drive."""

    SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build("drive", "v3", credentials=credentials)

    def set_credentials(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("drive", "v3", credentials=credentials)

    async def upload_file(self, params: UploadFileInput) -> dict:
        """Sube un archivo a Google Drive."""
        if not self.service:
            return {"error": "Drive no autenticado"}

        if not os.path.exists(params.local_path):
            return {"error": f"Archivo no encontrado: {params.local_path}"}

        try:
            file_metadata = {"name": os.path.basename(params.local_path)}
            if params.drive_folder_id:
                file_metadata["parents"] = [params.drive_folder_id]

            media = MediaFileUpload(
                params.local_path,
                mimetype=params.mime_type or "application/octet-stream",
                resumable=True,
            )
            uploaded = self.service.files().create(
                body=file_metadata, media_body=media, fields="id,webViewLink"
            ).execute()
            logger.info(f"Archivo subido a Drive: {uploaded.get('id')}")
            return {
                "file_id": uploaded.get("id"),
                "link": uploaded.get("webViewLink", ""),
                "status": "uploaded",
            }
        except HttpError as e:
            return {"error": str(e)}

    async def search_files(self, params: SearchFilesInput) -> dict:
        """Busca archivos en Google Drive."""
        if not self.service:
            return {"error": "Drive no autenticado"}

        try:
            query = f"name contains '{params.query}' and trashed=false"
            results = self.service.files().list(
                q=query, pageSize=20,
                fields="files(id,name,mimeType,modifiedTime,size,webViewLink)"
            ).execute()
            files = results.get("files", [])
            return {
                "count": len(files),
                "files": [
                    {
                        "id": f["id"],
                        "name": f["name"],
                        "mime": f.get("mimeType", ""),
                        "modified": f.get("modifiedTime", ""),
                        "link": f.get("webViewLink", ""),
                    }
                    for f in files
                ],
            }
        except HttpError as e:
            return {"error": str(e)}

    async def download_file(self, params: DownloadFileInput) -> dict:
        """Descarga un archivo de Google Drive."""
        if not self.service:
            return {"error": "Drive no autenticado"}

        try:
            request = self.service.files().get_media(fileId=params.file_id)
            os.makedirs(os.path.dirname(params.local_path) or ".", exist_ok=True)
            with open(params.local_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            return {"path": params.local_path, "status": "downloaded"}
        except HttpError as e:
            return {"error": str(e)}
