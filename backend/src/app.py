"""
Main application entry point for TovPlay Backend
This file serves as the WSGI entry point for production deployments
"""
from src.app import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)