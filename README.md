

Installeer Python mocht je de runtime nog niet hebben. Volg de instructies via de onderstaande link:

https://realpython.com/installing-python/


Installeer vervolgens `uv` voor het opzetten van een virtuele python environment. Dit kan op meerdere manieren zie:

https://docs.astral.sh/uv/getting-started/installation/


In de demo map kun je mcp servers runnen met mcp interceptor door 

```bash
# bij gebruik van fastmcp via mcp
uv run mcp dev mcp_meteo.py

# bij gebruik van fastmcp via FastMCP
uv run fastmcp dev mcp_knmi_local.py
```

De mcp package is de officiële implementatie van het Model Context Protocol, en bevat o.a. fastmcp als submodule om eenvoudig MCP-servers te bouwen.
De fastmcp package daarentegen is een losse, standalone distributie van diezelfde functionaliteit, handig als je alleen FastMCP nodig hebt zonder de hele mcp toolchain.
Kort gezegd: mcp[fastmcp] = compleet pakket inclusief CLI en protocol, fastmcp = lightweight install voor alleen de server-bouwkit.

Let op dat de api voor beide libraries kan afwijken


---
Meer info:

https://modelcontextprotocol.io/docs/getting-started/intro
https://gofastmcp.com/getting-started/welcome
