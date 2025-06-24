from flask import Flask, request, jsonify
import requests
import jwt
import datetime
import pandas as pd
import re
import os

app = Flask(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def extract_token(auth_header):
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[7:]
    return None


def token_is_expired(token: str) -> bool:
    """Check expiry of JWT without verifying signature."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get("exp")
        if exp is None:
            return True
        expire_time = datetime.datetime.utcfromtimestamp(exp)
        return expire_time < datetime.datetime.utcnow()
    except Exception:
        return True


def parse_file(file):
    file_ext = os.path.splitext(file.filename)[1].lower().strip()
    if file_ext == '.csv':
        df = pd.read_csv(file)
    elif file_ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

    upn_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    phone_pattern = re.compile(r'^\+?\d+(?:\s?\d+)*$')

    pairs = []
    for _, row in df.iterrows():
        upn = None
        phone = None
        for value in row.dropna():
            val = str(value).strip()
            if upn is None and upn_pattern.fullmatch(val):
                upn = val
            if phone is None and phone_pattern.fullmatch(val.replace(' ', '')):
                phone = val
        if upn and phone:
            pairs.append({'upn': upn, 'phone': phone})
    return pairs


def user_has_teams_phone(user_id, token):
    response = requests.get(
        f"{GRAPH_API_BASE}/users/{user_id}/licenseDetails",
        headers=get_auth_headers(token)
    )
    if response.status_code != 200:
        return False
    for lic in response.json().get('value', []):
        for plan in lic.get('servicePlans', []):
            if plan.get('servicePlanName') == 'MCOEV' and plan.get('provisioningStatus') == 'Success':
                return True
    return False


@app.route('/assign', methods=['POST'])
def assign_numbers():
    auth_header = request.headers.get('Authorization')
    token = extract_token(auth_header)

    if not token or token_is_expired(token):
        return jsonify({'error': 'Token fehlt oder abgelaufen'}), 401

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Datei fehlt'}), 400

    try:
        pairs = parse_file(file)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    results = []
    for pair in pairs:
        upn = pair['upn']
        phone = pair['phone']
        user_res = requests.get(f"{GRAPH_API_BASE}/users/{upn}", headers=get_auth_headers(token))
        if user_res.status_code != 200:
            results.append({'upn': upn, 'phone': phone, 'status': 'Benutzer nicht gefunden'})
            continue

        user_data = user_res.json()
        user_id = user_data.get('id')
        user_type = 'ResourceAccount' if user_data.get('userType') == 'Application' else 'User'

        if not user_has_teams_phone(user_id, token):
            results.append({'upn': upn, 'phone': phone, 'status': 'Keine Teams Phone Lizenz', 'target': user_type})
            continue

        patch_res = requests.patch(
            f"{GRAPH_API_BASE}/users/{user_id}",
            headers={**get_auth_headers(token), 'Content-Type': 'application/json'},
            json={'businessPhones': [phone]}
        )
        if patch_res.status_code in (200, 204):
            results.append({'upn': upn, 'phone': phone, 'status': 'Nummer zugewiesen', 'target': user_type})
        else:
            detail = patch_res.json().get('error', {}).get('message', patch_res.status_code)
            results.append({'upn': upn, 'phone': phone, 'status': f'Fehler: {detail}', 'target': user_type})

    return jsonify({'results': results})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
