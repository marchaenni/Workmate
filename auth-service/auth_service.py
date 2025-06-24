from flask import Flask, redirect, request, session, url_for, jsonify
import msal
import redis  
import os
from urllib.parse import urljoin
from flask_session import Session

# Auth-Konfiguration
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

# Umgebungsspezifische Konfiguration
DOMAIN = os.environ.get("DOMAIN", "localhost:5000")  # Optionaler Fallback für Entwicklung
VERIFY_SSL = os.environ.get("VERIFY_SSL", "true").lower() == "true"  # Als bool umwandeln

# URL-Konstruktion
FRONTEND_URL = f"https://{DOMAIN}/dashboard"
REDIRECT_URI = f"https://{DOMAIN}/getAToken"

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SECRET_KEY'] = "App-Secret"
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_REDIS'] = redis.from_url("redis://redis:6379")
Session(app)

AUTHORITY = 'https://login.microsoftonline.com/common'

SCOPE = [
    "User.Read",
    "User.Read.All",
    "Directory.Read.All",
    "Directory.AccessAsUser.All"
]

@app.route("/")
def index():
    if 'user' in session:
        return f"Eingeloggt als {session['user']['name']} - Tenant: {session.get('tenant_id')}"
    return redirect(url_for("login"))

@app.route("/login")
def login():
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    auth_url = msal_app.get_authorization_request_url(
        SCOPE, redirect_uri=REDIRECT_URI
    )
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    result = msal_app.acquire_token_by_authorization_code(
        request.args['code'], scopes=SCOPE, redirect_uri=REDIRECT_URI
    )

    print("🔁 Auth-Result von MSAL:", result)

    if "access_token" in result:
        session["user"] = result.get("id_token_claims")
        session["access_token"] = result["access_token"]
        session["tenant_id"] = session["user"]["tid"]

        print("✅ ACCESS TOKEN gespeichert:", result["access_token"])

        return redirect(FRONTEND_URL)
    else:
        print("❌ Auth fehlgeschlagen:", result)
        return "Login fehlgeschlagen.", 400

@app.route("/me")
def me():
    if 'user' not in session:
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "name": session["user"]["name"],
        "tenant_id": session["tenant_id"],
        "access_token": session["access_token"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

