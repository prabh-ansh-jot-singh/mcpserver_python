from flask import Flask, jsonify, request
import gspread
from google.oauth2.service_account import Credentials
from flask_cors import CORS
import re

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Error codes
MCP_ERRORS = {
    'PARSE_ERROR': {'code': -32700, 'message': 'Parse error'},
    'INVALID_REQUEST': {'code': -32600, 'message': 'Invalid Request'},
    'METHOD_NOT_FOUND': {'code': -32601, 'message': 'Method not found'},
    'INVALID_PARAMS': {'code': -32602, 'message': 'Invalid params'},
    'INTERNAL_ERROR': {'code': -32603, 'message': 'Internal error'},
    'SHEET_ERROR': {'code': -32000, 'message': 'Sheet operation failed'},
    'VALIDATION_ERROR': {'code': -32001, 'message': 'Validation failed'},
    'DATA_NOT_FOUND': {'code': -32002, 'message': 'Requested data not found'}
}

# Initialize Google Sheets
try:
    credentials = Credentials.from_service_account_file(
        'credentials.json',
        scopes=SCOPES
    )
    gc = gspread.authorize(credentials)
    sh = gc.open("My First Sheet")
    sheet = sh.sheet1
except Exception as e:
    print(f"Initialization error: {e}")
    sheet = None

# Helper functions
def validate_data(data):
    """Validate the incoming data"""
    errors = []
    
    if not data.get('Name') or len(data['Name'].strip()) < 2:
        errors.append("Name must be at least 2 characters")
    
    if not data.get('City') or len(data['City'].strip()) < 2:
        errors.append("City must be at least 2 characters")
    
    try:
        age = int(data.get('Age', 0))
        if age < 1 or age > 120:
            errors.append("Age must be between 1 and 120")
    except ValueError:
        errors.append("Age must be a valid number")
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, data.get('Email', '')):
        errors.append("Please enter a valid email address")
    
    phone = data.get('Phone', '').replace(" ", "").replace("-", "")
    if not phone.isdigit() or len(phone) < 8:
        errors.append("Phone must be at least 8 digits")
    
    return errors

def transform_record(record):
    """Transform record keys to standard format"""
    transformed = {}
    field_mappings = {
        'Name': ['name', 'Name', 'NAME'],
        'City': ['city', 'City', 'CITY'],
        'Age': ['age', 'Age', 'AGE'],
        'Email': ['email', 'Email', 'EMAIL'],
        'Phone': ['phone', 'Phone', 'PHONE']
    }
    
    for standard_field, possible_keys in field_mappings.items():
        for key in possible_keys:
            if key in record:
                transformed[standard_field] = record[key]
                break
        else:
            transformed[standard_field] = ''
    
    return transformed

# MCP Protocol Endpoints
@app.route("/mcp", methods=['POST'])
def mcp_endpoint():
    """Handle MCP protocol requests"""
    try:
        mcp_request = request.get_json()
        if not mcp_request:
            raise ValueError("Empty request")
            
        if not all(k in mcp_request for k in ['jsonrpc', 'method', 'params']):
            return jsonify({
                "jsonrpc": "2.0",
                "error": MCP_ERRORS['INVALID_REQUEST'],
                "id": mcp_request.get('id')
            }), 400
        
        method = mcp_request['method']
        if method == 'add_row':
            return handle_mcp_add_row(mcp_request)
        elif method == 'get_data':
            return handle_mcp_get_data(mcp_request)
        elif method == 'get_row_count':
            return handle_mcp_get_row_count(mcp_request)
        elif method == 'search_records':
            return handle_mcp_search_records(mcp_request)
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": MCP_ERRORS['METHOD_NOT_FOUND'],
                "id": mcp_request.get('id')
            }), 404
            
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['INTERNAL_ERROR']['code'],
                "message": f"{MCP_ERRORS['INTERNAL_ERROR']['message']}: {str(e)}"
            },
            "id": request.get_json().get('id') if request.get_json() else None
        }), 500

def handle_mcp_add_row(mcp_request):
    params = mcp_request['params']
    
    if not isinstance(params, dict) or not all(k in params for k in ['Name', 'City']):
        return jsonify({
            "jsonrpc": "2.0",
            "error": MCP_ERRORS['INVALID_PARAMS'],
            "id": mcp_request.get('id')
        }), 400
    
    validation_errors = validate_data(params)
    if validation_errors:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['VALIDATION_ERROR']['code'],
                "message": MCP_ERRORS['VALIDATION_ERROR']['message'],
                "data": validation_errors
            },
            "id": mcp_request.get('id')
        }), 400
    
    try:
        values = [
            params.get('Name', ''),
            params.get('City', ''),
            params.get('Age', ''),
            params.get('Email', ''),
            params.get('Phone', '')
        ]
        
        sheet.append_row(values)
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "status": "success",
                "rows_added": 1
            },
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['SHEET_ERROR']['code'],
                "message": f"{MCP_ERRORS['SHEET_ERROR']['message']}: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_get_data(mcp_request):
    try:
        all_records = sheet.get_all_records()
        transformed_records = [transform_record(record) for record in all_records]
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": transformed_records,
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['SHEET_ERROR']['code'],
                "message": f"{MCP_ERRORS['SHEET_ERROR']['message']}: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_get_row_count(mcp_request):
    try:
        record_count = len(sheet.get_all_records())
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "count": record_count
            },
            "id": mcp_request.get('id')
        })
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['SHEET_ERROR']['code'],
                "message": f"{MCP_ERRORS['SHEET_ERROR']['message']}: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_search_records(mcp_request):
    params = mcp_request['params']
    
    if not isinstance(params, dict) or not any(k in params for k in ['Name', 'City', 'Email']):
        return jsonify({
            "jsonrpc": "2.0",
            "error": MCP_ERRORS['INVALID_PARAMS'],
            "id": mcp_request.get('id')
        }), 400
    
    try:
        all_records = sheet.get_all_records()
        transformed_records = [transform_record(record) for record in all_records]
        
        filtered_records = []
        for record in transformed_records:
            match = True
            for field, value in params.items():
                if field in record and value.lower() not in str(record[field]).lower():
                    match = False
                    break
            if match:
                filtered_records.append(record)
        
        if not filtered_records:
            return jsonify({
                "jsonrpc": "2.0",
                "error": MCP_ERRORS['DATA_NOT_FOUND'],
                "id": mcp_request.get('id')
            }), 404
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": filtered_records,
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['SHEET_ERROR']['code'],
                "message": f"{MCP_ERRORS['SHEET_ERROR']['message']}: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

# REST Endpoints (optional)
@app.route("/get_data", methods=['GET'])
def get_data():
    if not sheet:
        return jsonify({"status": "error", "message": "Failed to load sheet."}), 500
    try:
        all_records = sheet.get_all_records()
        transformed_records = [transform_record(record) for record in all_records]
        return jsonify(transformed_records), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error fetching data: {str(e)}"}), 500

@app.route("/add_row", methods=['POST'])
def add_row():
    if not sheet:
        return jsonify({"status": "error", "message": "Failed to load sheet."}), 500
    try:
        data = request.get_json()
        validation_errors = validate_data(data)
        if validation_errors:
            return jsonify({
                "status": "error",
                "message": "Validation failed",
                "errors": validation_errors
            }), 400
        
        values = [
            data.get('Name', ''),
            data.get('City', ''),
            data.get('Age', ''),
            data.get('Email', ''),
            data.get('Phone', '')
        ]
        
        sheet.append_row(values)
        return jsonify({"status": "success", "message": "Row added successfully."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route("/")
def home():
    if not sheet:
        return jsonify({"status": "error", "message": "Failed to load sheet."}), 500
    try:
        all_records = sheet.get_all_records()
        transformed_records = [transform_record(record) for record in all_records]
        return jsonify(transformed_records)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)