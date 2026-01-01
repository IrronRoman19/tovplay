"""
Simple application entry point for TovPlay Backend
This is a simplified version for Docker deployments
"""
from src.app import create_app

# Create the Flask application instance
application = create_app()

if __name__ == "__main__":
    application.run(host="127.0.0.1", port=5001, debug=False)