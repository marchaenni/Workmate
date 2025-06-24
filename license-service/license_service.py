from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def extract_token(auth_header):
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[7:]
    return None

def get_licenses_dict(token):
    print("[License-Service] Hole Lizenzinformationen...")
    response = requests.get(f"{GRAPH_API_BASE}/subscribedSkus", headers=get_auth_headers(token))
    print(f"[License-Service] Antwortstatus: {response.status_code}")
    if response.status_code != 200:
        raise Exception("Microsoft Graph Fehler bei Lizenzabfrage")

    licenses = {}
    for sku in response.json().get("value", []):
        sku_id = sku["skuId"]
        sku_name = sku["skuPartNumber"]
        total = sku["prepaidUnits"]["enabled"]
        used = sku["consumedUnits"]
        available = total - used
        licenses[sku_name] = {
            "skuId": sku_id,
            "available": available,
            "used": used,
            "total": total
        }
    print("[License-Service] Lizenzen geladen:", licenses)
    return licenses

def user_has_license(user_id, license_sku_id, token):
    print(f"[License-Service] Prüfe Lizenz für User {user_id}")
    response = requests.get(f"{GRAPH_API_BASE}/users/{user_id}/licenseDetails", headers=get_auth_headers(token))
    if response.status_code != 200:
        print("[License-Service] Lizenzdetails nicht abrufbar.")
        return False
    licenses = response.json().get("value", [])
    return any(license["skuId"] == license_sku_id for license in licenses)

@app.route("/licenses", methods=["GET"])
def get_licenses():
    print("[License-Service] /licenses aufgerufen")
    auth_header = request.headers.get("Authorization")
    token = extract_token(auth_header)
    print("[License-Service] Token extrahiert:", token)

    if not token:
        return jsonify({"error": "Kein Token erhalten oder Format ungültig"}), 401

    try:
        licenses = get_licenses_dict(token)
        return jsonify(licenses)
    except Exception as e:
        print("[License-Service] Fehler beim Abrufen der Lizenzen:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/assign", methods=["POST"])
def assign_licenses():
    print("[License-Service] /assign aufgerufen")
    auth_header = request.headers.get("Authorization")
    token = extract_token(auth_header)
    print("[License-Service] Token extrahiert:", token)

    if not token:
        return jsonify({"error": "Kein Token erhalten oder Format ungültig"}), 401

    license_name = request.form.get("license_name")
    file = request.files.get("file")
    print(f"[License-Service] Lizenz: {license_name}")
    print(f"[License-Service] Datei: {file.filename if file else 'Keine'}")

    if not license_name or not file:
        return jsonify({"error": "Lizenzname oder Datei fehlt"}), 400

    try:
        licenses = get_licenses_dict(token)
        if license_name not in licenses:
            print("[License-Service] Lizenz nicht gefunden:", license_name)
            return jsonify({"error": f"Lizenz '{license_name}' nicht gefunden"}), 404

        license_info = licenses[license_name]
        sku_id = license_info["skuId"]
        print(f"[License-Service] Lizenz-ID: {sku_id}")

        try:
            print("[License-Service] Datei wird an File-Service gesendet...")
            print(f"[License-Service] Dateiname zur Weitergabe: '{file.filename}'")
            res = requests.post(
                "http://file-service:5002/upload",
                files=[('file', (file.filename, file.stream, file.mimetype))]
            )
            print(f"[License-Service] Antwort vom File-Service: {res.status_code}")
            if res.status_code != 200:
                print("[License-Service] Fehlerdetails:", res.text)
                return jsonify({"error": "Fehler bei Dateiverarbeitung", "details": res.text}), 400
            users = res.json().get("detected_upns", []) or res.json().get("all_detected_upns", [])
            print("[License-Service] UPNs erkannt:", users)
        except Exception as e:
            print("[License-Service] Fehler beim File-Service:", str(e))
            return jsonify({"error": f"File-Service Fehler: {str(e)}"}), 500

        results = []
        required_licenses = 0

        for upn in users:
            print(f"[License-Service] Prüfe Benutzer: {upn}")
            user_response = requests.get(f"{GRAPH_API_BASE}/users/{upn}", headers=get_auth_headers(token))
            if user_response.status_code != 200:
                print(f"[License-Service] Benutzer nicht gefunden: {upn}")
                results.append({"upn": upn, "status": "Benutzer nicht gefunden"})
                continue

            user_data = user_response.json()
            user_id = user_data.get("id")

            if user_has_license(user_id, sku_id, token):
                results.append({"upn": upn, "status": "Lizenz bereits vorhanden"})
                continue

            if not user_data.get("usageLocation"):
                patch_response = requests.patch(
                    f"{GRAPH_API_BASE}/users/{user_id}",
                    headers={**get_auth_headers(token), "Content-Type": "application/json"},
                    json={"usageLocation": "CH"}
                )
                if patch_response.status_code != 204:
                    results.append({"upn": upn, "status": "Fehler beim Setzen von usageLocation"})
                    continue

            required_licenses += 1
            results.append({"upn": upn, "user_id": user_id})

        if required_licenses > license_info["available"]:
            print("[License-Service] Nicht genügend Lizenzen verfügbar.")
            return jsonify({
                "error": f"Nicht genügend Lizenzen vorhanden ({required_licenses} benötigt, nur {license_info['available']} verfügbar)."
            }), 400

        for result in results:
            if "user_id" not in result:
                continue

            upn = result["upn"]
            user_id = result["user_id"]

            payload = {"addLicenses": [{"skuId": sku_id}], "removeLicenses": []}
            assign = requests.post(
                f"{GRAPH_API_BASE}/users/{user_id}/assignLicense",
                headers={**get_auth_headers(token), "Content-Type": "application/json"},
                json=payload
            )

            if assign.status_code == 200:
                result["status"] = "Lizenz zugewiesen"
            else:
                error_detail = assign.json().get("error", {}).get("message", assign.status_code)
                result["status"] = f"Unbekannter Fehler: {error_detail}"

            result.pop("user_id", None)

        return jsonify({"results": results})

    except Exception as e:
        print("[License-Service] Unerwarteter Fehler:", str(e))
        return jsonify({"error": f"Unerwarteter Fehler: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
