# Overview

**Puch AI Hackathon Project: Intelligent Data Hub**
Built by team "Backdoorz" for Puch AI's #BuildWithPuch hackathon - Phase 1: Be Wozniak (48 hours)

An AI-powered data collection and analytics platform that goes beyond simple forms. This MCP v2.0 compliant system provides:
- Real-time data validation and enrichment using AI
- Smart data insights and analytics dashboard
- Automated data quality scoring and recommendations
- Export capabilities for business intelligence
- Advanced search and filtering with natural language queries

The platform demonstrates practical AI integration that people would actually want to use for data management, making complex data operations accessible through an intuitive interface.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology**: Vanilla HTML/CSS/JavaScript with Tailwind CSS for styling
- **Design Pattern**: Single-page application with tabbed interface
- **Components**: Data collection form and MCP client interface
- **Styling**: Modern, responsive design using Tailwind CSS framework and Inter font family
- **Validation**: Client-side form validation with real-time error feedback

## Backend Architecture
- **Framework**: Flask web application with CORS enabled for cross-origin requests
- **API Pattern**: RESTful endpoints with MCP protocol compliance
- **Error Handling**: Structured error codes following JSON-RPC 2.0 specification
- **Validation**: Server-side data validation with custom validation functions
- **Logging**: Comprehensive logging for debugging and monitoring

## Data Storage
- **Primary Storage**: Google Sheets as the database backend
- **Authentication**: Service account credentials for Google Sheets API access
- **Schema**: Simple tabular structure storing Name, City, and Age fields
- **Access Pattern**: Direct Google Sheets API integration using gspread library

## Authentication & Authorization
- **Google Sheets Access**: Service account authentication using JSON credentials
- **Scopes**: Read/write access to Google Sheets and Google Drive
- **Security**: Service account key stored in credentials.json file

## Data Validation
- **Name Validation**: Minimum 2 characters, alphabetic characters only
- **City Validation**: Minimum 2 characters, alphabetic characters only  
- **Age Validation**: Numeric values between 1 and 120
- **Error Handling**: Structured validation errors with specific field-level feedback

# External Dependencies

## Google Services
- **Google Sheets API**: Primary data storage backend
- **Google Drive API**: File access and management
- **Service Account**: Authentication mechanism for API access

## Python Libraries
- **Flask**: Web framework and HTTP server
- **gspread**: Google Sheets API client library
- **google-oauth2**: Authentication and authorization
- **flask-cors**: Cross-origin resource sharing support

## Frontend Dependencies
- **Tailwind CSS**: Utility-first CSS framework via CDN
- **Google Fonts**: Inter font family for typography
- **Native JavaScript**: No external JavaScript frameworks

## Development Tools
- **Python 3.9.13**: Runtime environment
- **Logging**: Built-in Python logging for application monitoring