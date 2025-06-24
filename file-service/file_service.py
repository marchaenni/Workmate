from flask import Flask, request, jsonify
import pandas as pd
import re
import os

app = Flask(__name__)

# Regex zur UPN-Erkennung (z.B. max.muster@schule.ch)
def extract_upns(df):
    upn_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    detected_upns = set()

    for index, row in df.iterrows():
        for value in row.dropna():
            value_str = str(value).strip()
            if upn_pattern.fullmatch(value_str):
                detected_upns.add(value_str)

    return list(detected_upns)

@app.route('/upload', methods=['POST'])
def upload_files():
    print("📥 [File-Service] Upload-Request empfangen")
    print("[File-Service] request.files:", request.files)
    print("[File-Service] request.form:", request.form)
    print("[File-Service] keys:", list(request.files.keys()))

    files = request.files.getlist('file')
    print(f"[File-Service] Anzahl empfangene Dateien: {len(files)}")

    if not files:
        msg = "❌ Keine Dateien übergeben."
        print(msg)
        return jsonify({'error': msg}), 400

    all_upns = set()
    file_results = []

    for file in files:
        filename = file.filename
        if not filename:
            print("⚠️ Datei ohne Namen übersprungen.")
            continue

        print(f"📄 Datei empfangen: '{filename}', Typ: {file.mimetype}")

        file_ext = os.path.splitext(filename)[1].lower().strip()
        if not file_ext:
            msg = f"❌ Keine Dateiendung gefunden in '{filename}'"
            print(msg)
            return jsonify({'error': msg}), 400

        try:
            if file_ext == '.csv':
                df = pd.read_csv(file)
                print("✅ Datei als CSV geladen.")
            elif file_ext in ['.xls', '.xlsx']:
                print("🔄 Versuche Excel-Datei mit openpyxl zu laden...")
                df = pd.read_excel(file, engine='openpyxl')
                print("✅ Datei als Excel geladen.")
            else:
                msg = f"❌ Nicht unterstütztes Dateiformat: {file_ext}"
                print(msg)
                return jsonify({'error': msg}), 400
        except Exception as e:
            msg = f"❌ Fehler beim Lesen der Datei '{filename}': {type(e).__name__} – {str(e)}"
            print(msg)
            return jsonify({'error': msg}), 400

        upns = extract_upns(df)
        print(f"🔎 Gefundene UPNs in '{filename}': {upns}")

        all_upns.update(upns)
        file_results.append({
            'filename': filename,
            'detected_upns': upns,
            'total_detected': len(upns)
        })

    if not all_upns:
        msg = "❌ Keine gültigen UPNs erkannt."
        print(msg)
        return jsonify({'error': msg}), 400

    return jsonify({
        'files': file_results,
        'total_upns': len(all_upns),
        'all_detected_upns': list(all_upns)
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002)
