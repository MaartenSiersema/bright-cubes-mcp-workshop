"""
FastMCP — fetch external page via httpx and convert HTML to Markdown

Usage:
  uv pip install httpx markdownify
  uv run examples/mcp_fetch_httpx.py

Call:
  name: fetch_markdown, arguments: {"url": "https://example.com", "max_chars": 3000}
"""
from fastmcp import FastMCP
import httpx
from markdownify import markdownify as md

app = FastMCP(name="fetch-md-httpx", version="0.1.0")


@app.tool()
def fetch_markdown(url: str, timeout_sec: float = 15.0, max_chars: int = 4000) -> dict:
    with httpx.Client(follow_redirects=True, timeout=timeout_sec) as client:
        resp = client.get(url)
        resp.raise_for_status()
        text = md(resp.text)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...afgekapt voor demo...]\n"
    return {"content": [{"type": "text", "text": text}]}


if __name__ == "__main__":
    app.run()

