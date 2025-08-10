import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__, static_folder='static', template_folder='templates')

# Initialize Google Sheets
def init_gsheets():
    try:
        creds_json = os.environ.get('GCP_CREDENTIALS')
        if not creds_json:
            print("ERROR: GCP_CREDENTIALS environment variable not set")
            return None
            
        creds_info = json.loads(creds_json)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open("My First Sheet")
        return sh.sheet1
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return None

sheet = init_gsheets()

# Routes
@app.route('/')
def serve_dashboard():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/data')
def get_data():
    if not sheet:
        return jsonify({"error": "Google Sheets not initialized"}), 500
        
    try:
        records = sheet.get_all_records()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/add_row', methods=['POST'])
def add_row():
    if not sheet:
        return jsonify({"error": "Google Sheets not initialized"}), 500
        
    try:
        data = request.json
        sheet.append_row([
            data.get('Name', ''),
            data.get('City', ''),
            data.get('Age', ''),
            data.get('Email', ''),
            data.get('Phone', '')
        ])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
