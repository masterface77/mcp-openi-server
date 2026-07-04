#!/usr/bin/env python3
"""
server.py
=========

MCP (Model Context Protocol) server that exposes the Open-i biomedical image
search engine (U.S. National Library of Medicine) as a tool the Claude Code
agent can call.

Transport : stdio  (this is what Claude Code / claude mcp add expects)
SDK       : the official `mcp` Python SDK (FastMCP)

Run it directly for a quick smoke test:

    python server.py

but normally it is launched by Claude Code, which speaks MCP over stdin/stdout.
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from openi_client import (
    ARTICLE_TYPES,
    IMAGE_TYPES,
    IMAGE_TYPE_HINTS,
    SPECIALTIES,
    OpeniError,
    search_openi_async,
)

mcp = FastMCP("openi")


@mcp.tool()
async def search_openi_images(
    query: str,
    m: int = 1,
    n: int = 10,
    it: Optional[str] = None,
    sp: Optional[str] = None,
    at: Optional[str] = None,
) -> dict:
    """Search Open-i (NLM) for medical, clinical, graphical and dental images.

    Open-i (https://openi.nlm.nih.gov) is the U.S. National Library of
    Medicine's open-access biomedical image search engine. It indexes figures,
    charts, X-rays, photographs and illustrations from PubMed Central articles
    and other collections. No API key is required.

    ┌──────────────────────────────────────────────────────────────────────┐
    │ ⚠️  TRANSLATION RULE — READ THIS BEFORE CALLING THE TOOL              │
    │                                                                        │
    │ The Open-i index is ENGLISH-ONLY. You (the LLM agent) MUST translate  │
    │ every Portuguese term the user gives you into English BEFORE putting  │
    │ it into `query`. Never send Portuguese to the API.                    │
    │                                                                        │
    │   "incisão oral"          -> "oral incision"                          │
    │   "odontolegista"         -> "forensic dentistry"                     │
    │   "anatomia dental"       -> "dental anatomy"                         │
    │   "radiografia panorâmica"-> "panoramic radiograph"                   │
    │   "cárie"                 -> "dental caries"                          │
    │                                                                        │
    │ If the user writes in English already, pass it through unchanged.     │
    └──────────────────────────────────────────────────────────────────────┘

    Args:
        query: The search terms, IN ENGLISH (translate first — see rule above).
        m: Start index of the result window (1-based). Default 1.
        n: End index of the result window. Default 10. Ask for a small window
           (e.g. m=1, n=10) unless the user wants more.
        it: Image Type filter. One or more comma-separated codes from
            [xg, xm, x, u, ph, p, mc, m, g, c]. Most useful:
              g  = graphics / charts / diagrams / illustrations
              ph = photograph (clinical / gross photo)
              x  = X-ray            xm = mammography     xg = angiography
              u  = ultrasound       c  = CT              m  = MRI
              mc = microscopy / histology                p  = PET
            Leave empty to search all image types.
        sp: Specialties filter. Comma-separated codes, e.g. "d" for dentistry.
            Full set: [b, bc, c, ca, cc, d, de, dt, e, en, f, eh, g, ge, gr,
            gy, h, i, id, im, n, ne, nu, o, or, ot, p, py, pu, r, s, t, u, v,
            vil]. Leave empty for all specialties.
        at: Article Type filter. Comma-separated codes from [ab, bk, bf, cr,
            dp, di, ed, ib, in, lt, mr, ma, ne, ob, pr, or, re, ra, rw, sr,
            rr, os, hs, ot]. Leave empty for all article types.

    Returns:
        A dict with keys:
          query    - the (English) query that was actually sent
          total    - total number of matches Open-i reports
          returned - how many results are in this response
          api_url  - the exact URL that was requested (for transparency)
          results  - a clean list; each item has:
                       title, image_url, thumbnail_url, summary, article_url, uid

        To show a result to the user, render the image with Markdown:
            ![title](image_url)
        and cite the source with [Source](article_url).

        On failure the dict instead has:
          error    - a human-readable message
          status   - the HTTP status code if the API responded (400/500/…)
    """
    try:
        result = await search_openi_async(
            query=query,
            m=m,
            n=n,
            it=it,
            sp=sp,
            at=at,
        )
    except OpeniError as exc:
        return {"error": exc.message, "status": exc.status_code, "query": query}

    payload = result.to_dict()
    if not payload["results"]:
        payload["note"] = (
            "No images matched. Tips: make sure `query` is in English, "
            "broaden the terms, or remove the `it`/`sp`/`at` filters."
        )
    return payload


@mcp.tool()
def openi_reference() -> dict:
    """Return the Open-i filter code reference (image types, specialties, article types).

    Handy when you need to look up which filter code corresponds to what,
    without leaving the conversation.
    """
    return {
        "image_types": {code: IMAGE_TYPE_HINTS.get(code, code) for code in IMAGE_TYPES},
        "specialties_codes": SPECIALTIES,
        "article_type_codes": ARTICLE_TYPES,
        "notes": (
            "Open-i is English-only: translate Portuguese queries to English "
            "before searching. Full legend at https://openi.nlm.nih.gov/services"
        ),
    }


def main() -> None:
    """Entry point: run the MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
