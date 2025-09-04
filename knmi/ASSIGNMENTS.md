---
created: 2025-09-01T08:25
updated: 2025-09-02T16:29
---
# KNMI MCP Workshop Assignments

Deze opdrachten bouwen voort op een PoC met één tool (`query_knmi_noordzee_weerstation`) zonder type hints en zonder validatie. Breid de functionaliteit stap voor stap uit. Werk incrementieel en documenteer kort je keuzes.

## Level 1 — Baseline
- Setup (uv): `cd knmi`; start de server met `uv run mcp_knmi.py`.
- Type hints: voeg type hints toe aan de toolparameters en returnwaarde, en leg uit waarom dit helpt (schema en validatie in clients).
- Query-tool: zorg voor eenvoudige LIMIT/OFFSET-handling en documenteer voorbeeldqueries.
- Veiligheid (basic): voeg een minimale read-only check toe (bv. `sql.strip().lower().startswith("select")`).
- Observability: voeg logging toe van duur en rij-aantal.

### Voorbeeldqueries (PoC) + valkuilen

Probeer deze queries via `query_knmi_noordzee_weerstation` op de voorbeeld-DB `etmgeg_320`:

- Ruwe rijen (tienden van graden C):
  `SELECT YYYYMMDD, TG FROM etmgeg_320 ORDER BY YYYYMMDD LIMIT 10`
- Temperatuur in °C voor 1990:
  `SELECT YYYYMMDD, TG/10.0 AS temp_c FROM etmgeg_320 WHERE YYYYMMDD BETWEEN '19900101' AND '19901231' ORDER BY YYYYMMDD`
- Maandgemiddelden (let op deling door 10):
  `SELECT substr(YYYYMMDD,1,6) AS ym, AVG(TG)/10.0 AS t_c FROM etmgeg_320 GROUP BY ym ORDER BY ym`
- Jaarlijks gemiddelde (voor trendanalyse):
  `SELECT CAST(substr(YYYYMMDD,1,4) AS INT) AS yr, AVG(TG)/10.0 AS t_c FROM etmgeg_320 GROUP BY yr ORDER BY yr`

Waarom dit niet altijd werkt in de PoC (bewust):
- Geen validatie: destructieve statements werken ook (bv. `DROP TABLE etmgeg_320`) en breken je omgeving.
- Geen whitelist: alles mag; ook queries op `sqlite_master` of `PRAGMA` die onverwachte resultaten of errors geven.
- Geen LIMIT/OFFSET.
- Sentinelwaarden: missings zijn `-9999`. Zonder filter beïnvloeden die `AVG`/`MIN`/`MAX` sterk. Voorbeeld filter: `WHERE TG > -9999`.
- Eenheden: veel kolommen zijn in tienden → deel door 10.0 voor SI-eenheden; zonder dit zijn grafieken/analyses misleidend.
- Resultaatvorm: geen schema/typing → sommige clients interpreteren waarden niet robuust (strings vs. getallen), en fouten zijn minder duidelijk.

Opdracht: Los bovenstaande valkuilen op door stapsgewijs types, validatie (minstens read‑only), robuuste LIMIT/OFFSET en datacleaning toe te voegen.

## Level 2 — Stations & Datum 
- Meerdere stations: voeg een tool toe `list_stations()` die unieke STN’s retourneert (uit SQLite of na migratie DuckDB).
- Datumfilters: Ondersteun eenvoudige datumfilters (YYYYMMDD) en documenteer voorbeeldqueries per station.
- Normalisatie: Zorg dat “tienden” (TG, TX, TN, etc.) correct omgerekend worden in voorbeelden.
- Voeg `summarize_temperature(start_date, end_date, station)` toe (avg/min/max °C).

## Level 3 — Trendanalyse 
- Jaartrends: Bereken jaarlijkse gemiddelde temperatuur per station en toon een 50-jaars trendchart (minimaal 1975–2024 of zo ver als data reikt).
- Trend: `trend_analysis(start_year, end_year, station)` — lineaire trend (°C/jaar) en chart.
- Validatie: Documenteer de SQL en verifieer outliers/NULL-afhandeling.

## Level 4 — Caching & Performance 
- Migratie (optioneel): migreer naar DuckDB met importscript en cache-strategie.
- Index/Views: Maak (indien zinvol) views of materialized strategieën voor snellere aggregaties.
- Robustness: Heldere foutmeldingen, schema-checks, en input-validatie.

## Level 5 — Integratie 
- OpenAPI: Integreer een (K)NMI/Open Data/Open Meteo endpoint en cache resultaten (SQLite of DuckDB).
- Visuals: Voeg hulp-tooling toe voor meerdere visualisaties (bv. moving average, min/max band, multi-station overlay).
- Testing: Voeg minimaal 2 unit-tests toe (bv. voor SQL-helper en trendberekening). Type-check en linter is een plus.

## Deliverables
- MCP-server die minimaal `query_knmi` levert en gaandeweg de TODO’s implementeert.
- DuckDB met meerdere stations en 50-jaarsperiode (zover mogelijk).
- Korte README-notities per team: hoe te runnen, voorbeeldcalls, eventuele keuzes/afwegingen.

## Tips
- Gebruik veilige SELECT-checks en afdwingbare `LIMIT`/`OFFSET`.
- Houd functions klein en focus op hergebruik (db-helper, chart util, config).
- Gebruik `demo/` ter inspiratie; bouw hier modulair en uitbreidbaar.
- Als OpenAPI integratie niet lukt: documenteer fallback en toon je ontwerp.
