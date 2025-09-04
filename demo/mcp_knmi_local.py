# server.py
import base64, io, sqlite3, time
from pydantic import Field
from typing import Optional, Dict, Any, Annotated

import matplotlib
from fastmcp import FastMCP

matplotlib.use("Agg")            # headless
import matplotlib.pyplot as plt  # geen kleuren instellen -> LLM-vriendelijk

mcp = FastMCP("db-tools")

# Demo DB
conn = sqlite3.connect("data/knmi_etmgeg_320.sqlite", check_same_thread=False)
conn.row_factory = sqlite3.Row
ALLOWED_TABLES = {"etmgeg_320"}
MAX_LIMIT = 1000
DEFAULT_LIMIT = 200

def _is_safe_select(sql: str) -> bool:
    s = sql.strip().lower()
    return s.startswith("select") and "pragma" not in s and ";" not in s

def _enforce_limit(sql: str, limit: int) -> str:
    return sql if " limit " in sql.lower() else f"{sql}\nLIMIT {limit}"

@mcp.tool()
def query_knmi_noordzee_weerstation(
        sql: Annotated[str, Field(description="Read-only SELECT SQL query")],
        limit: Annotated[int, Field(description="Maximum number of rows to return", ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
        offset: Annotated[int, Field(description="Row offset for pagination", ge=0)] = 0
) -> dict:
    """
    Voer een read-only SELECT uit op de tabel `etmgeg_320` met dagelijkse meteorologische metingen
    van KNMI-weerstation 320 (De Bilt).

    Beschikbare kolommen en betekenis (eenheden conform KNMI-formaat):
    - STN        : Stationnummer (320 = De Bilt)
    - YYYYMMDD   : Datum in JJJJMMDD-formaat (tekst, bijv. '20250113')
    - DDVEC      : Gemiddelde windrichting (0–360 graden, 0 = noord)
    - FHVEC      : Uurgemiddelde windsnelheid vector (in 0.1 m/s)
    - FG         : Gemiddelde windsnelheid over de dag (in 0.1 m/s)
    - FHX        : Hoogste uurgemiddelde windsnelheid (in 0.1 m/s)
    - FHXH       : Uurvak waarin FHX gemeten is (UTC)
    - FHN        : Laagste uurgemiddelde windsnelheid (in 0.1 m/s)
    - FHNH       : Uurvak waarin FHN gemeten is (UTC)
    - FXX        : Hoogste windstoot (in 0.1 m/s)
    - FXXH       : Uurvak waarin FXX gemeten is (UTC)
    - TG         : Etmaalgemiddelde temperatuur (in 0.1 °C)
    - TN         : Minimumtemperatuur (in 0.1 °C)
    - TNH        : Uurvak waarin TN gemeten is (UTC)
    - TX         : Maximumtemperatuur (in 0.1 °C)
    - TXH        : Uurvak waarin TX gemeten is (UTC)
    - T10N       : Minimumtemperatuur op 10 cm hoogte (in 0.1 °C)
    - T10NH      : Uurvak waarin T10N gemeten is (UTC)
    - SQ         : Zonneschijnduur (in 0.1 uur)
    - SP         : Percentage van de langst mogelijke zonneschijnduur (%)
    - Q          : Globale straling (in J/cm²)
    - DR         : Duur van neerslag (in 0.1 uur)
    - RH         : Etmaalsom van neerslag (in 0.1 mm)
    - RHX        : Hoogste uurlijkse neerslagintensiteit (in 0.1 mm/u)
    - RHXH       : Uurvak waarin RHX gemeten is (UTC)
    - PG         : Gemiddelde luchtdruk op zeeniveau (in 0.1 hPa)
    - PX         : Hoogste luchtdruk op zeeniveau (in 0.1 hPa)
    - PXH        : Uurvak waarin PX gemeten is (UTC)
    - PN         : Laagste luchtdruk op zeeniveau (in 0.1 hPa)
    - PNH        : Uurvak waarin PN gemeten is (UTC)
    - VV         : Gemiddelde bewolking (code 0–9, 9 = geheel bewolkt)
    - NG         : Gemiddelde hoeveelheid bewolking (in achtsten, 0–8)
    - UG         : Gemiddelde relatieve vochtigheid (%)
    - UX         : Hoogste relatieve vochtigheid (%)
    - UXH        : Uurvak waarin UX gemeten is (UTC)
    - UN         : Laagste relatieve vochtigheid (%)
    - UNH        : Uurvak waarin UN gemeten is (UTC)
    - EV24       : Referentiegewasverdamping (in 0.1 mm, Makkink-formule)

    Waarden in tienden moeten gedeeld worden door 10 om naar SI-eenheden om te rekenen.
    Waarden met -9999 duiden op ontbrekende data.

    Richtlijnen voor gebruik:
    - Voer alleen **SELECT** queries uit.
    - Beperk het aantal rijen met `LIMIT` (maximaal 1000 aanbevolen).
    - Gebruik filters zoals `WHERE YYYYMMDD BETWEEN '20240101' AND '20241231'`
      of `WHERE TG > 200` (d.w.z. > 20.0°C).
    - Voor trends en samenvattingen gebruik aggregaties (`AVG`, `MAX`, `MIN`, `SUM`).
    - Combineer kolommen voor analyse, bijvoorbeeld gemiddelde temperatuur per maand:
      `SELECT substr(YYYYMMDD,1,6) AS maand, AVG(TG)/10.0 AS temp_c FROM etmgeg_320 GROUP BY maand`.

    Retourneert een JSON-object met:
    - columns: lijst van kolomnamen
    - rows: lijst van rijen (waarden)
    - row_count: aantal geretourneerde rijen
    - truncated: true als de query door LIMIT afgekapt is
    - elapsed_ms: tijd in milliseconden die de query duurde
    """
    start = time.time()
    if not _is_safe_select(sql):
        return {"error": "Only read-only SELECT statements are allowed."}

    # (Eenvoudige check; voor productie liever SQL parser gebruiken)
    lowered = sql.lower()
    if " from " in lowered and not any(f" {t} " in lowered for t in ALLOWED_TABLES):
        return {"error": "Query references non-whitelisted tables."}

    limit = min(max(1, int(limit)), MAX_LIMIT)
    q = _enforce_limit(sql, limit)
    if offset and " offset " not in q.lower():
        q = f"{q} OFFSET {int(offset)}"

    cur = conn.execute(q)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    data = [[r[c] for c in cols] for r in rows]
    return {
        "columns": cols,
        "rows": data,
        "row_count": len(data),
        "truncated": len(data) >= limit,
        "elapsed_ms": int((time.time() - start) * 1000),
    }

@mcp.tool()
def line_chart_sql(
        sql: str,
        x_col: str,
        y_col: str,
        title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Maak een **lijnchart** (PNG, base64) vanuit een **read-only SELECT** op de SQLite-db.
    Gebruik op de KNMI-tabel `etmgeg_320` (dagmetingen).
    Voorbeeld: gemiddelde temperatuur per maand:
      sql="SELECT substr(YYYYMMDD,1,6) AS ym, AVG(TG)/10.0 AS t_c FROM etmgeg_320 GROUP BY ym ORDER BY ym"
      x_col="ym", y_col="t_c", title="Gem. dagtemp (°C) per maand"
    Richtlijnen:
    - Alle **waarden in tienden** (zoals TG, TX, TN) eerst delen door 10 om °C/mm/hPa te krijgen.
    - Alleen **SELECT**; LIMIT wordt afgedwongen (max ~5000 rijen).
    Retourneert: { "image_base64": "...", "mime": "image/png", "width": int, "height": int, "row_count": int, "elapsed_ms": int }
    """
    if not _is_safe_select(sql):
        return {"error": "Only read-only SELECT statements are allowed."}

    sql_q = _enforce_limit(sql, MAX_LIMIT)

    t0 = time.time()
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql_q)
    rows = cur.fetchall()
    if not rows:
        return {"error": "Query returned no rows."}

    # haal kolommen
    cols = [d[0] for d in cur.description]  # type: ignore
    if x_col not in cols or y_col not in cols:
        return {"error": f"Columns not in result. Available: {cols}"}

    x = [r[x_col] for r in rows]
    y = [r[y_col] for r in rows]

    # eenvoudige plot
    fig = plt.figure(figsize=(8, 4.5), dpi=150)
    ax = plt.gca()
    ax.plot(x, y)              # geen kleuren instellen
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    if title:
        ax.set_title(title)
    fig.tight_layout()

    # naar PNG (base64)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    img_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "image_base64": img_b64,
        "mime": "image/png",
        "width": 1200,
        "height": 675,
        "row_count": len(rows),
        "elapsed_ms": int((time.time() - t0) * 1000),
    }


@mcp.tool()
def summarize_temperature(
        start_date: Annotated[str, Field(description="Start date in 'YYYYMMDD' format", pattern=r"^\d{8}$")],
        end_date: Annotated[str, Field(description="End date in 'YYYYMMDD' format", pattern=r"^\d{8}$")]
) -> Dict[str, Any]:
    """
    Compute summary temperature statistics (average, minimum, and maximum) for the daily temperature
    between `start_date` and `end_date` inclusive. Temperatures are returned in degrees Celsius (°C).
    """
    if end_date < start_date:
        return {"error": "end_date must be greater than or equal to start_date."}

    query = """
            SELECT AVG(TG)/10.0 AS avg_temp_c,
                   MIN(TN)/10.0 AS min_temp_c,
                   MAX(TX)/10.0 AS max_temp_c
            FROM etmgeg_320
            WHERE YYYYMMDD BETWEEN ? AND ? \
            """

    t0 = time.time()
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, (start_date, end_date))
    row = cur.fetchone()
    if not row or row["avg_temp_c"] is None:
        return {"error": "No data for specified date range."}

    return {
        "avg_temp_c": row["avg_temp_c"],
        "min_temp_c": row["min_temp_c"],
        "max_temp_c": row["max_temp_c"],
        "elapsed_ms": int((time.time() - t0) * 1000),
    }

if __name__ == "__main__":
    mcp.run()
