import os
from flask import Flask, redirect, url_for, session, request, abort, render_template
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials as UserCredentials
from dotenv import load_dotenv
import secrets
import pathlib
import requests
import access  # Ensure access.py is imported to use its functions
import podcast  # Ensure podcast.py is imported to use its functions

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates", static_url_path="/static")
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://127.0.0.1:5000/oauth2callback")

# Scopes:
# - gmail.readonly proves Gmail authorization
# - openid/email/profile lets us show who logged in
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly"
]

def _store_google_creds(creds):
    # Keep it small; avoid putting huge objects in cookies. Consider Flask-Session for server-side storage. WHAT DOES THIS MEAN???
    session["google_creds"] = {
        "token": creds.token,
        "refresh_token": getattr(creds, "refresh_token", None),
        "token_uri": creds.token_uri,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
    }

def _load_google_creds():
    data = session.get("google_creds")
    if not data:
        return None
    creds = UserCredentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    # Refresh if needed
    if creds.expired and creds.refresh_token:
        creds.refresh(google_requests.Request())
        _store_google_creds(creds)  # persist updated token/expiry
    return creds

def get_gmail_service():
    creds = _load_google_creds()
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)

def flow_for_request():
    # Build Flow from explicit client config so we keep everything in one file (no JSON needed).
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": "quiknews-470023",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [OAUTH_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config=client_config, scopes=SCOPES)
    flow.redirect_uri = OAUTH_REDIRECT_URI
    return flow

def logged_in():
    return bool(session.get("user"))

@app.route("/")
def index():
    if logged_in():
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/login")
def login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return "Missing GOOGLE_CLIENT_ID/SECRET. Set them in .env", 500

    flow = flow_for_request()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"  # force refresh token if needed
    )
    session["oauth_state"] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    if "oauth_state" not in session:
        abort(400, description="Missing OAuth state")

    flow = flow_for_request()
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        return f"Failed to fetch token: {e}", 403

    credentials = flow.credentials
    _store_google_creds(credentials)
    # Verify identity with ID token if present; otherwise fetch userinfo via API
    user_info = {}
    try:
        if credentials.id_token:
            idinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            user_info["email"] = idinfo.get("email")
            user_info["name"] = idinfo.get("name")
            print(user_info)
        else:
            # Fallback to userinfo endpoint
            resp = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            user_info.update(resp.json())
    except Exception:
        pass

    # Keep it light: store only essential bits in session
    session["user"] = {
        "email": user_info.get("email"),
        "name": user_info.get("name")
    }
    session["has_gmail_scope"] = True  # Proof that Gmail scope was granted

    return redirect(url_for("home"))

@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for("index"))

    audio_filename = "audio/podcast.mp3"
    transcript_filepath = "app/static/transcripts/transcript.txt"
    audio_filepath = "app/static/audio/podcast.mp3"
    if podcast.is_file_empty(transcript_filepath):
        service = get_gmail_service()
        content = access.create_podcast_content(service)
        podcast.generate_pod(content)
    if podcast.is_file_empty(audio_filepath):
        service = get_gmail_service()
        podcast.generate_audio(transcript_filepath)

    return render_template("home.html", 
                           user=session["user"], 
                           audio_filename=audio_filename)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

from pathlib import Path
@app.route("/__static_debug")
def __static_debug():
    p = Path(app.static_folder)
    files = [str(x.relative_to(p)) for x in p.rglob("*")] if p.exists() else []
    return {
        "app.static_folder": app.static_folder,
        "exists_static": p.exists(),
        "has_podcast": (p / "audio" / "podcast.mp3").exists(),
        "sample_files": files[:50],
    }

# # LOCALLY TEST
# if __name__ == "__main__":
#     # Ensure /static exists
#     pathlib.Path("app/static").mkdir(exist_ok=True)

#     # WSGI Server
#     # app.run(host="127.0.0.1", ssl_context="adhoc", port=5000, debug=True)

#     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
