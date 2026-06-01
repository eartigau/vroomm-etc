"""Serve the VROOMM ETC using waitress (no tty issues, works as background process)."""
from waitress import serve
from app import app

if __name__ == "__main__":
    print("VROOMM ETC running at http://127.0.0.1:5050")
    serve(app, host="127.0.0.1", port=5050)
