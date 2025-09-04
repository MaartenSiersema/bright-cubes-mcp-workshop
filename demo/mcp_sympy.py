from __future__ import annotations
import sympy as sp
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("math")

@mcp.tool()
def simplify(expr: str) -> str:
    """
    Vereenvoudig een algebraïsche expressie.
    Voorbeeld: "3x + 5x - 2 + 7"
    """
    return str(sp.simplify(expr))

class SolveInput(BaseModel):
    equation: str  # bijv "x^2 - 4 = 0"
    symbol: str = "x"

@mcp.tool()
def solve(data: SolveInput) -> list[str]:
    """
    Los een vergelijking op naar 'symbol'.
    Voorbeeld: {"equation":"x^2 - 4 = 0", "symbol":"x"}
    """
    sym = sp.symbols(data.symbol)
    return [str(s) for s in sp.solve(sp.Eq(sp.sympify(data.equation.split('=')[0]),
                                           sp.sympify(data.equation.split('=')[1])), sym)]

if __name__ == "__main__":
    mcp.run()