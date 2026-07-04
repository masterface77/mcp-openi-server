# mcp-openi-server — Open-i Medical Image Search for Claude Code (MCP Server + CLI + Plugin)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/Model%20Context%20Protocol-server-6C3BF3)](https://modelcontextprotocol.io)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757)](https://code.claude.com/docs/en/plugins)

**Search medical, clinical, radiological and dental images from your terminal and from Claude Code — powered by [Open-i](https://openi.nlm.nih.gov) (the U.S. National Library of Medicine's Open Access Biomedical Image Search Engine).** No API key, no sign-up, no rate-limit token — Open-i is a fully public research API, and this project is the fastest way to query it from an AI coding agent or a shell.

This repository gives you **several ways** to reach the same Open-i search engine, all sharing one tested core (`openi_client.py`):

| # | Component | What it is | How you use it |
|---|-----------|-----------|----------------|
| 1 | **Claude Code plugin** | A `.claude-plugin/plugin.json` + self-hosted marketplace, bundling the MCP server **and** an `/openi:medical-image` skill. | `/plugin marketplace add` + `/plugin install` — the recommended, one-command way to get the tool + skill in **every** Claude Code session. |
| 2 | **`medical-image` skill** | A model-invocable Skill (`/openi:medical-image <topic>`). | The **quick way**: one slash command finds + returns (or embeds) the best image. Claude also triggers it on its own while writing notes. |
| 3 | **MCP server** (`server.py`) | A [Model Context Protocol](https://modelcontextprotocol.io) server exposing a `search_openi_images` tool. | Claude Code (or any MCP client) calls it **for you**, mid-conversation, and returns images as Markdown links. |
| 4 | **`openi` CLI** (`cli.py` + `openi`) | A standalone terminal command. | You type `openi "dental anatomy"` and get results printed in your console — no chat needed. |
| 5 | **Manual `.mcp.json` / `claude mcp add`** | The classic, no-plugin way to wire up component #3. | Useful if you don't want to use the plugin/marketplace system, or need per-project config. |

The Open-i API is **public and requires no API key**.

> ℹ️ **API reference:** always double-check the parameters and codes against the official docs at **<https://openi.nlm.nih.gov/services>**. This project targets the `GET /api/search` endpoint documented there.

> ⚠️ **Don't confuse Open-i with NCBI's E-utilities.** `openi.nlm.nih.gov` (this project's only dependency) genuinely needs **no key at all** — it's a fully open, unauthenticated REST endpoint. A *different*, related NLM service — the **NCBI E-utilities API** at `eutils.ncbi.nlm.nih.gov` / `www.ncbi.nlm.nih.gov` (used for things like PubMed/PMC full-text lookups) — **does** require (or strongly recommend) an API key for higher rate limits. This project never calls that API: the `article_url` field in each result is just a plain, human-clickable link built from the `pmcid` Open-i already returns (e.g. `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456/`), not an authenticated API call. So: **no key needed anywhere in this repo**, today or if it grows — just be aware the two services are not the same thing if you extend this project to query NCBI directly.

---

## Table of contents

- [What can I search for?](#what-can-i-search-for)
- [Requirements](#requirements)
- [Windows notes](#windows-notes)
- [Quick start (60 seconds)](#quick-start-60-seconds)
- [0. Install as a Claude Code plugin (recommended)](#0-install-as-a-claude-code-plugin-recommended)
- [1. The MCP server](#1-the-mcp-server)
- [2. The `openi` terminal command](#2-the-openi-terminal-command)
- [3. Install the server into Claude Code (manual, no plugin)](#3-install-the-server-into-claude-code-manual-no-plugin)
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
- Internet access to `https://openi.nlm.nih.gov` (public, no API key/account needed)
- The **Claude Code CLI** — verify with `claude --version`
- **Either** of these, depending on which install path you pick:
  - [`uv`](https://docs.astral.sh/uv/getstarted/installation) — for the [plugin install path](#0-install-as-a-claude-code-plugin-recommended) (recommended, no venv needed)
  - **pip** + the ability to create a virtual environment (`python3 -m venv`) — for the [manual install path](#3-install-the-server-into-claude-code-manual-no-plugin)

---

## Windows notes

This project is fully tested on Windows (Git Bash + PowerShell), with two small differences from the Linux/macOS commands used throughout this README:

1. **Venv layout:** `python -m venv .venv` creates `.venv\Scripts\python.exe` on Windows, not `.venv/bin/python`. The `openi` launcher already detects both automatically — you only need to adjust the path yourself when typing a `claude mcp add`/`.mcp.json` command by hand.
2. **`$(pwd)` substitution:** this only works in a POSIX-style shell (Git Bash, WSL). In PowerShell/cmd, write the absolute path directly instead:

   ```powershell
   # PowerShell — from inside the cloned repo
   claude mcp add openi -s user -- "E:\path\to\mcp-openi-server\.venv\Scripts\python.exe" "E:\path\to\mcp-openi-server\server.py"
   ```

Everything else (the `openi` command, `cli.py`, `server.py`) behaves identically on Windows once the venv is created — console output is forced to UTF-8 internally, so accented characters and the `…` ellipsis print correctly even on a legacy `cp1252` terminal.

---

## Quick start (60 seconds)

### Fastest path — install as a plugin

No clone, no venv, no `pip install`. Just needs [`uv`](https://docs.astral.sh/uv/getstarted/installation) on your `PATH`. Run these three lines (in your shell **or** inside a Claude Code session as `/plugin ...`):

```bash
claude plugin marketplace add LeviReisJs/mcp-openi-server
claude plugin install openi@openi-marketplace
claude mcp list          # should show: plugin:openi:openi ... ✓ Connected
```

Then, in any Claude Code session, just ask — e.g. `/openi:medical-image dental anatomy` — or let Claude reach for it on its own. Done.

### Or — standalone CLI / manual install

Use this if you want the `openi` terminal command, or prefer not to use the plugin system.

```bash
# 1. Clone the repository
git clone https://github.com/LeviReisJs/mcp-openi-server.git
cd mcp-openi-server

# 2. Create an isolated Python environment and install the two dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Try the standalone CLI right away
python cli.py "dental anatomy" -n 5
```

```bash
# 4a. Register the MCP server with Claude Code — macOS / Linux / Git Bash:
claude mcp add openi -s user -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
```

```powershell
# 4b. Register the MCP server with Claude Code — Windows PowerShell
#     (run from inside the cloned repo; write out the absolute path):
claude mcp add openi -s user -- "$PWD\.venv\Scripts\python.exe" "$PWD\server.py"
```

Verify either path with `claude mcp list` — you should see `openi ... ✓ Connected`.

That's it. The rest of this README explains each piece in depth.

---

## 0. Install as a Claude Code plugin (recommended)

This repository is itself a **Claude Code plugin** (`.claude-plugin/plugin.json`) *and* a **self-hosted marketplace** (`.claude-plugin/marketplace.json`) for that one plugin. This is the easiest, most portable way to get `search_openi_images` into Claude Code — no manual venv, no `pip install`, no absolute paths to configure. It works because the plugin's MCP entry uses [`uv run`](https://docs.astral.sh/uv/) with the `${CLAUDE_PLUGIN_ROOT}` variable (resolved automatically by Claude Code to wherever the plugin was installed), so `uv` fetches `mcp` and `httpx` into an ephemeral environment on first run — you never touch a venv.

### Install (one-time)

```bash
# Add this repo as a marketplace (only needs to be done once)
claude plugin marketplace add LeviReisJs/mcp-openi-server

# Install the "openi" plugin from it
claude plugin install openi@openi-marketplace
```

You can run the same two commands **from inside an interactive Claude Code session** using the slash-command form instead:

```text
/plugin marketplace add LeviReisJs/mcp-openi-server
/plugin install openi@openi-marketplace
```

### Verify

```bash
claude plugin list        # shows: openi@openi-marketplace ... enabled
claude mcp list            # shows: plugin:openi:openi ... Connected
```

Or, inside a session, run `/mcp` to see it listed as a connected server, and `/context` to confirm the plugin is loaded.

### Requirements for the plugin path specifically

- [`uv`](https://docs.astral.sh/uv/getstarted/installation) installed and on your `PATH` (the plugin's MCP server is launched via `uv run`, which needs `uv` itself — everything else, `uv` installs automatically on first launch).
- No Python venv, no `pip install -r requirements.txt` needed for this path — `uv` handles `mcp` and `httpx` transparently, cached after the first run.

### Updating / removing

```bash
claude plugin marketplace update openi-marketplace   # pull the latest plugin.json from GitHub
claude plugin update openi                           # update the installed plugin
claude plugin uninstall openi                        # remove it
claude plugin marketplace remove openi-marketplace    # stop tracking this marketplace entirely
```

> Prefer the manual route (no plugin system, no marketplace)? Skip to [section 3](#3-install-the-server-into-claude-code-manual-no-plugin) — it still works exactly as before and is fully supported.

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

## 3. Install the server into Claude Code (manual, no plugin)

> If you already installed via [section 0](#0-install-as-a-claude-code-plugin-recommended), you can skip this — it's the same end result via a different mechanism.

This is the manual way to make `search_openi_images` available in **every** Claude Code session, without using the plugin/marketplace system.

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

### The quick way: the `/openi:medical-image` skill

When you install this as a [plugin](#0-install-as-a-claude-code-plugin-recommended), it ships a **Skill** called `medical-image`. That gives you a fast, explicit way to trigger an image search without describing the whole workflow every time:

```text
/openi:medical-image radiografia panorâmica de fratura de mandíbula
```

Claude runs the skill, which tells it to: translate the term to English, pick the right image-type filter, call `search_openi_images`, choose the most relevant result, and hand it back as a ready-to-paste Markdown image with a `[Fonte]` link. The skill also knows how to **place the image directly into a note** when you're working in a notes vault (e.g. Obsidian) — right under the relevant heading, with the citation kept — and can download it for offline use if your vault syncs to a phone/tablet.

Because it's model-invocable, Claude will also reach for the skill on its own when you're writing study notes and a figure would help — you don't have to type the slash command.

### Or just ask in natural language

You never *have* to call any command — just ask, and Claude Code decides to use the tool and hands you back an image. Try prompts like:

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
| `claude plugin install` fails / plugin not found | Run `claude plugin marketplace update openi-marketplace` first, then retry install. Confirm with `claude plugin marketplace list`. |
| Plugin installed but `claude mcp list` shows no `plugin:openi:openi` | Make sure [`uv`](https://docs.astral.sh/uv/) is installed and on `PATH` (`uv --version`) — the plugin's MCP entry runs the server via `uv run`. |
| `claude mcp list` doesn't show `openi` (manual/non-plugin install) | Re-run the `claude mcp add` command from **inside** the repo so `$(pwd)` resolves; check `claude mcp get openi`. |
| Tool errors with *"Could not reach Open-i"* | Check your internet/proxy; confirm `https://openi.nlm.nih.gov` is reachable (`curl -I https://openi.nlm.nih.gov`). |
| `ModuleNotFoundError: No module named 'mcp'` | You're not using the venv Python. Point Claude Code at `.venv/bin/python` (see section 3). |
| No results | Ensure the query is **English**, broaden the terms, and drop `--type`/`--specialty` filters. |
| HTTP 400 | A filter code is invalid — check the [reference table](#filter-codes-reference). |
| `openi: command not found` | Finish [section 2](#2-the-openi-terminal-command) (symlink onto PATH or `pip install .`). |

---

## Project layout

```
mcp-openi-server/
├── .claude-plugin/
│   ├── plugin.json      # Plugin manifest — makes this repo installable via `claude plugin install`
│   └── marketplace.json # Self-hosted marketplace listing the "openi" plugin (source: "./")
├── skills/
│   └── medical-image/
│       └── SKILL.md     # The `/openi:medical-image` skill (quick find + embed)
├── server.py            # MCP server (FastMCP, stdio) — the search "engine" for Claude Code
├── cli.py               # Standalone CLI implementation
├── openi                # Bash launcher so you can run `openi "…"` from anywhere
├── openi_client.py      # Shared core: API call + response parsing (used by both)
├── requirements.txt     # Runtime deps: mcp, httpx
├── pyproject.toml       # Packaging + `openi` console-script entry point
├── .mcp.json.example    # Template to auto-load the server per project in Claude Code (manual path)
├── LICENSE              # MIT
└── README.md            # This file
```

---

## License

MIT. Open-i content itself is subject to the terms of the U.S. National Library of Medicine — see <https://openi.nlm.nih.gov>.
