# Second Brain

A local-first knowledge assistant prototype.

## Features
- Markdown keyword and semantic retrieval.
- Local Qwen3 answers through Ollama.
- Cached nomic-embed-text embeddings.
- Source references and citation-label checks.
- Strict excerpt selection with text supplied by Python.
- Claude Desktop integration through MCP.
- Reviewed memory proposals and approvals.
- PDF text import and manual version refresh.
- Obsidian-compatible notes and links.

## Setup
Requires Python 3.13 and local Ollama.

    python3.13 -m venv .venv-mcp
    source .venv-mcp/bin/activate
    python -m pip install -r requirements.txt
    ollama pull qwen3:1.7b
    ollama pull nomic-embed-text

If my-vault is absent, copy the fictional examples:

    cp -R sample-vault my-vault

## Try it

    python ask.py "Which model generates local answers?"
    python strict_ask.py "How are citation labels checked?"

## Validation

    python -m unittest discover -v
    python evaluate.py

Six automated tests cover starter indexing, search, graph behavior, and PDF refresh, including changed text, unchanged files, and missing PDFs.
The evaluation compares retrieval on five fictional examples.
It is not a general accuracy benchmark.

## MCP
brain_mcp.py exposes list_notes and search_notes over stdio.
Configure the host with absolute Python and server paths.
Claude receives the passages returned by these tools.

## Limits
- Citation labels do not establish claim support.
- Strict mode can select irrelevant excerpts.
- The dollar-amount guard is narrowly scoped.
- PDF extraction may lose layout and table structure.
- PDF refresh is manual; same-named PDFs are treated as versions.
- Scanned documents need a separate OCR stage.
- Source facts require manual updates.
- Notes and databases lack application-level encryption.

Only fictional example notes are included.
Personal data folders and environments are excluded from Git.
