#!/usr/bin/env python3
"""
cli.py
======

Standalone terminal client for Open-i — the "quick shortcut" that lets you run

    openi "dental anatomy"

directly in your shell and get formatted results in the console, WITHOUT
opening the interactive Claude Code session.

It reuses the exact same search + parsing logic as the MCP server
(`openi_client.py`), so both paths behave identically.

Note on language: unlike the MCP tool (where the LLM translates for you), this
CLI sends your text to Open-i as-is. Open-i is English-only, so type your query
in English for best results (e.g. `openi "dental caries"`, not "cárie").

Usage:
    openi "dental anatomy"
    openi "panoramic radiograph" -n 5 --type g
    openi "oral incision" --specialty d --json
    openi "mandible fracture" --markdown
"""

from __future__ import annotations

import argparse
import json
import sys

from openi_client import (
    IMAGE_TYPE_HINTS,
    OpeniError,
    OpeniSearchResult,
    search_openi,
)

# Force UTF-8 stdout/stderr. Windows consoles default to a legacy codepage
# (e.g. cp1252), which cannot encode the accented characters, ellipsis (…) and
# box-drawing separators this CLI prints — without this, every run crashes
# with UnicodeEncodeError on Windows. Harmless no-op on platforms that are
# already UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ANSI colours (auto-disabled when output is not a TTY, e.g. piped to a file).
_USE_COLOR = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _bold(t: str) -> str:
    return _c(t, "1")


def _dim(t: str) -> str:
    return _c(t, "2")


def _cyan(t: str) -> str:
    return _c(t, "36")


def _green(t: str) -> str:
    return _c(t, "32")


def _red(t: str) -> str:
    return _c(t, "31")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openi",
        description="Search Open-i (NLM) biomedical images from your terminal.",
        epilog=(
            "Image type codes (--type): "
            + ", ".join(f"{k}={v}" for k, v in IMAGE_TYPE_HINTS.items())
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="+", help="Search terms (in English).")
    parser.add_argument("-m", "--start", type=int, default=1,
                        help="Start index (default: 1).")
    parser.add_argument("-n", "--end", type=int, default=10,
                        help="End index (default: 10).")
    parser.add_argument("-t", "--type", dest="it", default=None,
                        help="Image type filter, e.g. g (graphics), ph (photo), x (x-ray).")
    parser.add_argument("-s", "--specialty", dest="sp", default=None,
                        help="Specialty filter, e.g. d (dentistry).")
    parser.add_argument("-a", "--article-type", dest="at", default=None,
                        help="Article type filter code.")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of pretty text.")
    parser.add_argument("--markdown", action="store_true",
                        help="Output Markdown (inline image links) instead of pretty text.")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="HTTP timeout in seconds (default: 30).")
    return parser


def render_text(result: OpeniSearchResult) -> str:
    lines: list[str] = []
    header = (
        f"{_bold('Open-i')} — query: {_cyan(result.query)}  |  "
        f"showing {_green(str(len(result.results)))} of "
        f"{_green(str(result.total))} matches"
    )
    lines.append(header)
    lines.append(_dim("─" * 72))

    if not result.results:
        lines.append(_dim("No results. Try broader/English terms or remove filters."))
        return "\n".join(lines)

    for idx, img in enumerate(result.results, start=1):
        lines.append(f"{_bold(f'{idx}.')} {_bold(img.title)}")
        if img.summary:
            lines.append(f"   {img.summary}")
        if img.image_url:
            lines.append(f"   {_dim('image:')}  {_cyan(img.image_url)}")
        if img.article_url:
            lines.append(f"   {_dim('source:')} {img.article_url}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_markdown(result: OpeniSearchResult) -> str:
    lines = [
        f"# Open-i results for “{result.query}”",
        f"_Showing {len(result.results)} of {result.total} matches._",
        "",
    ]
    for img in result.results:
        lines.append(img.to_markdown())
        lines.append("\n---\n")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = " ".join(args.query).strip()

    try:
        result = search_openi(
            query=query,
            m=args.start,
            n=args.end,
            it=args.it,
            sp=args.sp,
            at=args.at,
            timeout=args.timeout,
        )
    except OpeniError as exc:
        status = f" (HTTP {exc.status_code})" if exc.status_code else ""
        print(_red(f"Error{status}: {exc.message}"), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif args.markdown:
        print(render_markdown(result))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
