"""Minimal MCP server (PoC) for KNMI workshop.

Only one tool: `query_knmi_noordzee_weerstation`, modeled after the example.
Type hints and validation are intentionally omitted to keep it PoC-simple
and to demonstrate improvements when adding them later.
"""

import sqlite3
import time

from fastmcp import FastMCP


mcp = FastMCP("knmi-poc")

# NOTE: This PoC uses the example SQLite DB shipped in the repo.
# When running from `workshop/knmi`, this relative path points to it.
DB_PATH = "./data/knmi_etmgeg_320.sqlite"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row


@mcp.tool()
def query_knmi(sql):
    """Voer een (niet-gevalideerde) SQL-query uit op de voorbeeld-DB met KNMI-dagmetingen.

    PoC: geen read-only check of whitelist. Gebruik met zorg. Opdrachten breiden dit uit.
    Retourneert: { columns, rows, row_count, truncated, elapsed_ms }.
    """
    t0 = time.time()

    cur = conn.execute(sql.lower())
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    data = [[r[c] for c in cols] for r in rows]
    return {
        "columns": cols,
        "rows": data,
        "row_count": len(data),

        "elapsed_ms": int((time.time() - t0) * 1000),
    }

if __name__ == "__main__":
    mcp.run()
