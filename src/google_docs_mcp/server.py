"""MCP server: docs_get, docs_replace_text, docs_append_text.

Notes for future readers:

  1. This uses the mcp>=2 MCPServer API (`mcp.server.mcpserver`). FastMCP
     was removed at 2.0. Don't paste a pre-2.0 example in here.

  2. Every tool is declared with `structured_output=False`. That is not a
     style choice — the Claude desktop app on macOS (bug
     anthropics/claude-code#80094, filed 2026-07-22) will not dispatch
     tool calls for tools that publish an outputSchema. Once that bug is
     fixed, structured_output can be removed here.

  3. Return values are strings. Callers get plain text; no output schema
     is inferred by the SDK when structured_output is False.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import __version__
from .auth import AuthError, get_docs_service
from .docs_ops import append_text, get_document_text, replace_all_text

server: MCPServer = MCPServer(
    name="google-docs",
    version=__version__,
    instructions=(
        "Read and edit the body of an existing Google Doc. "
        "Requires OAuth consent (run `google-docs-mcp-cli auth` once)."
    ),
)


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, AuthError):
        return f"Auth error: {exc}"
    return f"{exc.__class__.__name__}: {exc}"


@server.tool(
    name="docs_get",
    description=(
        "Return the plain-text body of a Google Doc. "
        "Argument `document_id` is the ID in the doc's URL "
        "(https://docs.google.com/document/d/<document_id>/edit)."
    ),
    structured_output=False,  # see module docstring
)
def docs_get(document_id: str) -> str:
    """Fetch document body text."""
    try:
        service = get_docs_service()
        return get_document_text(service, document_id)
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="docs_replace_text",
    description=(
        "Replace every occurrence of `find` with `replace` in the given "
        "Google Doc. `match_case` defaults to true. Returns the number of "
        "occurrences changed. WARNING: there is no undo through the API."
    ),
    structured_output=False,  # see module docstring
)
def docs_replace_text(
    document_id: str,
    find: str,
    replace: str,
    match_case: bool = True,
) -> str:
    """Replace all matches of `find` with `replace`."""
    try:
        service = get_docs_service()
        count = replace_all_text(service, document_id, find, replace, match_case)
        return f"Replaced {count} occurrence(s)."
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="docs_append_text",
    description=(
        "Append `text` at the end of the Google Doc's body. Include a "
        "leading newline in `text` if you want it on its own line."
    ),
    structured_output=False,  # see module docstring
)
def docs_append_text(document_id: str, text: str) -> str:
    """Append text to the end of the document body."""
    try:
        service = get_docs_service()
        end_index = append_text(service, document_id, text)
        return f"Appended {len(text)} character(s) at index {end_index}."
    except Exception as exc:
        return _friendly_error(exc)


def run() -> None:
    """Entry point for the MCP server (stdio transport)."""
    server.run(transport="stdio")
