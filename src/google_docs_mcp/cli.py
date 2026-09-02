"""CLI harness for local smoke testing.

Not required for the MCP server to work; this is what you run against a
throwaway document or spreadsheet to make sure the plumbing is right before
letting Claude touch a real one.
"""

from __future__ import annotations

import argparse
import sys

from .auth import authorize_interactive, get_docs_service, get_sheets_service
from .docs_ops import append_text, get_document_text, replace_all_text
from .sheets_ops import append_row, get_range, update_range


def _cmd_auth(_args: argparse.Namespace) -> int:
    creds = authorize_interactive()
    print(f"OK. Token written. Valid for scopes: {creds.scopes}")
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    service = get_docs_service()
    text = get_document_text(service, args.document_id)
    print(text, end="")
    return 0


def _cmd_replace(args: argparse.Namespace) -> int:
    service = get_docs_service()
    count = replace_all_text(
        service,
        args.document_id,
        args.find,
        args.replace,
        match_case=not args.ignore_case,
    )
    print(f"Replaced {count} occurrence(s).")
    return 0


def _cmd_append(args: argparse.Namespace) -> int:
    service = get_docs_service()
    end_index = append_text(service, args.document_id, args.text)
    print(f"Appended {len(args.text)} character(s) at index {end_index}.")
    return 0


def _cmd_sheets_get(args: argparse.Namespace) -> int:
    service = get_sheets_service()
    text = get_range(service, args.spreadsheet_id, args.range)
    print(text)
    return 0


def _cmd_sheets_update(args: argparse.Namespace) -> int:
    # Values are passed as one row per --row flag, cells split on tab.
    # e.g. --row "Wayne Reaves\tReplied\t2026-09-02"
    if not args.row:
        raise SystemExit("At least one --row is required.")
    rows = [row.split("\t") for row in args.row]
    service = get_sheets_service()
    count = update_range(service, args.spreadsheet_id, args.range, rows)
    print(f"Updated {count} cell(s).")
    return 0


def _cmd_sheets_append(args: argparse.Namespace) -> int:
    service = get_sheets_service()
    landed = append_row(service, args.spreadsheet_id, args.sheet_name, args.value)
    print(f"Appended 1 row at {landed}." if landed else "Appended 1 row.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="google-docs-mcp-cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth", help="Run one-time OAuth consent flow.").set_defaults(
        func=_cmd_auth
    )

    p_get = sub.add_parser("get", help="Print document body text.")
    p_get.add_argument("document_id")
    p_get.set_defaults(func=_cmd_get)

    p_rep = sub.add_parser("replace", help="Replace all occurrences of text.")
    p_rep.add_argument("document_id")
    p_rep.add_argument("find")
    p_rep.add_argument("replace")
    p_rep.add_argument("--ignore-case", action="store_true")
    p_rep.set_defaults(func=_cmd_replace)

    p_app = sub.add_parser("append", help="Append text at end of body.")
    p_app.add_argument("document_id")
    p_app.add_argument("text")
    p_app.set_defaults(func=_cmd_append)

    p_sget = sub.add_parser("sheet-get", help="Print rows in an A1 range.")
    p_sget.add_argument("spreadsheet_id")
    p_sget.add_argument("range", help="A1 range, e.g. Targets!A1:D3")
    p_sget.set_defaults(func=_cmd_sheets_get)

    p_supd = sub.add_parser("sheet-update", help="Overwrite an A1 range.")
    p_supd.add_argument("spreadsheet_id")
    p_supd.add_argument("range", help="A1 range, e.g. scratch!A1")
    p_supd.add_argument(
        "--row",
        action="append",
        default=[],
        help='One row, cells joined by tabs. Repeat for multiple rows.',
    )
    p_supd.set_defaults(func=_cmd_sheets_update)

    p_sapp = sub.add_parser("sheet-append", help="Append one row to a tab.")
    p_sapp.add_argument("spreadsheet_id")
    p_sapp.add_argument("sheet_name", help="Tab name, e.g. scratch")
    p_sapp.add_argument("value", nargs="+", help="One argument per cell.")
    p_sapp.set_defaults(func=_cmd_sheets_append)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
