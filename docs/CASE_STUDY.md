# Case study — the Google Docs MCP server

> Written for someone who has never used Claude Code or MCP.
> Purpose: a worked example of "when a customer actually needs a custom
> MCP server," and — more importantly — what taking that job on obliges
> the builder to keep doing.

## What the customer wanted

One line in a Google Doc was wrong. They wanted Claude to fix that
line, in place, without changing the document's link. They already had
Claude connected to their Google Drive.

That was the whole ask.

## Why the existing connector could not do it

The Google Drive connector shipped with Claude can search, read,
create, copy, rename, and trash files. Its "update" tool only changes
a file's **title and folder** — not its content.

There is no separate Google Docs connector. So editing the body of an
already-existing document is a gap in the out-of-the-box tooling.

## The three non-custom alternatives, and why each was rejected

1. **Ask Claude to recreate the doc and delete the old one.** Works,
   but the URL changes. Any link the customer has already shared —
   over email, in Slack, in another document — silently rots. That is
   the workaround they had used earlier the same day, and the reason
   this task existed.

2. **Ask Claude to paste the corrected text and let the customer edit
   by hand.** This is not automation; it is a slower version of what
   the customer would have done without Claude in the first place.

3. **Use `drive.file` scope + Drive API `files.update` with a media
   upload.** The `drive.file` OAuth scope only sees files the app
   itself created. Every existing document in the customer's Drive
   would be invisible to a server using that scope, which is exactly
   the class of document the customer needs to edit. So this option
   collapses on the first real request.

None of these were good enough. That is what made it a genuine
custom-build case rather than a workflow-tuning problem.

## What building the custom piece actually took

**Elapsed time:** about ninety minutes, wall-clock. Roughly half of
that was Google Cloud console navigation and pasted-command debugging;
the actual server code took ~30 minutes.

**What went wrong along the way:**

- **First `mv` command failed** because the terminal wrapped a
  multi-line paste and `mv` got no target. Fix: a single-line command,
  and later a `bin/gdocs` wrapper script so nothing longer than
  `bin/gdocs auth` needed to be pasted.
- **`source .venv/bin/activate` failed** for the same wrap reason;
  same wrapper script sidesteps it entirely.
- **Two design decisions had to be baked in from the start** because
  each had cost someone hours on this same machine within the past
  eight weeks:
  - MCP Python SDK 2.0 removed `mcp.server.fastmcp`. Any example
    written before mid-2026 is now wrong. The server declares
    `mcp>=2,<3` and uses `mcp.server.mcpserver.MCPServer`.
  - Claude Desktop on macOS has an open bug
    (`anthropics/claude-code#80094`, filed 2026-07-22) that refuses to
    dispatch tool calls when a tool publishes an `outputSchema`. Every
    tool in this server is declared with `structured_output=False`.
    There is a comment in the code pointing at the bug so a future
    reader knows why and can remove the workaround once it ships.
- **The Google OAuth "unverified app" warning surprised no one who
  has seen it before, and surprises everyone else.** For a personal
  Desktop client that will only ever be used by its author it is safe
  to click through, but a customer would have to be walked through it
  the first time.

**What did not go wrong** (and is worth noting because it is why the
scope stayed tight): the three tools — `docs_get`,
`docs_replace_text`, `docs_append_text` — mapped cleanly to Google
Docs API primitives, needed no cleverness, and were done in one pass.
`replaceAllText` in particular is a batchUpdate call that takes one
find string and one replace string; the whole "fix a typo without
rebuilding the doc" story is that single API call.

## The acceptance test

Written before the build, so it could not be quietly softened
afterwards. From `TASK_build-google-docs-mcp.md`:

> The document "Setup as a Service — scoping, honestly (untested)" in
> Drive at `01 — Business / Donkey Betz / 02 — Consulting / Solution
> Experiments` (fileId `1rldRAZic9QxRjOeltAb8SBPEFoVLkv1SWWjpzNhdDTk`)
> contains the line:
>
>     Status: UNTESTED. Nobody has paid for this. No one has been asked.
>
> The build succeeds if that line can be edited in place, from a
> chat, without the document's URL changing.

**Result: pass.** The line was edited via `docs_replace_text` on
2026-08-28. One occurrence replaced. The word "UNTESTED" was
deliberately preserved (the customer's call — the status is honest
and should stay honest). Same fileId, same URL, before and after.

## What it would cost a customer

At a build-only price, this is a **half-day engagement**. Not because
the code is complex — it is under 300 lines — but because the
irreducible parts are:

- Google Cloud project setup with them at their keyboard (they own it).
- OAuth consent screen configuration, including honest disclosure of
  the scope this server holds (read/write to all of their Google
  Docs).
- Walking them through the "unverified app" browser warning the first
  time.
- Installing the server, registering it in **both** Claude Desktop and
  Claude Code (those do not share configuration), and verifying the
  tools show up in a live chat.
- Writing the customer-facing README so the person who authorized the
  OAuth can revoke it, rotate the token, or hand it to someone else
  without calling us.

Half a day is the honest number. Quoting less means either eating the
setup time or shipping without the OAuth walk-through, and both of
those defer the cost onto the customer.

## What it obliges us to keep doing — this is the commercial part

This server depends on three moving pieces that we do not control:

1. **Google Docs API v1.** Google has, historically, deprecated
   endpoints on 12-month notice and moved required fields around
   without notice. Odds of a breaking change in the next 24 months:
   low but non-zero.
2. **The customer's OAuth client.** If the Google Cloud project is
   deleted, if billing gets disabled, if the consent screen falls out
   of "testing" mode past its 6-month window, or if the customer's
   admin removes the app from workspace-approved apps, the server
   stops working. The customer will not know why.
3. **Python MCP SDK.** Broke compatibility at 2.0 (six weeks before
   this was written). Assume it will happen again — the ecosystem is
   young.

So the customer is buying, in effect, a small piece of custom
software with three upstream dependencies that can break it without
warning. Three realistic scenarios:

- **"It stopped working."** Most common. Usually a refresh-token
  expiry, a scope change on Google's side, or the SDK upgrading past
  a compatible version because a `pip install --upgrade` ran.
  Diagnosis: 15–60 minutes. Fix: usually the same.
- **"Google renamed a field."** Rare, but every API-dependent server
  eventually hits one. Diagnosis: check the API changelog. Fix: one
  code change, maybe an hour.
- **"The MCP SDK broke again."** This is the scariest one because it
  can take out multiple servers at once. Fix requires reading the SDK
  release notes and updating both the import and, occasionally, the
  tool-declaration style. A few hours if we are lucky.

**The honest way to price this is not build-only.** It is build +
either an hourly incident retainer (customer eats the risk) or a flat
monthly fix-forward retainer (we eat the risk). Anything else is a
promise to fix things in perpetuity, unpaid, out of guilt.

For internal use — the case this specific server was built for — we
are the customer, we accept the risk, and the maintenance is folded
into normal engineering time. That works precisely because there is
one user, one authorizing account, and one machine. It does not scale
to "we sold this to five people."

## What we learned that the task file did not predict

- **The paste-wrap problem** was surprising in how much friction it
  added. Multi-line commands with `&&` chains and `source` calls are
  fragile in ways that don't show up when the developer types them
  themselves. `bin/gdocs` (six-line wrapper script) removed almost
  all of that friction. A production version of this project should
  ship with the wrapper by default.
- **The "unverified app" screen** is the single most likely place a
  non-technical customer will bail out. The README documents the
  click-through path, but a real customer engagement would benefit
  from a screenshot or a short screen-recording of that step.
- **Testing the MCP transport separately from the CLI harness matters.**
  Both were exercised on the throwaway document before touching
  anything real. Skipping the stdio round-trip test would have deferred
  the discovery of any transport issue to the moment the desktop app
  was reloaded, which is the worst place to debug it.

## When to reach for this pattern again

Only when all three of the following are true:

1. The customer's ask requires a specific API call that no existing
   connector makes.
2. The workaround costs the customer something they care about
   (URL stability, format fidelity, third-party integrations, etc.).
3. The API in question is documented, stable, and has a Python
   client.

If any of those is false, the answer is probably to configure a
workflow, not to write a server.

## Postscript — 2026-09-02, the Sheets half of the same gap

Five days after the Docs work landed, the same shape of problem hit
Sheets. A row in the "Remote_Sales_Target_List (CURRENT — tracker)"
Sheet needed to be marked `Replied` and one new row added. The stock
Drive connector could not do it; every previous "update" of a tracker
Sheet had actually rebuilt the file and re-uploaded it, and on
2026-08-31 that mechanism produced four duplicate copies of an
engineering tracker in Drive root before anyone noticed.

**The wrong first move**, worth recording so it does not recur: when
the cell write failed, the built-in browser pane in the Claude desktop
app got reached for. That pane is signed out of every Google account
and asking for a password across a chat is not the model. It stopped at
an account picker. The right tool was this server; nothing external.

**What the fix cost.** One session. Three tools added
(`sheets_get_range`, `sheets_update_range`, `sheets_append_row`), one
file (`sheets_ops.py`), one refactor to share credential loading
between Docs and Sheets, one scope added to `SCOPES`. Total server
surface went from three tools to six on the same OAuth token. Nothing
renamed, nothing moved.

Two human steps, not one — a lesson caught the first time the new
`sheets_get_range` was called and came back with `SERVICE_DISABLED`.
The OAuth re-consent flow was the obvious human step (add the
`spreadsheets` scope to the token), so it was the only one written
into the brief. But **enabling the Sheets API on the Cloud project is
a separate act**, and Google will not do either implicitly. Any future
"add API X to this server" task needs to name both.

**What was deliberately not built.** `sheets_clear_range`,
`sheets_delete_row`, `sheets_delete_tab`, `sheets_create_spreadsheet`,
`sheets_create_tab`. A tool that can blank a tracker will one day blank
a tracker; the workflow does not need any of them, and their absence is
now written into the README as a promise, not an omission.

**The wider point for the offer.** Two worked examples now sit under
"you might not need anything more than a Claude subscription and a
Drive." Search, read, create, move, share — Drive connector. Edit the
body of a Doc that already exists — this server, three tools,
`google-docs-mcp` on 2026-08-28. Edit cells in a Sheet that already
exists — this server, three more tools, same day-of-work extension on
2026-09-02. The pattern: most of Drive works out of the box, editing
what already exists needs one small custom piece per file type, and
that piece stays small because deleting and creating live in the
existing tools.

**The "no create" rule turned out to be over-cautious.** The first
Sheets pass forbade creating tabs and spreadsheets alongside forbidding
delete and clear — one omnibus caution against "tools that can blank a
tracker." Later the same day the customer's own workflow needed a
tracker created and a scratch tab added, and the Drive connector could
not do either (it makes empty files but cannot add a tab to an
existing Sheet). Two more tools went in, `sheets_create_tab` and
`sheets_create_spreadsheet` — no new scope, no re-consent. The line
now sits at delete, not at create: **create cannot destroy anything,
so the caution doesn't apply.** Same server, eight tools. If a future
"can we add X" question comes up, the test is not "could this cause
harm in the abstract" but "could this destroy an existing value the
customer cares about." Create doesn't; delete and clear do.
