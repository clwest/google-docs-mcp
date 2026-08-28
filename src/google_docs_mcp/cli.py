"""CLI harness for local smoke testing.

Not required for the MCP server to work; this is what you run against a
throwaway document to make sure the plumbing is right before letting
Claude touch a real doc.
"""

from __future__ import annotations

import argparse
import sys

from .auth import authorize_interactive, get_docs_service
from .docs_ops import append_text, get_document_text, replace_all_text


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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
