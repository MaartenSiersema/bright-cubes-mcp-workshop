import httpx
from fastmcp import FastMCP

# KNMI API configuratie
API_KEY = "eyJvcmciOiI1ZTU1NGUxOTI3NGE5NjAwMDEyYTNlYjEiLCJpZCI6IjMwZmU0ZWVjNjJkODQzOWRiZTMyZGNlZjAzNWNhNDVmIiwiaCI6Im11cm11cjEyOCJ9"
BASE_URL = "https://api.dataplatform.knmi.nl/edr/v1"

# Maak een simpele MCP server
mcp = FastMCP("knmi-weather")

@mcp.tool()
def get_collections() -> dict:
    """Haal alle beschikbare KNMI weather collections op
    
    Beschikbare collecties:
    - 'observations-1-minute': 1-minuut observaties (2024-heden)  
    - 'observations-10-minute': 10-minuut observaties (2012-heden)
    - 'observations-hourly': Uurlijkse observaties (1951-heden)
    - 'daily-in-situ-meteorological-observations-validated': Dagelijkse observaties gevalideerd (1901-heden) ⭐ AANBEVOLEN
    - 'Tg1_grid': Temperatuur grid data (1951-heden)
    - 'Rd1_grid': Neerslag grid data (1951-heden) 
    - 'EV24_grid': Verdamping grid data (1951-heden)
    - 'WINS50': Wind data voor energie (2019-2021)
    """
    response = httpx.get(f"{BASE_URL}/collections", headers={"Authorization": API_KEY})
    return response.json()

@mcp.tool()
def get_locations(collection_id: str = "daily-in-situ-meteorological-observations-validated") -> dict:
    """Haal alle weerstation locaties op voor een collectie
    
    Args:
        collection_id: Collectie ID (zie get_collections voor opties)
        
    Populaire collection_ids:
    - 'daily-in-situ-meteorological-observations-validated': Dagelijkse data (AANBEVOLEN)
    - 'observations-10-minute': 10-minuut real-time data
    - 'observations-hourly': Uurlijkse gevalideerde data
    
    Belangrijke station_ids (location_ids):
    - '06260': De Bilt (KNMI hoofdstation)
    - '06380': Maastricht Airport  
    - '06240': Schiphol Airport
    - '06344': Rotterdam Airport
    - '06290': Twenthe Airport
    - '06280': Eelde (Groningen Airport)
    - '06310': Vlissingen
    - '06330': Hoek van Holland
    """
    response = httpx.get(f"{BASE_URL}/collections/{collection_id}/locations", headers={"Authorization": API_KEY})
    return response.json()

@mcp.tool()
def get_weather_data(
    collection_id: str = "daily-in-situ-meteorological-observations-validated",
    location_id: str = "06380",  # Maastricht
    datetime_range: str = "2000-01-01/2025-01-01",
    parameter_name: str = "TG"  # Daily mean temperature
) -> dict:
    """Haal weerdata op voor een specifiek station en periode
    
    Args:
        collection_id: Collectie ID (zie get_collections)
        location_id: Station ID (zie get_locations) 
        datetime_range: Datumbereik "YYYY-MM-DD/YYYY-MM-DD"
        parameter_name: Parameter code (zie onderstaande lijst)
        
    Belangrijkste parameter codes voor dagelijkse data:
    
    🌡️ TEMPERATUUR:
    - TG: Gemiddelde temperatuur (°C * 10)
    - TN: Minimum temperatuur (°C * 10)  
    - TX: Maximum temperatuur (°C * 10)
    - T10N: Minimum temperatuur op 10cm hoogte (°C * 10)
    
    🌧️ NEERSLAG:
    - RH: Dagelijkse neerslagsom (mm * 10)
    - RHX: Maximum uurlijkse neerslag (mm * 10)
    - PG: Gemiddelde luchtdruk (hPa * 10)
    - PX: Maximum luchtdruk (hPa * 10)
    - PN: Minimum luchtdruk (hPa * 10)
    
    💨 WIND:
    - FG: Gemiddelde windsnelheid (m/s * 10)
    - FHX: Maximum uurgemiddelde windsnelheid (m/s * 10)  
    - FXX: Maximum windstoot (m/s * 10)
    - DG: Gemiddelde windrichting (graden)
    - DDX: Windrichting bij FXX (graden)
    
    ☀️ ZON & STRALING:
    - SQ: Zonschijnduur (uren * 10)
    - SP: Percentage mogelijke zonschijn (%)
    - Q: Globale straling (J/cm²)
    
    💧 VOCHTIGHEID & ZICHT:
    - UG: Gemiddelde relatieve vochtigheid (%)
    - UX: Maximum relatieve vochtigheid (%)
    - UN: Minimum relatieve vochtigheid (%)
    - VVN: Minimum zicht (km)
    - VVX: Maximum zicht (km)
    - NG: Gemiddelde bewolkingsgraad (okta's)
    
    🌫️ WEERFENOMENEN (uren per dag):
    - M: Mist
    - R: Regen  
    - S: Sneeuw
    - O: Onweer
    - Y: IJsvorming
    
    NOTA: Temperatuur en neerslag waarden zijn * 10 (deel door 10 voor echte waarde)
    """
    params = {
        "datetime": datetime_range,
        "parameter-name": parameter_name,
        "f": "CoverageJSON"
    }
    response = httpx.get(
        f"{BASE_URL}/collections/{collection_id}/locations/{location_id}",
        headers={"Authorization": API_KEY},
        params=params
    )
    return response.json()

if __name__ == "__main__":
    mcp.run()