# google-docs-mcp

An MCP server that reads and edits the body of an existing Google Doc,
and reads and writes cells in an existing Google Sheet.

The Google Drive connector shipped with Claude can search, read, create,
copy, rename, and trash files — but it **cannot edit the contents of an
existing Doc or Sheet**. This server fills that one gap. Nothing more.

## What it exposes

Six tools. That's the whole surface.

| Tool | What it does |
|---|---|
| `docs_get` | Return the plain-text body of a Google Doc. |
| `docs_replace_text` | Replace every occurrence of a string in the doc. Returns how many were replaced. |
| `docs_append_text` | Append text at the end of the document body. |
| `sheets_get_range` | Return the rows in an A1 range of a Sheet as tab-separated lines. |
| `sheets_update_range` | Overwrite an A1 range with a list of rows. Returns how many cells were updated. |
| `sheets_append_row` | Append one row to the end of a named tab. Returns the range it landed in. |

Not in this server: formatting, tables, images, comments, suggestions,
creating Docs or Sheets (use the Drive connector), deleting Docs or
Sheets, clearing or deleting rows, tabs or spreadsheets, and creating
tabs (do that in the UI). A tool that can blank a tracker will one day
blank a tracker; those tools deliberately do not exist here.

## What it is allowed to do to your account

This server holds an OAuth token with two scopes:
`https://www.googleapis.com/auth/documents` and
`https://www.googleapis.com/auth/spreadsheets`. Together that is
**read/write to all of your Google Docs AND all of your Google Sheets,
not just ones this app made.**

The narrower `drive.file` scope only sees files the app itself created,
which defeats the point of an "edit an existing document / spreadsheet"
tool. So the choice is: full Docs and Sheets access, or a tool that
can't do what it's for. This server picks the first option deliberately.
The token lives on your machine in
`~/.config/google-docs-mcp/token.json` — revoke access at
<https://myaccount.google.com/permissions> any time.

`replaceAllText` (Docs) and `values.update` (Sheets) are batch API
calls and there is no undo through the API. Test on a throwaway
document or a scratch tab before running against anything you care
about.

## One-time setup

### 1. Google Cloud project + Docs & Sheets APIs

1. Open <https://console.cloud.google.com/>.
2. Create a project (or reuse one). Name doesn't matter to Google.
3. **APIs & Services → Library** → enable **Google Docs API** and
   **Google Sheets API**. Both are needed.
4. **APIs & Services → OAuth consent screen** → User Type: External,
   fill in the name + your email, save. You do **not** need to submit
   for verification for personal use — add your Google account under
   "Test users" instead.
5. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID → Application type: Desktop app**. Name it whatever. Download the
   JSON.

### 2. Drop the client secret into ~/.config

```
mkdir -p ~/.config/google-docs-mcp
mv ~/Downloads/client_secret_*.json ~/.config/google-docs-mcp/client_secret.json
chmod 600 ~/.config/google-docs-mcp/client_secret.json
```

The server looks for exactly `client_secret.json` at that path.

### 3. Install and authorize

```
cd ~/Donkey_Betz/mcp-servers/google-docs-mcp
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -e .
google-docs-mcp-cli auth
```

The last step opens a browser, asks you to sign in and grant Docs and
Sheets access, then writes `~/.config/google-docs-mcp/token.json`. That
token refreshes itself; you shouldn't need to do this again unless the
set of scopes changes (as it did on 2026-09-02 when Sheets was added).

## Registering the server

Claude Desktop and Claude Code keep separate MCP configuration. Register
in both if you want both to see the server.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
and add an entry under `mcpServers` (back the file up first):

```json
{
  "mcpServers": {
    "google-docs": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "google_docs_mcp"]
    }
  }
}
```

Use the absolute path to the venv's Python — the desktop app does not
load your shell profile, so `python` alone often isn't on PATH. Then
fully quit the app (Cmd+Q) and reopen. Logs are at
`~/Library/Logs/Claude/mcp-server-google-docs.log`.

### Claude Code

This one goes at **user scope** (account-wide, not per-repo):

```
claude mcp add --scope user --transport stdio google-docs -- \
  /absolute/path/to/.venv/bin/python -m google_docs_mcp
```

Verify with `claude mcp list` — expect a `Connected` marker.

## Using it

`document_id` and `spreadsheet_id` are the ugly strings in the URL,
between `/d/` and `/edit`. So for
`https://docs.google.com/document/d/1abc...XYZ/edit` the ID is
`1abc...XYZ`; same shape for spreadsheets.

Docs:

- **Read**: "Read the doc `1abc...XYZ`."
- **Fix a typo**: "In doc `1abc...XYZ`, replace `teh` with `the`."
- **Append**: "In doc `1abc...XYZ`, append `\n\nSigned off 2026-08-28.`"

`docs_replace_text` matches every occurrence. If you want to replace
one specific occurrence, give it a longer surrounding string that is
already unique in the doc.

Sheets:

- **Read a range**: "Get `Targets!A1:D10` from spreadsheet `1abc...XYZ`."
- **Overwrite one cell**: "In spreadsheet `1abc...XYZ`, set `Targets!C7`
  to `Replied`."  (`values` = `[["Replied"]]`)
- **Append a row**: "In spreadsheet `1abc...XYZ`, append a row to
  `Targets` with `Wayne Reaves`, `Emailed`, `2026-09-02`."

The tab name in a range is separated from the A1 reference by `!`
(`Targets!A1`). `sheets_append_row` takes the tab name on its own, not
a range. If a tab does not exist, the Sheets API returns an error and
nothing is created — create the tab in the UI first.

## CLI harness

For local testing without going through MCP transport:

```
google-docs-mcp-cli auth                                          # one-time OAuth
google-docs-mcp-cli get <document_id>
google-docs-mcp-cli replace <document_id> <find> <replace>
google-docs-mcp-cli append <document_id> <text>
google-docs-mcp-cli sheet-get <spreadsheet_id> <A1_range>
google-docs-mcp-cli sheet-update <spreadsheet_id> <A1_range> --row "cell1\tcell2" [--row ...]
google-docs-mcp-cli sheet-append <spreadsheet_id> <tab_name> cell1 cell2 ...
```

This is the recommended way to smoke-test against a throwaway doc or a
scratch tab before letting Claude touch a real one.

## Design decisions worth knowing

- **No `outputSchema` on any tool.** There is an open bug in Claude
  Desktop (`anthropics/claude-code#80094`, 2026-07-22) that prevents
  tool dispatch when tools publish an outputSchema. Every tool here
  passes `structured_output=False`. When that bug ships a fix, that
  flag can be removed.
- **`mcp>=2,<3`**. FastMCP was removed at 2.0. If you find an older
  example using `mcp.server.fastmcp`, it will not work on 2.x.
- **Token in `~/.config`, not the repo.** The `.gitignore` also blocks
  credential-shaped filenames project-wide, so even a mistake in a
  future PR shouldn't leak.

## When something breaks

- `Auth error: No usable token.` → run `google-docs-mcp-cli auth`.
- `HttpError 403: The caller does not have permission` → the Google
  account you authorized with doesn't have edit rights on that doc.
- `HttpError 429` → Google rate limit; back off and retry.
- Tool doesn't show up in Claude Desktop → check the log file listed
  above; a common cause is `command` pointing at a Python that can't
  import the package.

## What this depends on

- Google Docs API v1 and Google Sheets API v4 — Google-managed,
  occasionally shift.
- OAuth client you created — if it gets deleted or the project is
  disabled, this server stops working until you re-do §1.
- Python MCP SDK 2.x — broke compatibility with FastMCP at 2.0; assume
  it will change again.

See `docs/CASE_STUDY.md` for what these dependencies imply for anyone
running this server long-term.
