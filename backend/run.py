#!/usr/bin/env python3
"""
TovPlay Backend Application Runner
Run this file to start the Flask development server
"""

import os
import sys
import threading

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

from src.app import create_app


    # Start websocket server in a background thread
def start_ws_server(app):
    from src.api import realtime_backend
    realtime_backend.start_servers(app)


app = create_app()

if __name__ == "__main__":


    # Only start the websocket server in the main Flask process (not the reloader)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        ws_thread = threading.Thread(target=start_ws_server, args=(app,), daemon=True)
        ws_thread.start()

    # Get configuration from environment variables
    # Override HOST for local development
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("FLASK_ENV", "development") == "development"

    print(f"[STARTING] TovPlay Backend on http://{host}:{port}")
    print(f"[DEBUG] Debug mode: {debug}")
    print(f"[DATABASE] Database connected: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
    print("[READY] Application ready! Press Ctrl+C to stop")

    # Start the development server - NEVER use debug=True hardcoded
    app.run(host=host, port=port, debug=debug, threaded=True)
