"""
Houdini - Servicio de Autenticación Google OAuth2
Maneja el flujo OAuth para Gmail, Calendar, Sheets y Drive.
"""
import os
import json
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger("houdini.services.oauth")
from config.settings import get_settings
settings = get_settings()


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleOAuth:
    """Gestiona OAuth2 para todos los servicios de Google."""

    def __init__(self):
        self.client_secrets_path = "config/google_client_secret.json"
        self.token_path = "config/google_token.json"

    def get_credentials(self) -> Credentials | None:
        """Obtiene credenciales válidas: carga token existente o inicia flujo OAuth."""
        creds = None

        # Cargar token existente
        if os.path.exists(self.token_path):
            with open(self.token_path, "r") as f:
                creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)

        # Si no hay creds o están expiradas, refrescar o pedir autorización
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(GoogleRequest())
                    self._save_token(creds)
                    logger.info("Token de Google refrescado")
                except Exception as e:
                    logger.warning(f"No se pudo refrescar token de Google: {e}. Continuando sin Google.")
                    return None
            else:
                creds = self._run_oauth_flow()
        return creds

    def _run_oauth_flow(self) -> Credentials | None:
        """Ejecuta el flujo OAuth interactivo (abre navegador una vez)."""
        if not os.path.exists(self.client_secrets_path):
            logger.error(
                f"No se encontró {self.client_secrets_path}. "
                "Descarga tu client_secret.json desde Google Cloud Console."
            )
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_path, SCOPES
            )
            creds = flow.run_local_server(port=8000)
            self._save_token(creds)
            logger.info("OAuth completado - token guardado")
            return creds
        except Exception as e:
            logger.error(f"Error en OAuth flow: {e}")
            return None

    def _save_token(self, creds: Credentials):
        """Guarda el token en disco."""
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, "w") as f:
            json.dump(token_data, f, indent=2)
