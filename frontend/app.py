from flask import Flask, render_template, redirect, request, session
import requests
import os

app = Flask(__name__)
app.secret_key = "Frontend-Secret"  # Session aktivieren

# 🌐 Umgebungskonfiguration
DOMAIN = os.getenv("DOMAIN", "workmate.m-haenni.ch")

# 🔒 Öffentlich erreichbare URL für Redirects etc.
EXTERNAL_BASE_URL = f"https://{DOMAIN}"

# 🔁 Interne Container-Adressen für API-Aufrufe (Docker-Netz)
INTERNAL_AUTH_URL = "http://auth-service:5001"
INTERNAL_LICENSE_URL = "http://license-service:5003"

# SSL-Verifizierung (nur für externe Zugriffe wichtig)
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() != "false"

@app.route("/")
def app_frontpage():
    try:
        res = requests.get(
            f"{INTERNAL_AUTH_URL}/me",
            cookies=request.cookies,
            headers={"X-Internal-Request": "true"},
            verify=VERIFY_SSL,
        )
        if res.status_code == 200:
            user_data = res.json()
            session["access_token"] = user_data.get("access_token")
            return redirect("/dashboard")
    except Exception:
        pass  # Ignorieren, wenn Auth-Check fehlschlägt

    return render_template("frontpage.html")

@app.route("/dashboard")
def index():
    try:
        # Token vom Auth-Service holen
        res = requests.get(
            f"{INTERNAL_AUTH_URL}/me",
            cookies=request.cookies,
            headers={"X-Internal-Request": "true"},
            verify=VERIFY_SSL,
        )

        if res.status_code != 200:
            # Nutzer im Browser weiterleiten (öffentliche URL)
            return redirect(f"{EXTERNAL_BASE_URL}/auth")

        user_data = res.json()
        session["access_token"] = user_data.get("access_token")

    except Exception as e:
        return f"Fehler beim Auth-Service: {e}"

    return render_template("dashboard.html", user=user_data)


@app.route("/license")
def license():
    access_token = session.get("access_token")
    print("[Frontend] Access Token:", access_token)

    if not access_token:
        return "Access Token fehlt oder Session abgelaufen", 401

    try:
        license_res = requests.get(
            f"{INTERNAL_LICENSE_URL}/licenses",
            headers={"Authorization": f"Bearer {access_token}"},
            verify=VERIFY_SSL
        )
        print("[Frontend] Status:", license_res.status_code)
        print("[Frontend] Antworttext:", license_res.text)

        license_data = license_res.json()

    except Exception as e:
        return f"Fehler beim License-Service: {e}"

    return render_template("license.html", licenses=license_data)


@app.route("/assign_license", methods=["POST"])
def assign_license():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(f"{EXTERNAL_BASE_URL}/auth")

    file = request.files.get("file")
    license_name = request.form.get("license_name")

    if not file or not license_name:
        return "Datei oder Lizenzname fehlt", 400

    files = {'file': (file.filename, file.stream, file.mimetype)}
    data = {'license_name': license_name}

    try:
        res = requests.post(
            f"{INTERNAL_LICENSE_URL}/assign",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {access_token}"}
        )

        result = res.json()

        return render_template(
            "assign_result.html",
            results=result.get("results", []),
            error=result.get("error"),
            license_name=license_name
        )


    except Exception as e:
        return f"Fehler bei der Lizenzzuweisung: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
