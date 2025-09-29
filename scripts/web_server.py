#!/usr/bin/env python3
"""
Simple web server to serve the Memory Stages chat UI.
Starts a local HTTP server that serves the web directory on port 3000.
"""

import os
import sys
import http.server
import socketserver
import webbrowser
from pathlib import Path
import argparse

# Add the parent directory to sys.path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import DEBUG


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler that suppresses logs in production."""

    def log_message(self, format, *args):
        if DEBUG:
            super().log_message(format, *args)
        # Suppress logs in production

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description='Serve Memory Stages Chat UI')
    parser.add_argument('--port', type=int, default=3000,
                       help='Port to serve on (default: 3000)')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind to (default: localhost)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not automatically open browser')
    parser.add_argument('--api-url',
                       help='API server URL (for CORS, default: same host on port 8000)')

    args = parser.parse_args()

    # Determine the web directory
    web_dir = Path(__file__).parent.parent / "web"
    if not web_dir.exists():
        print(f"❌ Error: Web directory not found at {web_dir}")
        print("Run this script from the project root or create the web directory first.")
        sys.exit(1)

    # Change to web directory
    os.chdir(web_dir)

    # Configure the server
    Handler = QuietHTTPRequestHandler

    try:
        with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
            server_url = f"http://{args.host}:{args.port}"
            api_url = args.api_url or f"http://{args.host}:8000"

            print("🧠 Memory Stages Chat UI Server")
            print("=" * 50)
            print(f"📁 Serving files from: {web_dir}")
            print(f"🌐 Web UI available at: {server_url}")
            print(f"🔗 Expected API server: {api_url}")
            print("")
            print("📋 Instructions:")
            print(f"1. Make sure your FastAPI server is running on {api_url}")
            print("2. Open your browser and go to the Web UI URL above")
            print("3. Start chatting with your memory system!")
            print("")
            print("Press Ctrl+C to stop the server")
            print("=" * 50)

            if DEBUG:
                print(f"🔧 Debug mode enabled - request logs will be shown")

            # Auto-open browser if requested
            if not args.no_browser:
                print("🌐 Opening browser...")
                webbrowser.open(server_url)

            # Start the server
            print("\n🚀 Starting server...")
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ Error: Port {args.port} is already in use.")
            print("Try running with a different port: --port 3001")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
