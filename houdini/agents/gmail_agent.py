"""
Houdini - GmailAgent
Sub-agente para enviar, buscar y leer correos via Gmail API.
"""
import logging
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email.utils import formataddr
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from schemas.tools import SendEmailInput, SearchEmailsInput, ReadEmailInput

logger = logging.getLogger("houdini.agents.gmail")


class GmailAgent:
    """Sub-agente para Gmail."""

    SIGNATURE_HTML = """
<br><br>
<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Arial,sans-serif;font-size:13px;color:#555">
 <tr>
  <td style="padding-bottom:8px">
   <table cellpadding="0" cellspacing="0" border="0">
    <tr>
     <td style="width:40px;height:2px;background:linear-gradient(90deg,#6C3BD2,#B8860B);border-radius:2px"></td>
    </tr>
   </table>
  </td>
 </tr>
 <tr>
  <td style="padding-bottom:2px">
   <span style="font-weight:700;color:#6C3BD2;font-size:14px">Enviado por Houdini</span>
   <span style="color:#999"> — </span>
   <span style="color:#B8860B">Asistente Digital de Juan José</span>
  </td>
 </tr>
</table>"""

    SCOPES = ["https://www.googleapis.com/auth/gmail.send",
              "https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, credentials: Credentials | None = None):
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build("gmail", "v1", credentials=credentials)

    def set_credentials(self, credentials: Credentials):
        self.credentials = credentials
        self.service = build("gmail", "v1", credentials=credentials)

    async def send_email(self, params: SendEmailInput) -> dict:
        """Envía un correo electrónico."""
        if not self.service:
            return {"error": "Gmail no autenticado. Ejecuta oauth setup primero."}

        try:
            message = MIMEMultipart()
            message["to"] = params.to
            message["subject"] = params.subject

            # Cuerpo + firma HTML
            if "<" in params.body:
                # Ya es HTML, se lo agregamos directo
                full_body = params.body + self.SIGNATURE_HTML
            else:
                # Texto plano → lo envolvemos en HTML
                escaped_body = params.body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                full_body = f"""<html><body style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#333;line-height:1.6">
{escaped_body}
{self.SIGNATURE_HTML}
</body></html>"""
            msg_text = MIMEText(full_body, "html", "utf-8")
            message.attach(msg_text)

            # Adjuntos
            for path in params.attachments:
                try:
                    with open(path, "rb") as f:
                        file_bytes = f.read()
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(base64.b64encode(file_bytes).decode())
                    filename = os.path.basename(path)
                    encoded_name = Header(filename, "utf-8").encode()
                    part.add_header("Content-Disposition", "attachment", filename=encoded_name)
                    part.add_header("Content-Transfer-Encoding", "base64")
                    message.attach(part)
                except FileNotFoundError:
                    return {"error": f"Archivo no encontrado: {path}"}

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            sent = self.service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            logger.info(f"Email enviado a {params.to}: {sent['id']}")
            return {"message_id": sent["id"], "status": "sent"}
        except HttpError as e:
            logger.error(f"Error Gmail API: {e}")
            return {"error": str(e)}

    async def search_emails(self, params: SearchEmailsInput) -> dict:
        """Busca correos en Gmail."""
        if not self.service:
            return {"error": "Gmail no autenticado"}

        try:
            results = self.service.users().messages().list(
                userId="me", q=params.query, maxResults=params.max_results
            ).execute()
            messages = results.get("messages", [])
            emails = []
            for msg in messages:
                detail = self.service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()
                headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "snippet": detail.get("snippet", ""),
                })
            return {"count": len(emails), "emails": emails}
        except HttpError as e:
            return {"error": str(e)}

    async def read_email(self, params: ReadEmailInput) -> dict:
        """Lee un correo específico."""
        if not self.service:
            return {"error": "Gmail no autenticado"}

        try:
            msg = self.service.users().messages().get(
                userId="me", id=params.message_id, format="full"
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = self._extract_body(msg.get("payload", {}))
            return {
                "id": msg["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
            }
        except HttpError as e:
            return {"error": str(e)}

    def _extract_body(self, payload: dict) -> str:
        """Extrae el cuerpo del mensaje del payload."""
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                body = self._extract_body(part)
                if body:
                    return body
        return ""
