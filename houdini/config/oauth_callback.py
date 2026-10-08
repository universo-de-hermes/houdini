import sys, os, json, threading, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
auth_code = None

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if 'code' in params:
            auth_code = params['code'][0]
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body style="background:#0a0e17;color:#00d4ff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh"><h1>Autorizado - Ya puedes cerrar</h1></body></html>')
        threading.Thread(target=self.server.shutdown, daemon=True).start()
    def log_message(self, *a): pass

flow = InstalledAppFlow.from_client_secrets_file('config/google_client_secret.json', SCOPES)
url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')

server = HTTPServer(('127.0.0.1', 8000), Handler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
time.sleep(0.3)

print('LISTENING on port 8000')
print('URL ready - open browser to authorize')
print(url)
sys.stdout.flush()

while auth_code is None:
    time.sleep(1)

flow.fetch_token(code=auth_code)
creds = flow.credentials
token_data = {k: getattr(creds, k, None) for k in ['token','refresh_token','token_uri','client_id','client_secret','scopes']}
with open('config/google_token.json', 'w') as f:
    json.dump(token_data, f, indent=2, default=str)
print('TOKEN_SAVED')