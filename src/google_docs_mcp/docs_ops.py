"""Pure-Python operations against the Google Docs API.

Kept separate from the MCP server layer so the CLI harness and the tool
handlers can share the same code, and so tests can exercise them without
touching MCP transport.
"""

from __future__ import annotations

from typing import Any


def get_document_text(service, document_id: str) -> str:
    """Return the plain-text body of a Google Doc.

    Walks the document's structural elements and concatenates every
    textRun. Tables, images, footnotes etc. are ignored — v1 scope is
    body text only.
    """
    doc = service.documents().get(documentId=document_id).execute()
    parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for run in paragraph.get("elements", []):
            text_run = run.get("textRun")
            if text_run and "content" in text_run:
                parts.append(text_run["content"])
    return "".join(parts)


def get_document_end_index(service, document_id: str) -> int:
    """Return the index one past the final character in the body.

    Google Docs insertText needs a location; appending at end-of-body
    means index = (last element's endIndex) - 1. The trailing newline
    that Docs maintains at end-of-body is at endIndex - 1, so inserting
    there puts new text before that newline.
    """
    doc = service.documents().get(documentId=document_id).execute()
    content = doc.get("body", {}).get("content", [])
    if not content:
        return 1
    last_end = content[-1].get("endIndex", 1)
    return max(1, last_end - 1)


def replace_all_text(
    service,
    document_id: str,
    find: str,
    replace: str,
    match_case: bool = True,
) -> int:
    """Replace every occurrence of `find` with `replace`. Returns match count.

    Uses documents.batchUpdate with replaceAllText. There is no undo
    through the API — that's why the README says test on a throwaway
    first and why we return the count so callers can sanity-check.
    """
    if not find:
        raise ValueError("`find` must be a non-empty string.")
    request: dict[str, Any] = {
        "replaceAllText": {
            "containsText": {"text": find, "matchCase": match_case},
            "replaceText": replace,
        }
    }
    response = (
        service.documents()
        .batchUpdate(documentId=document_id, body={"requests": [request]})
        .execute()
    )
    replies = response.get("replies", [])
    if not replies:
        return 0
    return replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0) or 0


def append_text(service, document_id: str, text: str) -> int:
    """Append `text` at the end of the document body. Returns end index used."""
    if not text:
        raise ValueError("`text` must be a non-empty string.")
    end_index = get_document_end_index(service, document_id)
    request: dict[str, Any] = {
        "insertText": {
            "location": {"index": end_index},
            "text": text,
        }
    }
    service.documents().batchUpdate(
        documentId=document_id, body={"requests": [request]}
    ).execute()
    return end_index
