# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a thin shim. **See [AGENTS.md](AGENTS.md) for the full guidance** — architecture, the
Entry-spine model, the SQLite-as-source-of-truth + derived-projections design, commands
(run / test / migrations), and the conventions/gotchas that matter when editing this code.

Quick pointers:
- Run: `.venv/bin/uvicorn main:app --reload` (http://127.0.0.1:8080, `/docs`)
- Test: `.venv/bin/python -m pytest tests/ -q`
- Roadmap: [future_implementations.md](future_implementations.md)
- API/class reference: [documentation.md](documentation.md)
