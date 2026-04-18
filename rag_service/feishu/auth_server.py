"""
Simple local server to handle OAuth callback.
Run this first, then open the authorization URL.
"""
import os
import sys
import json
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = Path.home() / ".feishu_token"
REDIRECT_URI = "http://localhost:8080/callback"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle OAuth callback"""
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if "code" in query:
            code = query["code"][0]
            print(f"\nGot code: {code[:30]}...")

            # Exchange code for token
            try:
                from feishu.oauth import get_oauth
                oauth = get_oauth()
                token_data = oauth.exchange_code_for_token(code)

                # Save token
                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_data, f, indent=2)

                print(f"Token saved to: {TOKEN_FILE}")
                print(f"access_token: {token_data.get('access_token', '')[:30]}...")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<html><body><h1>Success! Close this window.</h1></body></html>".encode("utf-8"))
            except Exception as e:
                print(f"Token get failed: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<html><body><h1>Error: {e}</h1></body></html>".encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<html><body><h1>No code in URL</h1></body></html>".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_server(port=8080):
    """Start the callback server"""
    server = HTTPServer(("", port), Handler)
    print(f"Server started, waiting for callback...")
    print(f"Listening on port: {port}")
    print("Open the auth URL in browser, token will be saved automatically")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
