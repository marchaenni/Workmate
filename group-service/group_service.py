from flask import Flask, request, jsonify
import requests
import jwt
import datetime

app = Flask(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def extract_token(auth_header):
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[7:]
    return None


def token_is_expired(token: str) -> bool:
    """Prüft das Ablaufdatum des JWT ohne Signaturprüfung."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get("exp")
        if exp is None:
            return True
        expire_time = datetime.datetime.utcfromtimestamp(exp)
        return expire_time < datetime.datetime.utcnow()
    except Exception as e:
        print("[Group-Service] Token konnte nicht dekodiert werden:", e)
        return True


def get_groups_dict(token):
    print("[Group-Service] Hole Gruppeninformationen...")
    response = requests.get(f"{GRAPH_API_BASE}/groups?$select=id,displayName", headers=get_auth_headers(token))
    print(f"[Group-Service] Antwortstatus: {response.status_code}")
    if response.status_code != 200:
        raise Exception("Microsoft Graph Fehler bei Gruppenabfrage")

    groups = {}
    for group in response.json().get("value", []):
        name = group.get("displayName")
        group_id = group.get("id")
        if name:
            groups[name] = group_id
    print("[Group-Service] Gruppen geladen:", groups)
    return groups


@app.route("/groups", methods=["GET"])
def get_groups():
    print("[Group-Service] /groups aufgerufen")
    auth_header = request.headers.get("Authorization")
    token = extract_token(auth_header)
    print("[Group-Service] Token extrahiert:", token)

    if not token or token_is_expired(token):
        return jsonify({"error": "Token fehlt oder abgelaufen"}), 401

    try:
        groups = get_groups_dict(token)
        return jsonify(groups)
    except Exception as e:
        print("[Group-Service] Fehler beim Abrufen der Gruppen:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/assign", methods=["POST"])
def assign_groups():
    print("[Group-Service] /assign aufgerufen")
    auth_header = request.headers.get("Authorization")
    token = extract_token(auth_header)
    print("[Group-Service] Token extrahiert:", token)

    if not token or token_is_expired(token):
        return jsonify({"error": "Token fehlt oder abgelaufen"}), 401

    group_name = request.form.get("group_name")
    file = request.files.get("file")
    print(f"[Group-Service] Gruppe: {group_name}")
    print(f"[Group-Service] Datei: {file.filename if file else 'Keine'}")

    if not group_name or not file:
        return jsonify({"error": "Gruppenname oder Datei fehlt"}), 400

    try:
        groups = get_groups_dict(token)
        if group_name not in groups:
            print("[Group-Service] Gruppe nicht gefunden:", group_name)
            return jsonify({"error": f"Gruppe '{group_name}' nicht gefunden"}), 404

        group_id = groups[group_name]
        print(f"[Group-Service] Gruppen-ID: {group_id}")

        try:
            print("[Group-Service] Datei wird an File-Service gesendet...")
            res = requests.post(
                "http://file-service:5002/upload",
                files=[('file', (file.filename, file.stream, file.mimetype))]
            )
            print(f"[Group-Service] Antwort vom File-Service: {res.status_code}")
            if res.status_code != 200:
                print("[Group-Service] Fehlerdetails:", res.text)
                return jsonify({"error": "Fehler bei Dateiverarbeitung", "details": res.text}), 400
            users = res.json().get("detected_upns", []) or res.json().get("all_detected_upns", [])
            print("[Group-Service] UPNs erkannt:", users)
        except Exception as e:
            print("[Group-Service] Fehler beim File-Service:", str(e))
            return jsonify({"error": f"File-Service Fehler: {str(e)}"}), 500

        results = []
        for upn in users:
            print(f"[Group-Service] Prüfe Benutzer: {upn}")
            user_response = requests.get(f"{GRAPH_API_BASE}/users/{upn}", headers=get_auth_headers(token))
            if user_response.status_code != 200:
                print(f"[Group-Service] Benutzer nicht gefunden: {upn}")
                results.append({"upn": upn, "status": "Benutzer nicht gefunden"})
                continue

            user_id = user_response.json().get("id")
            add_payload = {
                "@odata.id": f"{GRAPH_API_BASE}/directoryObjects/{user_id}"
            }
            add_response = requests.post(
                f"{GRAPH_API_BASE}/groups/{group_id}/members/$ref",
                headers={**get_auth_headers(token), "Content-Type": "application/json"},
                json=add_payload
            )
            if add_response.status_code in (200, 201, 204):
                results.append({"upn": upn, "status": "Zur Gruppe hinzugefügt"})
            else:
                error_detail = add_response.json().get("error", {}).get("message", add_response.status_code)
                results.append({"upn": upn, "status": f"Fehler: {error_detail}"})

        return jsonify({"results": results})

    except Exception as e:
        print("[Group-Service] Unerwarteter Fehler:", str(e))
        return jsonify({"error": f"Unerwarteter Fehler: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
