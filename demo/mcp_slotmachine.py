# slot_mcp.py
# MCP server met stateful slotmachine: kosten per spin en uitbetaling op score.
# Run: uvx mcp dev slot_mcp.py   (of: python slot_mcp.py)

import random
from typing import Tuple, Optional
from pydantic import BaseModel, Field, conint
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("slot-machine")

# ----------------------------
# Game config
# ----------------------------
SYMBOLS = ["◻️", "◻️", "◻️", "🍒", "🍋", "🍊", "🍇", "💎"]
SPIN_COST = 2  # kosten per spin (credits)

# Score zoals in je Swift-voorbeeld
def score_reels(reels: Tuple[str, str, str]) -> int:
    r1, r2, r3 = reels
    if (r1, r2, r3) == ("💎", "💎", "💎"):
        return 100
    if (r1, r2, r3) == ("🍒", "🍒", "🍒"):
        return 10
    if (r1, r2, r3) == ("🍇", "🍇", "🍇"):
        return 5
    if (r1, r2, r3) == ("🍊", "🍊", "🍊"):
        return 3
    if (r1, r2, r3) == ("🍋", "🍋", "🍋"):
        return 2
    if "🍒" in reels:
        return 1
    return 0

# Uitbetaling = score (kan je later tweaken met multiplier)
def payout_for_score(score: int) -> int:
    return score

# ----------------------------
# State & schemas
# ----------------------------
class GameState(BaseModel):
    credits: int = 0
    spins: int = 0
    total_spent: int = 0
    total_earned: int = 0
    last_reels: Optional[Tuple[str, str, str]] = None
    last_score: Optional[int] = None
    last_delta: Optional[int] = None  # earned - cost

# Eenvoudig globale serverstate voor demo.
STATE = GameState(credits=0)

class InitGameInput(BaseModel):
    starting_credits: conint(ge=0) = Field(10, description="Starttegoed in credits")

class AddCreditsInput(BaseModel):
    amount: conint(gt=0) = Field(..., description="Aantal credits om toe te voegen (>0)")

class SpinResult(BaseModel):
    reels: Tuple[str, str, str]
    score: int
    cost: int
    earned: int
    delta: int
    balance: int

# ----------------------------
# Tools
# ----------------------------
@mcp.tool()
def init_game(data: InitGameInput) -> GameState:
    """
    Start een nieuw spel met 'starting_credits'.
    """
    global STATE
    STATE = GameState(credits=data.starting_credits)
    return STATE

@mcp.tool()
def add_credits(data: AddCreditsInput) -> GameState:
    """
    Voeg credits toe aan het huidige spel.
    """
    STATE.credits += data.amount
    return STATE

@mcp.tool()
def get_state() -> GameState:
    """
    Geef de huidige spelstatus terug.
    """
    return STATE

@mcp.tool()
def reset() -> GameState:
    """
    Reset het spel naar 0 credits en leegt de laatste resultaten.
    """
    global STATE
    STATE = GameState(credits=0)
    return STATE

@mcp.tool()
def spin() -> SpinResult:
    """
    Draai de slotmachine (kost credits) en ontvang eventuele uitbetaling.
    """
    if STATE.credits < SPIN_COST:
        # In MCP wil je liever geen exceptions; maar voor duidelijkheid:
        raise ValueError(f"Onvoldoende credits ({STATE.credits}) om te spinnen. Kosten: {SPIN_COST}")

    # Trek kosten af
    STATE.credits -= SPIN_COST
    STATE.total_spent += SPIN_COST

    # Spin 3 rollen
    reels = (random.choice(SYMBOLS), random.choice(SYMBOLS), random.choice(SYMBOLS))
    score = score_reels(reels)
    earned = payout_for_score(score)

    # Uitbetaling bijschrijven
    STATE.credits += earned
    STATE.total_earned += earned
    STATE.spins += 1

    delta = earned - SPIN_COST

    # Laatste resultaten bewaren
    STATE.last_reels = reels
    STATE.last_score = score
    STATE.last_delta = delta

    return SpinResult(
        reels=reels,
        score=score,
        cost=SPIN_COST,
        earned=earned,
        delta=delta,
        balance=STATE.credits,
    )

if __name__ == "__main__":
    # Start een STDIO MCP server
    mcp.run()
