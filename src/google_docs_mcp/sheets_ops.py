"""Pure-Python operations against the Google Sheets API.

Kept separate from the MCP server layer so the CLI harness and the tool
handlers can share the same code, and so tests can exercise them without
touching MCP transport.

Scope is deliberately small: read a range, overwrite a range, append a row,
create a tab, create a spreadsheet. Nothing here clears a range or deletes
anything. A tool that can blank a tracker will one day blank a tracker;
create cannot destroy anything, so the line is at delete, not at create.
"""

from __future__ import annotations

from typing import Iterable

# USER_ENTERED means a value typed like `2026-09-02` is parsed as a date and
# `=A1+1` as a formula, the way it would be if a person typed it into the UI.
# Using RAW here would store everything as literal strings and break trackers
# that rely on date sorting or formulas.
_VALUE_INPUT_OPTION = "USER_ENTERED"


def get_range(service, spreadsheet_id: str, range_: str) -> str:
    """Return the rows in an A1 range as tab-separated lines, one per row.

    Range example: `Targets!A1:Z60`. Blank trailing cells in a row are not
    padded — the Sheets API omits them. Callers that need a rectangular grid
    should pass an explicit range and pad on their side.
    """
    if not range_:
        raise ValueError("`range` must be a non-empty A1 reference.")
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_)
        .execute()
    )
    rows = response.get("values", [])
    return "\n".join("\t".join(str(cell) for cell in row) for row in rows)


def update_range(
    service,
    spreadsheet_id: str,
    range_: str,
    values: Iterable[Iterable[object]],
) -> int:
    """Overwrite the given A1 range with `values`. Returns cells updated.

    `values` is a list of rows (list of lists). The range must be large
    enough for the values; excess cells in the range are left untouched by
    the API.
    """
    if not range_:
        raise ValueError("`range` must be a non-empty A1 reference.")
    body = {"values": [list(row) for row in values]}
    if not body["values"]:
        raise ValueError("`values` must contain at least one row.")
    response = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption=_VALUE_INPUT_OPTION,
            body=body,
        )
        .execute()
    )
    return int(response.get("updatedCells", 0) or 0)


def append_row(
    service,
    spreadsheet_id: str,
    sheet_name: str,
    values: Iterable[object],
) -> str:
    """Append one row to the end of a named tab. Returns the range it landed in.

    Uses insertDataOption=INSERT_ROWS so an existing row below the table is
    pushed down instead of overwritten. If `sheet_name` does not exist the
    Sheets API returns a 400; we surface that error unchanged. This function
    never creates a tab.
    """
    if not sheet_name:
        raise ValueError("`sheet_name` must be a non-empty string.")
    row = list(values)
    if not row:
        raise ValueError("`values` must contain at least one cell.")
    response = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption=_VALUE_INPUT_OPTION,
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        )
        .execute()
    )
    updates = response.get("updates", {})
    return str(updates.get("updatedRange", ""))


def create_tab(service, spreadsheet_id: str, title: str) -> tuple[int, str]:
    """Add a new tab to an existing spreadsheet. Returns (sheetId, title).

    Fails 400 if a tab with `title` already exists — the API surfaces this;
    we do not rename or suffix, and we do not swallow it.
    """
    if not title:
        raise ValueError("`title` must be a non-empty string.")
    request = {"addSheet": {"properties": {"title": title}}}
    response = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [request]})
        .execute()
    )
    replies = response.get("replies", [])
    if not replies:
        raise RuntimeError("addSheet returned no replies.")
    props = replies[0].get("addSheet", {}).get("properties", {})
    sheet_id = int(props.get("sheetId", 0))
    returned_title = str(props.get("title", title))
    return sheet_id, returned_title


def create_spreadsheet(service, title: str) -> tuple[str, str]:
    """Create a new spreadsheet in Drive root. Returns (spreadsheetId, URL).

    The `spreadsheets` scope cannot place the file in a folder — moving it
    is the Drive connector's job (`update_file` with `parentId`). We do not
    add the Drive scope here just for that; one more scope is one more
    consent screen, and the connector already covers this.
    """
    if not title:
        raise ValueError("`title` must be a non-empty string.")
    response = (
        service.spreadsheets()
        .create(body={"properties": {"title": title}}, fields="spreadsheetId,spreadsheetUrl")
        .execute()
    )
    return str(response.get("spreadsheetId", "")), str(response.get("spreadsheetUrl", ""))
