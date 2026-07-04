"""
openi_client.py
================

Shared, dependency-light client for the Open-i (Open Access Biomedical Image
Search Engine) public API provided by the U.S. National Library of Medicine.

    Base URL : https://openi.nlm.nih.gov/
    Endpoint : GET /api/search
    Auth     : none (public API, no key required)
    Docs     : https://openi.nlm.nih.gov/services

This module is imported by BOTH:
  * server.py  -> the MCP server (tool `search_openi_images`)
  * cli.py     -> the standalone `openi` terminal command

Keeping the networking + parsing logic here means there is a single source of
truth for how we talk to Open-i and how we normalise its (somewhat noisy)
JSON response into a clean list of results.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import httpx

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

OPENI_BASE_URL = "https://openi.nlm.nih.gov"
SEARCH_ENDPOINT = f"{OPENI_BASE_URL}/api/search"

DEFAULT_TIMEOUT = 45.0  # seconds — openi.nlm.nih.gov can be slow/flaky under load
USER_AGENT = "mcp-openi-server/1.0 (+https://github.com/masterface77/mcp-openi-server)"

# Allowed parameter values, taken verbatim from the official OAS 2.0 spec at
# https://openi.nlm.nih.gov/services . We do NOT hard-fail on unknown values
# (the API is the ultimate authority) but we expose these so the MCP tool and
# CLI can help the user / LLM pick valid codes.
IMAGE_TYPES = ["xg", "xm", "x", "u", "ph", "p", "mc", "m", "g", "c"]
ARTICLE_TYPES = [
    "ab", "bk", "bf", "cr", "dp", "di", "ed", "ib", "in", "lt", "mr", "ma",
    "ne", "ob", "pr", "or", "re", "ra", "rw", "sr", "rr", "os", "hs", "ot",
]
SPECIALTIES = [
    "b", "bc", "c", "ca", "cc", "d", "de", "dt", "e", "en", "f", "eh", "g",
    "ge", "gr", "gy", "h", "i", "id", "im", "n", "ne", "nu", "o", "or", "ot",
    "p", "py", "pu", "r", "s", "t", "u", "v", "vil",
]
COLLECTIONS = ["pmc", "cxr", "usc", "hmd", "mpx"]

# Human-readable hints for the most commonly used image-type codes. The full
# legend lives on the Open-i site; these are the ones people reach for.
IMAGE_TYPE_HINTS = {
    "g": "graphics / charts / illustrations / diagrams",
    "ph": "photograph (clinical/gross photo)",
    "x": "X-ray",
    "xg": "X-ray angiography",
    "xm": "mammography",
    "u": "ultrasound",
    "c": "CT scan",
    "m": "MRI",
    "mc": "microscopy / histology",
    "p": "PET",
}


# --------------------------------------------------------------------------- #
# Result / error data structures
# --------------------------------------------------------------------------- #


@dataclass
class OpeniImage:
    """One normalised search result."""

    title: str
    image_url: Optional[str]
    thumbnail_url: Optional[str]
    summary: str
    article_url: Optional[str] = None
    uid: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        """Render as a Markdown block with an inline image link."""
        parts = [f"### {self.title}".strip()]
        if self.image_url:
            alt = _truncate(self.title, 80) or "Open-i image"
            parts.append(f"![{alt}]({self.image_url})")
        if self.summary:
            parts.append(self.summary)
        if self.article_url:
            parts.append(f"[Source article]({self.article_url})")
        return "\n\n".join(parts)


@dataclass
class OpeniSearchResult:
    """The full outcome of a search call."""

    query: str
    total: int
    results: list[OpeniImage] = field(default_factory=list)
    api_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total": self.total,
            "returned": len(self.results),
            "api_url": self.api_url,
            "results": [r.to_dict() for r in self.results],
        }


class OpeniError(Exception):
    """Raised when the Open-i API returns an error or is unreachable."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _abs_url(path: Optional[str]) -> Optional[str]:
    """Turn an Open-i relative image path into an absolute URL."""
    if not path or not isinstance(path, str):
        return None
    path = path.strip()
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return OPENI_BASE_URL + path


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> str:
    """Strip HTML tags / entities / excess whitespace from a text field."""
    if value is None:
        return ""
    text = str(value)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"  # ellipsis


def _first_nonempty(*values: Any) -> str:
    for v in values:
        cleaned = _clean_text(v)
        if cleaned:
            return cleaned
    return ""


def build_search_params(
    query: str,
    m: Optional[int] = None,
    n: Optional[int] = None,
    it: Optional[str] = None,
    sp: Optional[str] = None,
    at: Optional[str] = None,
    coll: Optional[str] = None,
    favor: Optional[str] = None,
    fields: Optional[str] = None,
) -> dict[str, str]:
    """Assemble the query-string parameters for GET /api/search.

    Only non-empty parameters are included so we send a minimal, valid request.
    """
    if not query or not query.strip():
        raise OpeniError("`query` must be a non-empty string.")

    params: dict[str, str] = {"query": query.strip()}
    optional = {
        "m": m,
        "n": n,
        "it": it,
        "sp": sp,
        "at": at,
        "coll": coll,
        "favor": favor,
        "fields": fields,
    }
    for key, value in optional.items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            params[key] = text
    return params


def parse_search_response(query: str, data: dict[str, Any], api_url: Optional[str] = None,
                          max_summary_chars: int = 500) -> OpeniSearchResult:
    """Normalise the raw Open-i JSON into an :class:`OpeniSearchResult`.

    The Open-i payload is a dict that contains a ``list`` of records. Field
    names vary between records, so we probe several likely keys for each piece
    of information and fall back gracefully.
    """
    if not isinstance(data, dict):
        raise OpeniError("Unexpected API response: not a JSON object.")

    raw_list = data.get("list")
    if raw_list is None:
        # Some error payloads carry a message instead of a list.
        msg = _first_nonempty(data.get("error"), data.get("message"))
        if msg:
            raise OpeniError(f"Open-i API error: {msg}")
        raw_list = []

    total = _coerce_int(
        data.get("total"),
        data.get("count"),
        default=len(raw_list) if isinstance(raw_list, list) else 0,
    )

    results: list[OpeniImage] = []
    if isinstance(raw_list, list):
        for item in raw_list:
            if isinstance(item, dict):
                results.append(_parse_item(item, max_summary_chars))

    return OpeniSearchResult(
        query=query,
        total=total,
        results=results,
        api_url=api_url,
    )


def _coerce_int(*values: Any, default: int = 0) -> int:
    for v in values:
        if v is None:
            continue
        try:
            return int(v)
        except (TypeError, ValueError):
            continue
    return default


def _parse_item(item: dict[str, Any], max_summary_chars: int) -> OpeniImage:
    image = item.get("image") if isinstance(item.get("image"), dict) else {}

    # Title: prefer the article title, then the image caption.
    title = _first_nonempty(
        item.get("title"),
        item.get("docTitle"),
        image.get("caption"),
        "Untitled Open-i result",
    )

    # Image URL: large image preferred, then thumbnail.
    image_url = _abs_url(
        _first_str(item.get("imgLarge"), item.get("imgGrid150"),
                   item.get("imgThumb"), image.get("imgLarge"))
    )
    thumbnail_url = _abs_url(
        _first_str(item.get("imgThumb"), item.get("imgGrid150"),
                   item.get("imgLarge"))
    )

    # Summary: image caption first (most relevant to the picture), then abstract.
    summary_raw = _first_nonempty(
        image.get("caption"),
        item.get("abstract"),
        image.get("mention"),
    )
    summary = _truncate(summary_raw, max_summary_chars)

    # Link to the source article when available.
    article_url = _abs_url(
        _first_str(
            item.get("fulltext_html_url"),
            item.get("detailedQueryURL"),
            item.get("pmc_url"),
        )
    )
    if not article_url:
        pmcid = _first_str(item.get("pmcid"))
        if pmcid:
            article_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"

    return OpeniImage(
        title=_truncate(title, 300),
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        summary=summary,
        article_url=article_url,
        uid=_first_str(item.get("uid"), item.get("pmcid")),
    )


def _first_str(*values: Any) -> Optional[str]:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


# --------------------------------------------------------------------------- #
# Network calls
# --------------------------------------------------------------------------- #


def _handle_status(response: httpx.Response) -> dict[str, Any]:
    """Convert an httpx response into parsed JSON, raising OpeniError on failure."""
    status = response.status_code
    if status == 200:
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise OpeniError(f"Open-i returned status 200 but invalid JSON: {exc}", 200)

    # The docs call out 400 (bad request) and 500 (server error) explicitly.
    snippet = _truncate(_clean_text(response.text), 200)
    if status == 400:
        raise OpeniError(
            f"Open-i rejected the request (HTTP 400 - Bad Request). "
            f"Check the parameter values. Details: {snippet or 'none'}",
            400,
        )
    if status == 500:
        raise OpeniError(
            f"Open-i had an internal error (HTTP 500 - Server Error). "
            f"Try again shortly. Details: {snippet or 'none'}",
            500,
        )
    raise OpeniError(f"Open-i returned unexpected HTTP {status}. Details: {snippet or 'none'}", status)


async def search_openi_async(
    query: str,
    m: Optional[int] = None,
    n: Optional[int] = None,
    it: Optional[str] = None,
    sp: Optional[str] = None,
    at: Optional[str] = None,
    coll: Optional[str] = None,
    favor: Optional[str] = None,
    fields: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_summary_chars: int = 500,
) -> OpeniSearchResult:
    """Async search against Open-i. Used by the MCP server."""
    params = build_search_params(query, m, n, it, sp, at, coll, favor, fields)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers,
                                     follow_redirects=True) as client:
            response = await client.get(SEARCH_ENDPOINT, params=params)
    except httpx.TimeoutException as exc:
        raise OpeniError(f"Open-i request timed out after {timeout}s: {exc}") from exc
    except httpx.HTTPError as exc:
        raise OpeniError(f"Could not reach Open-i: {exc}") from exc

    data = _handle_status(response)
    return parse_search_response(query, data, api_url=str(response.url),
                                 max_summary_chars=max_summary_chars)


def search_openi(
    query: str,
    m: Optional[int] = None,
    n: Optional[int] = None,
    it: Optional[str] = None,
    sp: Optional[str] = None,
    at: Optional[str] = None,
    coll: Optional[str] = None,
    favor: Optional[str] = None,
    fields: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_summary_chars: int = 500,
) -> OpeniSearchResult:
    """Synchronous search against Open-i. Used by the standalone CLI."""
    params = build_search_params(query, m, n, it, sp, at, coll, favor, fields)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        with httpx.Client(timeout=timeout, headers=headers,
                          follow_redirects=True) as client:
            response = client.get(SEARCH_ENDPOINT, params=params)
    except httpx.TimeoutException as exc:
        raise OpeniError(f"Open-i request timed out after {timeout}s: {exc}") from exc
    except httpx.HTTPError as exc:
        raise OpeniError(f"Could not reach Open-i: {exc}") from exc

    data = _handle_status(response)
    return parse_search_response(query, data, api_url=str(response.url),
                                 max_summary_chars=max_summary_chars)
