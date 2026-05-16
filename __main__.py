"""Allow running the package with `python -m magi` or `python -m magi --web`."""
import sys
import argparse
from pathlib import Path

# Ensure the parent of the magi/ package is on sys.path
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


def main():
    parser = argparse.ArgumentParser(
        prog="magi",
        description="MAGI Framework — Silverline Assembly Line Simulation",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the MAGI Dashboard web server instead of the CLI.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the web server to (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the web server (default: 8765).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the browser when starting the web server.",
    )

    # Parse known args only so the CLI can still pass its own flags through
    args, remaining = parser.parse_known_args()

    if args.web:
        _run_web(host=args.host, port=args.port, open_browser=not args.no_browser)
    else:
        # Original CLI path — pass remaining args back to argv
        sys.argv = [sys.argv[0]] + remaining
        from magi.cli import main as cli_main
        cli_main()


def _run_web(host: str, port: int, open_browser: bool) -> None:
    """Launch the FastAPI dashboard server."""
    import asyncio
    import threading
    import time
    import webbrowser

    import uvicorn
    from magi.meta.server import create_app

    app = create_app()

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)

    if open_browser:
        # Open after a short delay so the server has time to start
        def _open():
            time.sleep(1.5)
            url = f"http://{'localhost' if host in ('0.0.0.0', '127.0.0.1') else host}:{port}"
            print(f"\n  MAGI Dashboard: {url}\n")
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()

    server.run()


if __name__ == "__main__":
    main()
