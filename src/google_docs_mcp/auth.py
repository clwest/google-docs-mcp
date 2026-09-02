"""OAuth for the Google Docs and Google Sheets APIs.

Token and client_secret live in ~/.config/google-docs-mcp/ — never inside the
repo. `.gitignore` also blocks credential-shaped names in the project tree, so
even if someone forgets that rule the commit won't include them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# `documents` and `spreadsheets` are deliberate. `drive.file` only sees files
# the app itself created, which defeats the point of an "edit an existing
# document / spreadsheet" server. The README says plainly that this grants
# read/write to all of the user's Google Docs AND Sheets — that trade-off is
# real, name it, don't hide it.
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

CONFIG_DIR = Path(
    os.environ.get("GOOGLE_DOCS_MCP_CONFIG_DIR")
    or (Path.home() / ".config" / "google-docs-mcp")
)
CLIENT_SECRET_PATH = CONFIG_DIR / "client_secret.json"
TOKEN_PATH = CONFIG_DIR / "token.json"


class AuthError(RuntimeError):
    """Raised when the OAuth setup on disk is missing or unusable."""


def _load_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write_token(creds)
        return creds
    return None


def _write_token(creds: Credentials) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)


def authorize_interactive() -> Credentials:
    """Run the OAuth consent flow. Requires a browser; use once at setup."""
    if not CLIENT_SECRET_PATH.exists():
        raise AuthError(
            f"client_secret.json not found at {CLIENT_SECRET_PATH}. "
            "See README section 'One-time setup'."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
    # Desktop InstalledAppFlow always yields OAuth user credentials; the
    # union return type covers the workforce-identity case that can't
    # happen here.
    creds = cast(Credentials, flow.run_local_server(port=0))
    _write_token(creds)
    return creds


def get_credentials() -> Credentials:
    """Return usable credentials or raise AuthError with a clear message.

    Never triggers a browser flow — the MCP server runs headless under
    Claude Desktop / Claude Code. First-time consent has to happen in the
    CLI harness (`google-docs-mcp-cli auth`).

    A token stored before the Sheets scope was added will load with only
    the Docs scope, and every Sheets call will fail 403 until
    `google-docs-mcp-cli auth` is re-run.
    """
    creds = _load_credentials()
    if creds is None:
        raise AuthError(
            "No usable token. Run `google-docs-mcp-cli auth` once from a "
            "shell to complete the OAuth consent flow."
        )
    return creds


def _build_service(api_name: str, api_version: str):
    """Build a Google API client with cached OAuth credentials.

    cache_discovery=False avoids a noisy warning under Python 3.11+ about the
    file-based discovery cache; there is no benefit to it here.
    """
    creds = get_credentials()
    return build(api_name, api_version, credentials=creds, cache_discovery=False)


def get_docs_service():
    """Build a Google Docs API client."""
    return _build_service("docs", "v1")


def get_sheets_service():
    """Build a Google Sheets API client."""
    return _build_service("sheets", "v4")
