# Copilot Instructions
- Taal: Nederlands, beknopt.
- Tools-first: roep MCP-tools aan i.p.v. vrije tekst bij acties.
- JSON-RPC strikt: valide JSON, juiste id, content blocks correct.
- Veiligheid: geen onbeheerde bestands- of netwerkacties; least privilege.
- Validatie: houd je aan schema’s; geef duidelijke fouten terug.
- Images: altijd base64 data + mimeType, plus tekst-fallback.
- Grote outputs: resource-URI i.p.v. base64 > ~1–5MB.
- ALLEEN data via goedgekeurde MCP-tools; GEEN externe API’s.
- GEEN aannames buiten tool-output; GEEN hardcoded (weer)statistieken.