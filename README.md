# mcp-openi-server

**Search medical, clinical, radiological and dental images from your terminal and from Claude Code — powered by [Open-i](https://openi.nlm.nih.gov) (the U.S. National Library of Medicine's Open Access Biomedical Image Search Engine).**

This repository gives you **three ways** to reach the same Open-i search engine, all sharing one tested core (`openi_client.py`):

| # | Component | What it is | How you use it |
|---|-----------|-----------|----------------|
| 1 | **MCP server** (`server.py`) | A [Model Context Protocol](https://modelcontextprotocol.io) server exposing a `search_openi_images` tool. | Claude Code (or any MCP client) calls it **for you**, mid-conversation, and returns images as Markdown links. |
| 2 | **`openi` CLI** (`cli.py` + `openi`) | A standalone terminal command. | You type `openi "dental anatomy"` and get results printed in your console — no chat needed. |
| 3 | **Claude Code plugin config** | The `claude mcp add …` command + `.mcp.json`. | Installs component #1 so it is available in every Claude Code session automatically. |

The Open-i API is **public and requires no API key**.

> ℹ️ **API reference:** always double-check the parameters and codes against the official docs at **<https://openi.nlm.nih.gov/services>**. This project targets the `GET /api/search` endpoint documented there.

---

## Table of contents

- [What can I search for?](#what-can-i-search-for)
- [Requirements](#requirements)
- [Quick start (60 seconds)](#quick-start-60-seconds)
- [1. The MCP server](#1-the-mcp-server)
- [2. The `openi` terminal command](#2-the-openi-terminal-command)
- [3. Install the server into Claude Code](#3-install-the-server-into-claude-code)
- [Using it inside Claude Code (let the agent do it for you)](#using-it-inside-claude-code-let-the-agent-do-it-for-you)
- [Filter codes reference](#filter-codes-reference)
- [The Portuguese → English translation rule](#the-portuguese--english-translation-rule)
- [How it works internally](#how-it-works-internally)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)
- [License](#license)

---

## What can I search for?

Open-i indexes **figures, charts, X-rays, CT/MRI scans, ultrasound, histology and clinical photographs** extracted from PubMed Central articles and other NLM collections. Typical uses:

- A **dentistry** reference: `openi "dental anatomy" --type g`
- A **clinical photo** of a procedure: `openi "oral incision" --type ph`
- A **radiograph**: `openi "panoramic radiograph mandible" --type x`
- A **chart/diagram** for a paper or slide deck: `openi "bone remodeling diagram" --type g`

---

## Requirements

- **Python 3.10 or newer** (`python3 --version`)
- **pip** and the ability to create a virtual environment (`python3 -m venv`)
- Internet access to `https://openi.nlm.nih.gov`
- *(Optional, for the Claude Code integration)* the **Claude Code CLI** — verify with `claude --version`

---

## Quick start (60 seconds)

```bash
# 1. Clone the repository
git clone https://github.com/masterface77/mcp-openi-server.git
cd mcp-openi-server

# 2. Create an isolated Python environment and install the two dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Try the standalone CLI right away
python cli.py "dental anatomy" -n 5

# 4. Register the MCP server with Claude Code (see section 3 for details)
claude mcp add openi -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

That's it. The rest of this README explains each piece in depth.

---

## 1. The MCP server

`server.py` uses the **official MCP Python SDK** (`FastMCP`) and communicates over **stdio** — exactly what Claude Code expects. It exposes two tools:

- **`search_openi_images`** — the main search tool.
- **`openi_reference`** — returns the filter-code cheat sheet (image types, specialties, article types) without leaving the conversation.

### Install

```bash
cd mcp-openi-server
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # installs: mcp, httpx
```

### Run it standalone (optional smoke test)

You normally never launch this by hand — Claude Code does. But you can confirm it starts:

```bash
python server.py
```

It will wait silently for MCP messages on stdin. Press `Ctrl+C` to stop. (Seeing nothing is *correct*: stdio servers don't print to the console.)

### The `search_openi_images` tool

| Parameter | Type | Default | Meaning |
|-----------|------|---------|---------|
| `query`   | string | — (required) | Search terms, **in English** (the agent translates for you). |
| `m`       | int  | `1`  | Start index of the result window. |
| `n`       | int  | `10` | End index of the result window. |
| `it`      | string | none | Image-type filter code(s), e.g. `g`, `ph`, `x`. |
| `sp`      | string | none | Specialty code(s), e.g. `d` (dentistry). |
| `at`      | string | none | Article-type code(s). |

**Returns** a clean object:

```jsonc
{
  "query": "dental anatomy",
  "total": 42,
  "returned": 5,
  "api_url": "https://openi.nlm.nih.gov/api/search?query=dental+anatomy&m=1&n=5",
  "results": [
    {
      "title": "Dental anatomy of the mandibular molar",
      "image_url": "https://openi.nlm.nih.gov/imgs/512/1/PMC123/fig1.png",
      "thumbnail_url": "https://openi.nlm.nih.gov/imgs/150/1/PMC123/fig1.png",
      "summary": "Figure 1. Cross-section showing enamel, dentin and pulp.",
      "article_url": "https://openi.nlm.nih.gov/pmc/articles/PMC123456/",
      "uid": "PMC123-fig1"
    }
  ]
}
```

On failure it returns `{ "error": "...", "status": 400, "query": "..." }`. HTTP **400** (bad request) and **500** (server error) from the API are caught and reported clearly, as are timeouts and network problems.

---

## 2. The `openi` terminal command

The **quick shortcut**. Run a search and get formatted results straight in your console — no Claude session required.

```bash
openi "dental anatomy"
```

### Make `openi` available everywhere

Pick **one** of these:

**Option A — symlink onto your PATH (recommended):**

```bash
# from inside the repo
chmod +x openi
ln -s "$(pwd)/openi" ~/.local/bin/openi     # make sure ~/.local/bin is on your PATH
openi "panoramic radiograph"
```

The `openi` launcher automatically finds and uses the project's `.venv`, so it works from any directory.

**Option B — install as a console script:**

```bash
source .venv/bin/activate
pip install .            # reads pyproject.toml, installs an `openi` command
openi "dental caries"
```

**Option C — just call it directly (no install):**

```bash
python cli.py "dental caries"
```

### CLI options

```text
openi [-h] [-m START] [-n END] [-t TYPE] [-s SPECIALTY] [-a ARTICLE_TYPE]
      [--json] [--markdown] [--timeout SECONDS] query [query ...]
```

| Flag | Meaning |
|------|---------|
| `-m, --start` | Start index (default 1). |
| `-n, --end`   | End index (default 10). |
| `-t, --type`  | Image type, e.g. `g` graphics, `ph` photo, `x` x-ray. |
| `-s, --specialty` | Specialty code, e.g. `d` dentistry. |
| `-a, --article-type` | Article-type code. |
| `--json` | Print raw JSON (great for piping into `jq`). |
| `--markdown` | Print Markdown with inline `![](…)` image links. |
| `--timeout` | HTTP timeout in seconds (default 30). |

### Examples

```bash
openi "oral incision" --type ph -n 5           # 5 clinical photos
openi "bone remodeling" --type g --markdown    # diagrams, as Markdown
openi "mandible fracture" --json | jq '.results[].image_url'
```

> **Language note:** the CLI sends your text to Open-i **as-is** (there is no LLM in the loop here). Open-i is **English-only**, so type English terms — `openi "dental caries"`, not `openi "cárie"`. Inside Claude Code, the agent translates automatically (see below).

---

## 3. Install the server into Claude Code

This is the "plugin" step: make `search_openi_images` available in **every** Claude Code session.

### The exact command

From inside the cloned repo (so `$(pwd)` resolves correctly):

```bash
claude mcp add openi -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

- `openi` is the name the server will have inside Claude Code.
- Everything after `--` is the command Claude Code runs to start the server.
- Using the **`.venv` Python** guarantees the `mcp` and `httpx` dependencies are found.

Add `-s user` to make it available in **all** your projects (not just the current directory):

```bash
claude mcp add openi -s user -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

### Verify

```bash
claude mcp list                 # should show: openi
```

Or, inside an interactive Claude Code session, run the slash command `/mcp` to see connected servers and their tools.

### Alternative A — `uv` (no manual venv)

If you use [`uv`](https://docs.astral.sh/uv/):

```bash
claude mcp add openi -- uv run --directory "$(pwd)" --with mcp --with httpx python server.py
```

### Alternative B — commit a `.mcp.json` (share with your team)

Copy the provided template and edit the absolute paths:

```bash
cp .mcp.json.example .mcp.json
```

```jsonc
{
  "mcpServers": {
    "openi": {
      "command": "/ABSOLUTE/PATH/mcp-openi-server/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/mcp-openi-server/server.py"]
    }
  }
}
```

Anyone who opens the project in Claude Code will be prompted to enable the `openi` server automatically.

### Alternative C — Claude Desktop

Add the same block to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`,
Windows: `%APPDATA%\Claude\claude_desktop_config.json`) and restart the app.

### Removing it

```bash
claude mcp remove openi
```

---

## Using it inside Claude Code (let the agent do it for you)

Once installed, **you don't call any command** — you just ask in natural language, and Claude Code decides to use the tool and hands you back an image. Try prompts like:

> **"Search Open-i for a diagram of dental anatomy and show me the best image."**

> **"Preciso de uma foto clínica de uma incisão oral para uma apresentação — busca no Open-i e me manda o link em Markdown."**
> *(Portuguese is fine — the agent translates the query to English before searching.)*

> **"Find an X-ray of a mandible fracture on Open-i and embed it here."**

Because the tool's description tells the agent to **render results as Markdown image links**, Claude will reply with something you can paste anywhere:

```markdown
![Dental anatomy of the mandibular molar](https://openi.nlm.nih.gov/imgs/512/1/PMC123/fig1.png)
*Figure 1. Cross-section showing enamel, dentin and pulp.* — [Source](https://openi.nlm.nih.gov/pmc/articles/PMC123456/)
```

You can also nudge the agent to filter: *"only clinical photos"* → it sets `it="ph"`; *"only charts/diagrams"* → `it="g"`; *"dentistry specialty"* → `sp="d"`.

---

## Filter codes reference

Values below come from the official OAS 2.0 spec at <https://openi.nlm.nih.gov/services>. Inside Claude Code you can also call the `openi_reference` tool to print them.

### Image type (`it` / `--type`)

`[xg, xm, x, u, ph, p, mc, m, g, c]`

| Code | Meaning (common ones) |
|------|-----------------------|
| `g`  | **graphics** — charts, diagrams, illustrations |
| `ph` | **photograph** — clinical / gross photo |
| `x`  | X-ray |
| `xm` | mammography |
| `xg` | X-ray angiography |
| `u`  | ultrasound |
| `c`  | CT scan |
| `m`  | MRI |
| `mc` | microscopy / histology |
| `p`  | PET |

### Specialties (`sp` / `--specialty`)

`[b, bc, c, ca, cc, d, de, dt, e, en, f, eh, g, ge, gr, gy, h, i, id, im, n, ne, nu, o, or, ot, p, py, pu, r, s, t, u, v, vil]`
(e.g. `d` is the dentistry-related specialty; consult the site for the full legend.)

### Article types (`at` / `--article-type`)

`[ab, bk, bf, cr, dp, di, ed, ib, in, lt, mr, ma, ne, ob, pr, or, re, ra, rw, sr, rr, os, hs, ot]`

### Other endpoint parameters (advanced, supported by `openi_client.py`)

`coll` (collections: `pmc, cxr, usc, hmd, mpx`), `favor` (rank by), `fields` (search in), plus `lic`, `sub`, `vid`, `hmp` — see the official docs.

---

## The Portuguese → English translation rule

Open-i's index is **English-only**. This project handles that in two different ways depending on the entry point:

- **MCP server (Claude Code):** the `search_openi_images` docstring **explicitly instructs the LLM agent to translate any Portuguese term to English before filling `query`.** So `"odontolegista"` becomes `forensic dentistry`, `"cárie"` becomes `dental caries`, etc. — automatically.
- **`openi` CLI:** there is no LLM, so **you** should type English terms.

Common translations the agent uses:

| Portuguese | English (sent to Open-i) |
|------------|--------------------------|
| incisão oral | oral incision |
| odontolegista | forensic dentistry |
| anatomia dental | dental anatomy |
| radiografia panorâmica | panoramic radiograph |
| cárie | dental caries |

---

## How it works internally

```
                         ┌────────────────────┐
   Claude Code  ──stdio──▶     server.py       │  (MCP tool: search_openi_images)
                         └─────────┬──────────┘
                                   │  imports
   Your terminal ─────────▶  cli.py  (openi)   │
                                   │  imports
                                   ▼
                         ┌────────────────────┐   HTTPS GET
                         │   openi_client.py   ├────────────▶ openi.nlm.nih.gov/api/search
                         │  • build params     │◀────────────  JSON (200 / 400 / 500)
                         │  • call API (httpx) │
                         │  • parse + clean    │
                         └────────────────────┘
```

`openi_client.py` is the **single source of truth**: it builds the query parameters, calls the API with `httpx`, handles HTTP 400/500 and network/timeout errors, strips HTML out of captions, turns relative image paths into absolute URLs, and returns a tidy list of `{title, image_url, thumbnail_url, summary, article_url}`. Both `server.py` and `cli.py` just call it.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `claude mcp list` doesn't show `openi` | Re-run the `claude mcp add` command from **inside** the repo so `$(pwd)` resolves; check `claude mcp get openi`. |
| Tool errors with *"Could not reach Open-i"* | Check your internet/proxy; confirm `https://openi.nlm.nih.gov` is reachable (`curl -I https://openi.nlm.nih.gov`). |
| `ModuleNotFoundError: No module named 'mcp'` | You're not using the venv Python. Point Claude Code at `.venv/bin/python` (see section 3). |
| No results | Ensure the query is **English**, broaden the terms, and drop `--type`/`--specialty` filters. |
| HTTP 400 | A filter code is invalid — check the [reference table](#filter-codes-reference). |
| `openi: command not found` | Finish [section 2](#2-the-openi-terminal-command) (symlink onto PATH or `pip install .`). |

---

## Project layout

```
mcp-openi-server/
├── server.py            # MCP server (FastMCP, stdio) — the search "engine" for Claude Code
├── cli.py               # Standalone CLI implementation
├── openi                # Bash launcher so you can run `openi "…"` from anywhere
├── openi_client.py      # Shared core: API call + response parsing (used by both)
├── requirements.txt     # Runtime deps: mcp, httpx
├── pyproject.toml       # Packaging + `openi` console-script entry point
├── .mcp.json.example    # Template to auto-load the server per project in Claude Code
└── README.md            # This file
```

---

## License

MIT. Open-i content itself is subject to the terms of the U.S. National Library of Medicine — see <https://openi.nlm.nih.gov>.
