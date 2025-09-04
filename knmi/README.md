---
created: 2025-09-01T08:25
updated: 2025-09-02T16:24
---
# KNMI MCP Workshop (Team Edition)

Doel: PoC-startpunt voor teams (~4 p.) om een MCP-tooling voor KNMI-data uit te werken. We starten super-minimaal met één tool, zonder type hints en zonder validatie, en bouwen via opdrachten stap voor stap uit.

Belangrijke randvoorwaarden:
- Laat de bestaande voorbeelden in `examples/` intact. Deze map is losstaand voor de workshopopdrachten.
- Pas de presentatie of sidenotes nog niet aan.
- Richt je op best practices: modulair, type hints, docstrings, configuratie, logging, duidelijke error-afhandeling, pure SELECT-queries, en reproduceerbare resultaten.

Onderdelen in deze map:
- `ASSIGNMENTS.md` — opdrachten en uitbreidingen (zonder puntentelling).
- `pyproject.toml` — projectmetadata en dependencies voor uv.
- `knmi_mcp/` — minimale MCP-server met één tool.

Snel starten (uv):
1) Ga naar de map: `cd workshop/knmi`
2) Installeer dependencies: `uv sync`
3) Start de MCP-server: `uv run knmi-mcp` (of `uv run python -m knmi_mcp.server`)
   - De server gebruikt de voorbeeld SQLite DB: `../../examples/data/knmi_etmgeg_320.sqlite`.
4) Koppel je MCP-client (Claude Desktop, MCP Inspector, etc.).
5) Werk de opdrachten in `ASSIGNMENTS.md` af; bouw validatie, charts, meerdere stations en (optioneel) DuckDB-ondersteuning stap voor stap in.

Tip: Gebruik `examples/` als referentie; het PoC hier is bewust minimaal (geen type hints, geen validatie). Opdrachten vragen je o.a. om type hints, validatie, LIMIT/OFFSET-handling, visualisaties en (optioneel) overschakeling naar DuckDB te implementeren.

Ideeën voor een licht competitief element zonder puntentelling:
- “Eerste tot Level 3” badge: welk team levert als eerste een correcte trendanalyse (inclusief chart)?
- Peer review: teams reviewen elkaars aanpak (structuur, validatie, reproduceerbaarheid) en stemmen op “meest robuuste oplossing”.
- Reproduceerbaarheid: willekeurige her-run door trainer — teams met foutloze runs verdienen een shout‑out.
