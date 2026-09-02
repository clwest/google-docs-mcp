"""MCP server: three Docs tools and five Sheets tools on one credential.

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

  4. Sheets tools deliberately do not clear ranges or delete anything —
     no delete_tab, no delete_spreadsheet, no clear_range, no delete_rows.
     A tool that can blank a tracker will one day blank a tracker. Create
     is in (2026-09-02 Item 4): create cannot destroy anything, so the
     line moved to delete, not create. See sheets_ops.py for the reasoning.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import __version__
from .auth import AuthError, get_docs_service, get_sheets_service
from .docs_ops import append_text, get_document_text, replace_all_text
from .sheets_ops import (
    append_row,
    create_spreadsheet,
    create_tab,
    get_range,
    update_range,
)

server: MCPServer = MCPServer(
    name="google-docs",
    version=__version__,
    instructions=(
        "Read and edit the body of an existing Google Doc, and read/write "
        "cells in an existing Google Sheet. Requires OAuth consent "
        "(run `google-docs-mcp-cli auth` once)."
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


@server.tool(
    name="sheets_get_range",
    description=(
        "Return the rows in an A1 range of a Google Sheet as tab-separated "
        "lines, one row per line. `spreadsheet_id` is the ID in the sheet's "
        "URL. `range` is an A1 reference like `Targets!A1:Z60`."
    ),
    structured_output=False,  # see module docstring
)
def sheets_get_range(spreadsheet_id: str, range: str) -> str:  # noqa: A002 - matches API vocabulary
    """Fetch a range of cells."""
    try:
        service = get_sheets_service()
        return get_range(service, spreadsheet_id, range)
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="sheets_update_range",
    description=(
        "Overwrite the given A1 range with `values`. `values` is a list of "
        "rows (each row a list of strings). Values are parsed the way the "
        "UI would parse a typed entry: `2026-09-02` becomes a date. Returns "
        "the number of cells updated. WARNING: there is no undo through the "
        "API — this overwrites cells in place."
    ),
    structured_output=False,  # see module docstring
)
def sheets_update_range(
    spreadsheet_id: str,
    range: str,  # noqa: A002 - matches API vocabulary
    values: list[list[str]],
) -> str:
    """Overwrite a range of cells."""
    try:
        service = get_sheets_service()
        count = update_range(service, spreadsheet_id, range, values)
        return f"Updated {count} cell(s)."
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="sheets_append_row",
    description=(
        "Append one row to the end of a named tab in a Google Sheet. "
        "`sheet_name` is the tab name (e.g. `Targets`), NOT an A1 range. "
        "`values` is a list of strings, one per cell. Returns the A1 range "
        "the row landed in. Does not create the tab if it is missing — use "
        "`sheets_create_tab` for that."
    ),
    structured_output=False,  # see module docstring
)
def sheets_append_row(
    spreadsheet_id: str,
    sheet_name: str,
    values: list[str],
) -> str:
    """Append one row to a tab."""
    try:
        service = get_sheets_service()
        landed = append_row(service, spreadsheet_id, sheet_name, values)
        return f"Appended 1 row at {landed}." if landed else "Appended 1 row."
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="sheets_create_tab",
    description=(
        "Add a new tab (worksheet) to an existing Google Sheet. `title` is "
        "the tab name. Fails with the API's error if a tab with that title "
        "already exists — no renaming, no suffixing. Returns the new tab's "
        "sheetId and title."
    ),
    structured_output=False,  # see module docstring
)
def sheets_create_tab(spreadsheet_id: str, title: str) -> str:
    """Create a new tab."""
    try:
        service = get_sheets_service()
        sheet_id, returned = create_tab(service, spreadsheet_id, title)
        return f"Created tab '{returned}' (sheetId={sheet_id})."
    except Exception as exc:
        return _friendly_error(exc)


@server.tool(
    name="sheets_create_spreadsheet",
    description=(
        "Create a new Google Sheet in Drive root. `title` is the file name. "
        "Returns the new spreadsheet's id and URL. The file lands in Drive "
        "root because the `spreadsheets` scope cannot place it in a folder; "
        "use the Drive connector's `update_file` with `parentId` to move it."
    ),
    structured_output=False,  # see module docstring
)
def sheets_create_spreadsheet(title: str) -> str:
    """Create a new spreadsheet."""
    try:
        service = get_sheets_service()
        spreadsheet_id, url = create_spreadsheet(service, title)
        return f"Created spreadsheet id={spreadsheet_id} url={url}"
    except Exception as exc:
        return _friendly_error(exc)


def run() -> None:
    """Entry point for the MCP server (stdio transport)."""
    server.run(transport="stdio")
