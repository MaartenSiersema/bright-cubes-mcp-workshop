---
created: 2025-08-26T22:05
updated: 2025-08-29T14:45
---

# Best Practices voor MCP + FastMCP (Python)

Praktische richtlijnen om MCP-servers betrouwbaar, veilig en prettig bruikbaar te maken. Met voorbeelden, checklists en host-tips.

## 1) Protocol & outputdiscipline

- JSON-RPC: altijd `"jsonrpc": "2.0"` en matchende `id`.
- Tools-first: laat de LLM MCP-tools aanroepen, geen “vrije tekst”-acties.
- Content blocks: return exact `{"content": [...]}` zonder extra velden.
- Niet naar stdout loggen (stdout = protocol). Gebruik stderr/logging.

Workshop-context: met FastMCP hoef je zelden zelf JSON-RPC te schrijven—de lib doet dit voor je. Voor de workshop is het vooral belangrijk dat je toolresponses correct zijn (content blocks) en dat je niets naar stdout logt.

Voorbeeld response (success):
```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "result": { "content": [ { "type": "text", "text": "OK" } ] }
}
```

## 2) Toolontwerp & naming

- Duidelijke namen en beschrijvingen → betere toolselectie door de LLM.
- Kleine, idempotente tools met expliciete side-effects waar nodig.
- Beschrijf input duidelijk (beschrijvingen, ranges, voorbeelden).

### Functie-docstrings & comments

- Schrijf beknopte, actiegerichte docstrings per tool-functie. De eerste regel is een korte samenvatting; daarna context, parameters, returnvorm en fouten.
- Gebruik docstrings ook als bron voor de tool-omschrijving (veel hosts tonen deze bij `tools/list`).
- Geef voorbeelden (voorbeeld-aanroep en typische output) om de LLM te sturen.
- Commentaar focust op het waarom en randvoorwaarden; vermijd obvious “wat”-comments.

Voorbeeld (docstring + comments):
```python
from fastmcp import tool, MCPError
from pydantic import BaseModel, Field

class QueryArgs(BaseModel):
    sql: str = Field(..., description="ALLEEN SELECT-query")
    limit: int = Field(200, ge=1, le=10_000, description="Maximaal aantal rijen")
    offset: int = Field(0, ge=0, description="Verschuiving voor paging")

@tool(app, name="query_sql", args_model=QueryArgs)
def query_sql(args: QueryArgs) -> dict:
    """Voer een veilige SELECT-query uit op de dataset.

    Doel: snelle, leesbare dataretrieval met basisbeperkingen (alleen SELECT).

    Args:
      args.sql: SQL die met 'SELECT' begint (verplicht).
      args.limit: Limiet op rijen (1–10.000).
      args.offset: Offset voor paging.

    Returns:
      content: lijst met content blocks met een `text`-samenvatting en (optioneel)
        een `resource`-verwijzing als het resultaat groot is.

    Raises:
      MCPError: bij ongeldige/gevaarlijke query of uitvoerfout.

    Voorbeeld:
      name: query_sql
      arguments: {"sql": "SELECT * FROM knmi LIMIT 5"}
    """
    # Waarom-check: alleen SELECT is toegestaan; voorkom mutaties/DDL.
    if not args.sql.strip().lower().startswith("select"):
        raise MCPError(code=-32001, message="Alleen SELECT-queries toegestaan")

    # TODO: whitelist tabellen/kolommen (least privilege) indien nodig.
    rows = run_sqlite(args.sql, limit=args.limit, offset=args.offset)  # bestaande helper

    summary = f"{len(rows)} rijen opgehaald. LIMIT={args.limit}, OFFSET={args.offset}."
    return {"content": [{"type": "text", "text": summary}]}  # resource voor grote outputs
```

Richtlijnen samengevat:
- Eerste docstring-regel = korte samenvatting; daarna details/voorbeelden.
- Documenteer inputbereik en side-effects (indien aanwezig).
- Houd comments schaars maar betekenisvol (constraints, keuzes, valkuilen).

## 3) Validatie & schema’s (Pydantic)

Gebruik Pydantic voor type- en vormcontrole. Voeg zo nodig extra validators toe.

```python
from pydantic import BaseModel, field_validator, ValidationError

class QueryModel(BaseModel):
    sql: str
    limit: int = 200
    offset: int = 0

    @field_validator("sql")
    @classmethod
    def must_start_with_select(cls, v: str):
        if not v.strip().lower().startswith("select"):
            raise ValueError("Alleen SELECT-queries toegestaan")
        return v

def handle_query(sql: str, limit: int = 200, offset: int = 0):
    try:
        params = QueryModel(sql=sql, limit=limit, offset=offset)
    except ValidationError as e:
        return {"content": [{"type": "text", "text": f"Inputfout: {e}"}]}
    # … voer veilige query uit …
```

## 4) Content blocks: text, image, resource

- Afbeeldingen: base64 in `image.data` + altijd `mimeType` (bijv. `image/png`).
- Altijd ook een tekst-fallback meesturen.
- Grotere resultaten → gebruik `resource` (bestands-URI) i.p.v. megabytes base64.

Voorbeeld (image + text):
```python
return {"content": [
  {"type": "text", "text": "Grafiek gegenereerd."},
  {"type": "image", "mimeType": "image/png", "data": base64_png}
]}
```

Resource fallback:
```python
return {"content": [
  {"type": "text", "text": "Chart opgeslagen als bestand."},
  {"type": "resource", "uri": file_uri, "mimeType": "image/png"}
]}
```

## 5) Foutafhandeling & status

- Gooi protocolconforme fouten (bv. `MCPError`) of geef duidelijke tekst terug.
- Gebruik waar mogelijk progress/log-notifications (host-afhankelijk).

```python
from fastmcp import MCPError

def risky():
    raise MCPError(code=-32000, message="Iets ging mis")
```

## 6) Logging & observability

- Configureer logging naar stderr met niveau en formatter.
- Log per call: request_id, duur (ms), status, relevante parameters.

```python
import logging, time, uuid
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def with_logging(fn):
    def wrap(*a, **kw):
        rid = str(uuid.uuid4())
        t0 = time.perf_counter()
        try:
            logging.info(f"start rid={rid} fn={fn.__name__} args={kw}")
            out = fn(*a, **kw)
            ms = int((time.perf_counter()-t0)*1000)
            logging.info(f"done  rid={rid} ms={ms}")
            return out
        except Exception as e:
            ms = int((time.perf_counter()-t0)*1000)
            logging.exception(f"fail  rid={rid} ms={ms} err={e}")
            raise
    return wrap
```

### 6b) MCP Interceptor/Inspector (FastMCP dev)

Gebruik de (dev) interceptor/inspector om protocolverkeer inzichtelijk te maken tijdens ontwikkeling en demo’s. Handig voor:
- Testen: zie exacte `tools/call` requests en `result`/`error` responses
- Debuggen: valideer `content`-structuur, ids, timings
- Auditing: log ruwe JSON met tijdstempels (let op: pseudonimiseer indien nodig)

Inschakelen
- Als jouw FastMCP-versie dev/inspectie ondersteunt: zet de dev-modus aan (bijv. via een dev‑flag of env‑variabele) en activeer de MCP‑interceptor. Raadpleeg de versie‑docs; implementaties verschillen.
- Alternatief: voeg een eenvoudige tracer toe die alle toolcalls logt (zie decorator hierboven) en, indien beschikbaar, hook in op protocol-events.

Starten met uv (dev)
- Variant A (CLI entrypoint):
  ```bash
  uv run fastmcp dev --app mcp_server.py
  ```
- Variant B (module-invoer):
  ```bash
  uv run python -m fastmcp dev --app mcp_server.py
  ```
- Variant C (env‑flag binnen je eigen script):
  ```bash
  FASTMCP_DEV=1 uv run python mcp_server.py
  ```

Let op
- De exacte CLI‑vlaggen (bijv. `--app`, `--stdio`/`--http`) kunnen per versie verschillen. Check je geïnstalleerde FastMCP‑help (`uv run fastmcp --help`).
- Houd de dev/inspector alleen lokaal/ontwikkelgericht; bevat vaak uitgebreide logs.

Generiek tracer‑patroon (pas aan aan jouw versie):
```python
import json, logging

def on_protocol(direction: str, payload: dict):
    # direction: "in" (client→server) of "out" (server→client)
    logging.info("proto %s: %s", direction, json.dumps(payload, ensure_ascii=False)[:5000])

# Voorbeeld: als de lib een interceptor ondersteunt
# app.set_protocol_interceptor(on_protocol)  # pseudocode, check jouw FastMCP-versie
```

Tips
- Log naar stderr/bestand; niet naar stdout.
- Redigeer gevoelige payloads indien nodig (API‑keys, PII).
- Combineer met request_id/timings uit de logging‑decorator voor complete traces.

## 7) Performance & caching (DuckDB)

- Cache herhaal-queries met een sleutel op SQL + parameters.
- Simpele TTL (bijv. 5–10 min) en handmatige invalidatie bij schemawijziging.

Mini-cache helper:
```python
import duckdb, hashlib, json, time

class DuckDBCache:
    def __init__(self, path="cache.duckdb", ttl_seconds=600):
        self.db = duckdb.connect(path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS cache_json (
              key TEXT PRIMARY KEY,
              payload JSON NOT NULL,
              created_at BIGINT NOT NULL
            )
        """)
        self.ttl = ttl_seconds

    def key(self, *, sql, limit, offset, params=None):
        blob = json.dumps({"sql": sql, "limit": limit, "offset": offset, "params": params}, sort_keys=True)
        return hashlib.sha1(blob.encode()).hexdigest()

    def get(self, k):
        row = self.db.execute("SELECT payload, created_at FROM cache_json WHERE key=?", [k]).fetchone()
        if not row: return None
        payload, created_at = row
        if time.time() - int(created_at) > self.ttl:
            self.db.execute("DELETE FROM cache_json WHERE key=?", [k])
            return None
        return json.loads(payload)

    def set(self, k, rows):
        self.db.execute("INSERT OR REPLACE INTO cache_json VALUES (?, ?, ?)", [k, json.dumps(rows), int(time.time())])
```

## 8) Security & governance

Risico’s: prompt injection, tool poisoning, sessiekaping, RCE/credential theft.

Mitigaties:
- Least privilege, duidelijke tool-policy en whitelists.
- Unieke toolnamen; valideer input (Pydantic, regex, ranges).
- Resource-URI’s: geen gevoelige paden; gebruik temp-dirs.
- Beveilig HTTP/SSE: auth, CORS, TLS, rate-limits (indien van toepassing).
- Geen logs naar stdout; beperk gevoelige data in logs.

Project/bot-constraints (aanbevolen in copilot-instructions):
- ALLEEN data via de goedgekeurde MCP-tools.
- GEEN externe databronnen of API’s.
- GEEN aannames over data die niet expliciet door MCP-tools wordt geleverd.
- GEEN hardcoded (weer)data of statistieken.

## 9) Testen

- Unit: roep tool-functies direct aan met Pydantic-args; assert content-structuur.
- Protocol: start server; stuur JSON-RPC; controleer `jsonrpc/id/result` vs `error`.
- Sanity: kleine NL-opdracht (“Leg kort RAG uit”) om host/instellingen te checken.

## 10) System prompts & copilot-instructions

System prompt (tools-first, NL):
```text
Je bent een tool-using agent. Gebruik MCP-tools waar mogelijk.
Antwoord NIET met vrije tekst voor acties die een tool vereisen.
Gebruik uitsluitend geldige tool-calls (MCP/JSON-RPC).
Houd output strikt aan de gevraagde structuur. Antwoord in het Nederlands.
Vraag door bij ambiguïteit.
```

`copilot-instructions.md` (plaats in projectroot):
```markdown
# Copilot Instructions
- Taal: Nederlands, beknopt.
- Tools-first: roep MCP-tools aan i.p.v. vrije tekst bij acties.
- JSON-RPC strikt: valide JSON, juiste id, content blocks correct.
- Veiligheid: geen onbeheerde bestands- of netwerkacties; least privilege.
- Validatie: houd je aan Pydantic-schema’s; geef duidelijke fouten terug.
- Images: altijd base64 data + mimeType, plus tekst-fallback.
- Grote outputs: resource-URI i.p.v. base64 > ~1–5MB.
- ALLEEN data via goedgekeurde MCP-tools; GEEN externe API’s.
- GEEN aannames buiten tool-output; GEEN hardcoded (weer)statistieken.
```

## 11) Host/IDE-tips (LM Studio e.a.)

- Temperature: 0.2 (tools/JSON) of 0.5 (gewone chat).
- Top-p: 0.9 • Top-k: 40 • Repeat penalty: 1.1–1.2.
- Context: 8k is vaak genoeg; voorkom afkappen van prompts.
- “Stop at EOS” aan. Voor tools: “Structured/JSON output” en “prefer/force tools”.
- Veelvoorkomende issues en fixes:
  - Verkeerd chat-template → kies “Meta Llama 3 Instruct”.
  - Te hoge temperatuur → variatie/hallucinaties.
  - Te lange/ruisige context → knip irrelevants weg.
  - Mix van talen → voeg “antwoord in het Nederlands” toe.
  - RAG/plug-in voegt tekst vóór user prompt → controleer preprocessor/plug-ins.

## 12) Quickstart (uv)

```bash
uv init
uv add fastmcp duckdb pydantic matplotlib
uv run python mcp_server.py
```

`pyproject.toml`:
```toml
[project]
name = "mcp-server"
version = "0.1.0"
dependencies = [
  "fastmcp",
  "duckdb",
  "pydantic",
  "matplotlib",
]
[tool.uv]
python = "3.11"
```

## 13) Kleine workflow-checklist

- [ ] Heldere toolnamen + beschrijvingen
- [ ] Pydantic-schema’s met validators
- [ ] Strict JSON-RPC + content blocks
- [ ] Text-fallback bij image; resource voor groot
- [ ] Logging naar stderr; request_id + duur
- [ ] Cache (TTL) voor herhaal-queries (DuckDB)
- [ ] Security-policies (least privilege, whitelists)
- [ ] System prompt + copilot-instructions aanwezig

## 14) Copilot-configuratie (MCP‑servers)

Configureer in Copilot (VS Code/IDE) welke MCP‑servers beschikbaar zijn. De exacte bestandslocatie/keys verschillen per versie/host; onderstaand voorbeeld laat het gangbare `mcpServers`‑blok zien. Kies per server een `command` + `args` en (optioneel) `env`.

Voorbeeld (npx Playwright + eigen FastMCP via uv):
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"]
    },
    "mijn-fastmcp": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "env": { "FASTMCP_DEV": "1" }
    }
  }
}
```

Alternatief met `uvx` en FastMCP‑CLI in dev‑modus:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"]
    },
    "mijn-fastmcp": {
      "command": "uvx",
      "args": ["fastmcp", "dev", "--app", "mcp_server.py"]
    }
  }
}
```

Tips
- Gebruik (indien ondersteund) een werkdirectory/cwd als je server afhankelijk is van lokale bestanden.
- Voeg `env`‑variabelen toe voor dev/inspectie (`FASTMCP_DEV=1`) of secrets (liever via OS‑keychain/IDE secret store).
- Controleer de help van je host: waar moet dit JSON‑blok staan en welke extra velden (zoals `cwd`) worden ondersteund.
