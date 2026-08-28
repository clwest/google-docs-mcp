"""Module entry point so `python -m google_docs_mcp` runs the server."""

from .server import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
