import httpx
import yaml
from fastmcp import FastMCP

# From OpenAPI spec
response = httpx.get("https://raw.githubusercontent.com/open-meteo/open-meteo/main/openapi.yml")
spec = yaml.safe_load(response.text)
mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=httpx.AsyncClient(base_url='https://api.open-meteo.com')
)

if __name__ == "__main__":
    mcp.run()