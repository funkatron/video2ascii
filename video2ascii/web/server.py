"""Web server entry point."""

import sys
import webbrowser
from threading import Timer

try:
    import uvicorn
    from video2ascii.web.app import app
except ImportError:
    print("Error: Web dependencies not installed.", file=sys.stderr)
    print("Install with: uv pip install -e '.[web]' or pip install -e '.[web]'", file=sys.stderr)
    sys.exit(1)


def main(port: int = 9999):
    """Start the web server."""
    url = f"http://localhost:{port}"

    # Open browser after a short delay
    def open_browser():
        webbrowser.open(url)

    Timer(1.5, open_browser).start()

    print(f"Starting video2ascii web GUI...")
    print(f"Open your browser to: {url}")
    print("Press Ctrl+C to stop the server")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
