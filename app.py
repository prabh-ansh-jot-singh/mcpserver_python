from flask import Flask, jsonify, request, render_template_string
import gspread
from google.oauth2.service_account import Credentials
from flask_cors import CORS
import re
import os
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow all origins

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

# Demo data store when Google Sheets is not available
demo_data = [
    {"Name": "Alice Johnson", "City": "London", "Age": "28", "Email": "alice@example.com", "Phone": "1234567890"},
    {"Name": "Bob Smith", "City": "New York", "Age": "35", "Email": "bob@example.com", "Phone": "0987654321"},
    {"Name": "Carol Davis", "City": "Tokyo", "Age": "24", "Email": "carol@example.com", "Phone": "1122334455"},
    {"Name": "David Wilson", "City": "London", "Age": "42", "Email": "david@example.com", "Phone": "2233445566"},
    {"Name": "Eva Brown", "City": "Paris", "Age": "31", "Email": "eva@example.com", "Phone": "3344556677"},
    {"Name": "Frank Miller", "City": "New York", "Age": "29", "Email": "frank@example.com", "Phone": "4455667788"},
    {"Name": "Grace Lee", "City": "Seoul", "Age": "26", "Email": "grace@example.com", "Phone": "5566778899"}
]

# Initialize Google Sheets
sheet = None
gc = None
try:
    # Try to use credentials from environment variable first
    credentials_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )
        logging.info("Using credentials from environment variable")
    else:
        # Fallback to credentials.json file
        credentials = Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        logging.info("Using credentials from file")
    
    gc = gspread.authorize(credentials)
    logging.info("Google Sheets client authorized")
    
    # Use the specific Google Sheet URL from environment variable
    sheet_url = os.environ.get("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/186pG2bEE_ORj3F1eTRfWD6ldhM2-tM8KdvYeHCxJbMA/edit?gid=0#gid=0")
    sh = gc.open_by_url(sheet_url)
    sheet = sh.sheet1
    logging.info(f"Google Sheets initialized successfully: {sheet.title}")
    
except Exception as e:
    logging.error(f"Google Sheets initialization error: {str(e)}")
    logging.info("Running in demo mode - data will be stored in memory only")
    sheet = None

# Helper functions
def validate_data(data):
    """Enhanced AI-powered data validation"""
    errors = []
    
    # Name validation with AI suggestions
    name = data.get('Name', '').strip()
    if not name or len(name) < 2:
        errors.append("Name must be at least 2 characters")
    elif not re.match(r'^[a-zA-Z\s\'-]+$', name):
        errors.append("Name should only contain letters, spaces, hyphens, and apostrophes")
    
    # City validation with smart suggestions
    city = data.get('City', '').strip()
    if not city or len(city) < 2:
        errors.append("City must be at least 2 characters")
    elif not re.match(r'^[a-zA-Z\s\'-]+$', city):
        errors.append("City should only contain letters, spaces, hyphens, and apostrophes")
    
    # Smart age validation
    try:
        age = int(data.get('Age', 0))
        if age < 1 or age > 120:
            errors.append("Age must be between 1 and 120")
        elif age < 13:
            errors.append("Age appears too young for data collection compliance")
    except (ValueError, TypeError):
        errors.append("Age must be a valid number")
    
    # Enhanced email validation
    email = data.get('Email', '').strip().lower()
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        errors.append("Email address is required")
    elif not re.match(email_regex, email):
        errors.append("Please enter a valid email address")
    elif any(domain in email for domain in ['tempmail', '10minute', 'guerrilla']):
        errors.append("Temporary email addresses are not allowed")
    
    # Smart phone validation
    phone = data.get('Phone', '').replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
    if not phone:
        errors.append("Phone number is required")
    elif not phone.isdigit():
        errors.append("Phone number should contain only digits")
    elif len(phone) < 8:
        errors.append("Phone number must be at least 8 digits")
    elif len(phone) > 15:
        errors.append("Phone number seems too long")
    
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
        elif method == 'get_analytics':
            return handle_mcp_get_analytics(mcp_request)
        elif method == 'get_data_quality':
            return handle_mcp_get_data_quality(mcp_request)
        elif method == 'export_data':
            return handle_mcp_export_data(mcp_request)
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": MCP_ERRORS['METHOD_NOT_FOUND'],
                "id": mcp_request.get('id')
            }), 404
            
    except Exception as e:
        logging.error(f"MCP endpoint error: {str(e)}")
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
        
        if sheet:
            sheet.append_row(values)
            logging.info(f"Added row to Google Sheets: {values}")
        else:
            # Demo mode - store in memory
            record = {
                'Name': params.get('Name', ''),
                'City': params.get('City', ''),
                'Age': params.get('Age', ''),
                'Email': params.get('Email', ''),
                'Phone': params.get('Phone', '')
            }
            demo_data.append(record)
            logging.info(f"Added row in demo mode: {record}")
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "status": "success",
                "rows_added": 1,
                "mode": "google_sheets" if sheet else "demo"
            },
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        logging.error(f"Sheet append error: {str(e)}")
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
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
            logging.info(f"Fetched {len(transformed_records)} records from Google Sheets")
        else:
            # Demo mode - return in-memory data
            transformed_records = demo_data
            logging.info("Using demo data")
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": transformed_records,
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        logging.error(f"Sheet get_data error: {str(e)}")
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
        if sheet:
            record_count = len(sheet.get_all_records())
        else:
            # Demo mode - count in-memory data
            record_count = len(demo_data)
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "count": record_count,
                "mode": "google_sheets" if sheet else "demo"
            },
            "id": mcp_request.get('id')
        })
    except Exception as e:
        logging.error(f"Sheet get_row_count error: {str(e)}")
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
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            # Demo mode - use in-memory data
            transformed_records = demo_data
        
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
        logging.error(f"Sheet search error: {str(e)}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['SHEET_ERROR']['code'],
                "message": f"{MCP_ERRORS['SHEET_ERROR']['message']}: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_get_analytics(mcp_request):
    """Get analytics data via MCP protocol"""
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        analytics = generate_analytics(transformed_records)
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": analytics,
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        logging.error(f"Analytics error: {str(e)}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['INTERNAL_ERROR']['code'],
                "message": f"Analytics generation failed: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_get_data_quality(mcp_request):
    """Assess data quality via MCP protocol"""
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        quality_score = assess_data_quality(transformed_records)
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": quality_score,
            "id": mcp_request.get('id')
        })
        
    except Exception as e:
        logging.error(f"Data quality assessment error: {str(e)}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['INTERNAL_ERROR']['code'],
                "message": f"Data quality assessment failed: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def handle_mcp_export_data(mcp_request):
    """Export data in specified format via MCP protocol"""
    params = mcp_request.get('params', {})
    export_format = params.get('format', 'json').lower()
    
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        if export_format == 'csv':
            # Generate CSV format
            if not transformed_records:
                csv_data = "Name,City,Age,Email,Phone\n"
            else:
                headers = ['Name', 'City', 'Age', 'Email', 'Phone']
                csv_data = ','.join(headers) + '\n'
                for record in transformed_records:
                    row = [str(record.get(field, '')).replace(',', ';') for field in headers]
                    csv_data += ','.join(row) + '\n'
            
            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "format": "csv",
                    "data": csv_data,
                    "record_count": len(transformed_records)
                },
                "id": mcp_request.get('id')
            })
        else:
            # Default to JSON format
            return jsonify({
                "jsonrpc": "2.0",
                "result": {
                    "format": "json",
                    "data": transformed_records,
                    "record_count": len(transformed_records)
                },
                "id": mcp_request.get('id')
            })
        
    except Exception as e:
        logging.error(f"Export error: {str(e)}")
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": MCP_ERRORS['INTERNAL_ERROR']['code'],
                "message": f"Data export failed: {str(e)}"
            },
            "id": mcp_request.get('id')
        }), 500

def generate_analytics(data):
    """Generate comprehensive analytics from data"""
    if not data:
        return {"total_records": 0, "message": "No data available"}
    
    total_records = len(data)
    cities = [r.get('City') for r in data if r.get('City')]
    ages = []
    for r in data:
        age_str = r.get('Age', '')
        if age_str and str(age_str).isdigit():
            ages.append(int(age_str))
    
    # City statistics
    city_counts = {}
    for city in cities:
        city_counts[city] = city_counts.get(city, 0) + 1
    
    # Age statistics
    age_stats = {}
    if ages:
        sorted_ages = sorted(ages)
        age_stats = {
            "average": sum(ages) / len(ages),
            "median": sorted_ages[len(ages)//2],
            "min": min(ages),
            "max": max(ages),
            "age_groups": {
                "18-25": len([a for a in ages if 18 <= a <= 25]),
                "26-35": len([a for a in ages if 26 <= a <= 35]),
                "36-45": len([a for a in ages if 36 <= a <= 45]),
                "46+": len([a for a in ages if a >= 46])
            }
        }
    
    return {
        "total_records": total_records,
        "unique_cities": len(set(cities)) if cities else 0,
        "city_distribution": dict(sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "age_statistics": age_stats,
        "data_completeness": assess_data_quality(data)["overall_score"],
        "generated_at": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None))
    }

def assess_data_quality(data):
    """Assess the quality of data records"""
    if not data:
        return {"overall_score": 0, "issues": ["No data available"]}
    
    total_records = len(data)
    complete_records = 0
    issues = []
    field_completeness = {"Name": 0, "City": 0, "Age": 0, "Email": 0, "Phone": 0}
    
    for record in data:
        record_complete = True
        for field in field_completeness.keys():
            if record.get(field) and str(record.get(field)).strip():
                field_completeness[field] += 1
            else:
                record_complete = False
        
        if record_complete:
            complete_records += 1
    
    # Calculate completion rates
    completion_rates = {field: (count/total_records)*100 for field, count in field_completeness.items()}
    overall_score = (complete_records / total_records) * 100
    
    # Identify issues
    if overall_score < 70:
        issues.append("Low data completeness - consider improving data collection")
    
    for field, rate in completion_rates.items():
        if rate < 80:
            issues.append(f"{field} field has low completion rate ({rate:.1f}%)")
    
    return {
        "overall_score": round(overall_score, 1),
        "complete_records": complete_records,
        "total_records": total_records,
        "field_completion_rates": {k: round(v, 1) for k, v in completion_rates.items()},
        "issues": issues if issues else ["Data quality looks good!"],
        "recommendations": generate_quality_recommendations(completion_rates, overall_score)
    }

def generate_quality_recommendations(completion_rates, overall_score):
    """Generate AI-powered recommendations for data quality improvement"""
    recommendations = []
    
    if overall_score >= 90:
        recommendations.append("Excellent data quality! Consider implementing automated data enrichment.")
    elif overall_score >= 70:
        recommendations.append("Good data quality. Focus on improving field completion rates.")
    else:
        recommendations.append("Data quality needs improvement. Implement validation and required field checking.")
    
    # Field-specific recommendations
    for field, rate in completion_rates.items():
        if rate < 60:
            recommendations.append(f"Critical: {field} field needs attention - consider making it required")
        elif rate < 80:
            recommendations.append(f"Moderate: Improve {field} field completion through better UX")
    
    recommendations.append("Consider implementing real-time validation and data enrichment APIs")
    
    return recommendations

# REST Endpoints
@app.route("/get_data", methods=['GET'])
def get_data():
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            # Demo mode - return in-memory data
            transformed_records = demo_data
        
        return jsonify(transformed_records), 200
    except Exception as e:
        logging.error(f"REST get_data error: {str(e)}")
        return jsonify({"status": "error", "message": f"Error fetching data: {str(e)}"}), 500

@app.route("/add_row", methods=['POST'])
def add_row():
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
        
        if sheet:
            sheet.append_row(values)
            logging.info(f"Added row to Google Sheets: {values}")
        else:
            # Demo mode - store in memory
            record = {
                'Name': data.get('Name', ''),
                'City': data.get('City', ''),
                'Age': data.get('Age', ''),
                'Email': data.get('Email', ''),
                'Phone': data.get('Phone', '')
            }
            demo_data.append(record)
            logging.info(f"Added row in demo mode: {record}")
        
        return jsonify({
            "status": "success", 
            "message": f"Row added successfully in {'Google Sheets' if sheet else 'demo'} mode."
        }), 200
    except Exception as e:
        logging.error(f"REST add_row error: {str(e)}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route("/analytics", methods=['GET'])
def get_analytics():
    """REST endpoint for analytics data"""
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        analytics = generate_analytics(transformed_records)
        return jsonify(analytics), 200
    except Exception as e:
        logging.error(f"Analytics REST error: {str(e)}")
        return jsonify({"error": f"Analytics generation failed: {str(e)}"}), 500

@app.route("/data-quality", methods=['GET'])
def get_data_quality():
    """REST endpoint for data quality assessment"""
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        quality_assessment = assess_data_quality(transformed_records)
        return jsonify(quality_assessment), 200
    except Exception as e:
        logging.error(f"Data quality REST error: {str(e)}")
        return jsonify({"error": f"Data quality assessment failed: {str(e)}"}), 500

@app.route("/export/<format>", methods=['GET'])
def export_data(format):
    """REST endpoint for data export"""
    try:
        if sheet:
            all_records = sheet.get_all_records()
            transformed_records = [transform_record(record) for record in all_records]
        else:
            transformed_records = demo_data
        
        if format.lower() == 'csv':
            if not transformed_records:
                csv_data = "Name,City,Age,Email,Phone\n"
            else:
                headers = ['Name', 'City', 'Age', 'Email', 'Phone']
                csv_lines = [','.join(headers)]
                for record in transformed_records:
                    row = [f'"{str(record.get(field, ""))}"' for field in headers]
                    csv_lines.append(','.join(row))
                csv_data = '\n'.join(csv_lines)
            
            return csv_data, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename="data_export_{logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None)).replace(":", "-")}.csv"'
            }
        else:
            return jsonify(transformed_records), 200
            
    except Exception as e:
        logging.error(f"Export REST error: {str(e)}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

@app.route("/")
def home():
    """Serve the main dashboard"""
    try:
        with open('index.html', 'r') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return jsonify({"error": "Dashboard not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
