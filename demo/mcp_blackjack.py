# blackjack_mcp.py
# Blackjack MCP-server (STDIO) met state, dealer-reveal fix en correcte blackjack payout (3:2).
# Start:
#   uv tool install "mcp[cli]" pydantic   (of: uvx pip install "mcp[cli]" pydantic)
#   uvx mcp dev blackjack_mcp.py
# Of direct:
#   python blackjack_mcp.py

import random
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, conint
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("blackjack")

# ----------------------------
# Kaarten & helpers
# ----------------------------
SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def build_shoe(num_decks: int) -> List[str]:
    deck = [f"{r}{s}" for r in RANKS for s in SUITS]
    shoe = deck * num_decks
    random.shuffle(shoe)
    return shoe

def hand_value(cards: List[str]) -> Tuple[int, bool]:
    """Return (best_value, is_soft). Aces kunnen 1 of 11 zijn."""
    values = []
    aces = 0
    for c in cards:
        r = c[:-1] or c[0]  # "10" vs "A"
        if r in ["J", "Q", "K"]:
            v = 10
        elif r == "A":
            v = 11
            aces += 1
        else:
            v = int(r)
        values.append(v)
    total = sum(values)
    # Verlaag A's van 11 naar 1 indien bust
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    # soft = er telt nog minstens één A als 11
    soft = aces > 0
    return total, soft

def is_blackjack(cards: List[str]) -> bool:
    if len(cards) != 2:
        return False
    val, _ = hand_value(cards)
    ranks = {cards[0][:-1] or cards[0][0], cards[1][:-1] or cards[1][0]}
    return val == 21 and ("A" in ranks)

# ----------------------------
# Config & State
# ----------------------------
class GameConfig(BaseModel):
    starting_credits: conint(ge=0) = Field(50, description="Starttegoed")
    num_decks: conint(ge=1, le=8) = Field(4, description="Aantal decks in de shoe")
    bj_pay_n: conint(ge=1) = Field(3, description="Blackjack payout numerator (3)")
    bj_pay_d: conint(ge=1) = Field(2, description="Blackjack payout denominator (2)")
    dealer_hits_soft_17: bool = Field(False, description="Dealer hit op soft 17 (False=stand)")

class RoundResult(BaseModel):
    outcome: Optional[str] = None  # "player_blackjack", "player_win", "dealer_win", "push", "player_bust", "dealer_bust", "dealer_blackjack"
    payout: int = 0  # netto verandering voor speler (exclusief teruggegeven inzet bij push)

class GameState(BaseModel):
    credits: int = 0
    current_bet: int = 0
    shoe: List[str] = Field(default_factory=list)
    discard: List[str] = Field(default_factory=list)
    player_hand: List[str] = Field(default_factory=list)
    dealer_hand: List[str] = Field(default_factory=list)  # [0]=upcard, [1]=hole
    in_round: bool = False
    can_double: bool = False
    config: GameConfig = Field(default_factory=GameConfig)
    last_result: Optional[RoundResult] = None

    # Nieuw: definitieve handen van de laatst afgerekende ronde, voor reveal
    last_final_player_hand: List[str] = Field(default_factory=list)
    last_final_dealer_hand: List[str] = Field(default_factory=list)

    @property
    def dealer_upcard(self) -> Optional[str]:
        return self.dealer_hand[0] if self.dealer_hand else None

    def visible_state(self) -> dict:
        # Tijdens ronde: toon upcard + verborgen hole
        if self.in_round:
            visible_dealer = self.dealer_hand[:1] + (["🂠"] if len(self.dealer_hand) >= 2 else [])
            player = self.player_hand
        else:
            # Na ronde: toon de gerevealde, definitieve handen (indien aanwezig)
            if self.last_result and self.last_final_dealer_hand:
                visible_dealer = self.last_final_dealer_hand
                player = self.last_final_player_hand
            else:
                visible_dealer = self.dealer_hand
                player = self.player_hand

        return {
            "credits": self.credits,
            "current_bet": self.current_bet,
            "player_hand": player,
            "dealer_hand": visible_dealer,
            "in_round": self.in_round,
            "can_double": self.can_double,
            "config": self.config.dict(),  # of .model_dump() bij pydantic v2
            "last_result": self.last_result.dict() if self.last_result else None,
            "shoe_remaining": len(self.shoe),
            "discard_count": len(self.discard),
        }

STATE = GameState(credits=0)

# ----------------------------
# Schemas (inputs/outputs)
# ----------------------------
class InitGameInput(GameConfig):
    pass

class AddCreditsInput(BaseModel):
    amount: conint(gt=0) = Field(..., description="Credits toevoegen (>0)")

class PlaceBetInput(BaseModel):
    amount: conint(gt=0) = Field(..., description="Inzet (>0)")

class ActionResult(BaseModel):
    state: dict
    message: str

# ----------------------------
# Kernlogica
# ----------------------------
def ensure_shoe():
    # Als de shoe te klein wordt, schud bij met discard of bouw nieuwe shoe
    if len(STATE.shoe) < 15:
        STATE.shoe += STATE.discard
        STATE.discard = []
        random.shuffle(STATE.shoe)
        if not STATE.shoe:
            STATE.shoe = build_shoe(STATE.config.num_decks)

def deal_card(to: List[str]):
    ensure_shoe()
    card = STATE.shoe.pop()
    to.append(card)

def settle_round_with_payout(result: RoundResult) -> RoundResult:
    STATE.last_result = result
    return settle_round(result.outcome or "round_end")

def settle_round(reason: str) -> RoundResult:
    """Sluit ronde af, onthoud definitieve handen voor reveal, gooi daarna naar discard."""
    result = STATE.last_result or RoundResult(outcome=reason, payout=0)

    # Sla definitieve handen op vóór we ze legen (reveal werkt hierdoor correct)
    STATE.last_final_player_hand = STATE.player_hand.copy()
    STATE.last_final_dealer_hand = STATE.dealer_hand.copy()

    # Kaarten naar discard + ronde sluiten
    STATE.discard.extend(STATE.player_hand)
    STATE.discard.extend(STATE.dealer_hand)
    STATE.player_hand.clear()
    STATE.dealer_hand.clear()
    STATE.current_bet = 0
    STATE.in_round = False
    STATE.can_double = False
    STATE.last_result = result
    return result

def dealer_play():
    """Dealer speelt; standaard stand op 17 inclusief soft (tenzij dealer_hits_soft_17=True)."""
    while True:
        total, soft = hand_value(STATE.dealer_hand)
        if total < 17:
            deal_card(STATE.dealer_hand)
            continue
        if total == 17 and soft and STATE.config.dealer_hits_soft_17:
            deal_card(STATE.dealer_hand)
            continue
        break

def resolve_outcome(initial_check: bool = False) -> RoundResult:
    """Bepaalt resultaat. Bij initial_check: check blackjacks; anders normale afronding."""
    bet = STATE.current_bet
    player_total, _ = hand_value(STATE.player_hand)
    dealer_total, _ = hand_value(STATE.dealer_hand)

    if initial_check:
        player_bj = is_blackjack(STATE.player_hand)
        dealer_bj = is_blackjack(STATE.dealer_hand)

        if player_bj and dealer_bj:
            # Push: inzet terug
            STATE.credits += bet
            result = RoundResult(outcome="push", payout=0)
            return settle_round_with_payout(result)

        if player_bj:
            # Blackjack betaalt 3:2 (standaard) — netto winst = 1.5 * bet
            profit = (STATE.config.bj_pay_n * bet) // STATE.config.bj_pay_d
            STATE.credits += bet + profit  # inzet + winst
            result = RoundResult(outcome="player_blackjack", payout=profit)
            return settle_round_with_payout(result)

        if dealer_bj:
            # Speler verliest inzet
            result = RoundResult(outcome="dealer_blackjack", payout=-bet)
            return settle_round_with_payout(result)

        # Geen blackjack -> ronde gaat door
        return RoundResult(outcome=None, payout=0)

    # Normale afronding
    if player_total > 21:
        result = RoundResult(outcome="player_bust", payout=-bet)
        return settle_round_with_payout(result)

    if dealer_total > 21:
        # Dealer bust -> speler wint 1:1
        STATE.credits += bet * 2
        result = RoundResult(outcome="dealer_bust", payout=bet)
        return settle_round_with_payout(result)

    if player_total > dealer_total:
        STATE.credits += bet * 2
        result = RoundResult(outcome="player_win", payout=bet)
        return settle_round_with_payout(result)

    if player_total < dealer_total:
        result = RoundResult(outcome="dealer_win", payout=-bet)
        return settle_round_with_payout(result)

    # Push: inzet terug
    STATE.credits += bet
    result = RoundResult(outcome="push", payout=0)
    return settle_round_with_payout(result)

# ----------------------------
# MCP Tools
# ----------------------------
@mcp.tool()
def init_game(data: InitGameInput) -> ActionResult:
    """Start nieuw spel met config (credits, #decks, bj payout, dealer soft17-gedrag)."""
    global STATE
    STATE = GameState(
        credits=data.starting_credits,
        shoe=build_shoe(data.num_decks),
        discard=[],
        config=GameConfig(**data.dict()),
    )
    # reset reveal
    STATE.last_result = None
    STATE.last_final_player_hand = []
    STATE.last_final_dealer_hand = []
    return ActionResult(state=STATE.visible_state(), message="Nieuw spel gestart.")

@mcp.tool()
def add_credits(data: AddCreditsInput) -> ActionResult:
    """Voeg credits toe."""
    STATE.credits += data.amount
    return ActionResult(state=STATE.visible_state(), message=f"{data.amount} credits toegevoegd.")

@mcp.tool()
def get_state() -> ActionResult:
    """Huidige zichtbare state (dealer hole verborgen in-ronde, volledig gereveald na ronde)."""
    return ActionResult(state=STATE.visible_state(), message="OK")

@mcp.tool()
def reset() -> ActionResult:
    """Reset spel: credits=0, nieuwe shoe, wis laatste reveal."""
    global STATE
    cfg = STATE.config
    STATE = GameState(
        credits=0,
        shoe=build_shoe(cfg.num_decks),
        discard=[],
        config=cfg,
    )
    STATE.last_result = None
    STATE.last_final_player_hand = []
    STATE.last_final_dealer_hand = []
    return ActionResult(state=STATE.visible_state(), message="Reset uitgevoerd.")

@mcp.tool()
def place_bet(data: PlaceBetInput) -> ActionResult:
    """
    Plaats inzet en deel startkaarten uit.
    - Trekt inzet direct van credits af.
    - Dealt speler 2, dealer 2 (1 up, 1 hole).
    - Controleert blackjack(s) en rondt zo nodig af.
    """
    if STATE.in_round:
        return ActionResult(state=STATE.visible_state(), message="Ronde loopt al.")
    if data.amount > STATE.credits:
        raise ValueError(f"Onvoldoende credits ({STATE.credits}) voor inzet {data.amount}.")
    if data.amount <= 0:
        raise ValueError("Inzet moet > 0 zijn.")

    STATE.credits -= data.amount
    STATE.current_bet = data.amount
    STATE.player_hand = []
    STATE.dealer_hand = []
    STATE.in_round = True
    STATE.can_double = True

    # Wis reveal van vorige ronde
    STATE.last_result = None
    STATE.last_final_player_hand = []
    STATE.last_final_dealer_hand = []

    # Deal: speler, dealer, speler, dealer
    deal_card(STATE.player_hand)
    deal_card(STATE.dealer_hand)
    deal_card(STATE.player_hand)
    deal_card(STATE.dealer_hand)

    # Directe blackjack check
    res = resolve_outcome(initial_check=True)
    if res.outcome:
        # Ronde is al afgerekend (BJ/push/dealer BJ)
        return ActionResult(
            state=STATE.visible_state(),
            message=f"Ronde afgerond: {res.outcome} (payout {res.payout})."
        )
    return ActionResult(state=STATE.visible_state(), message="Inzet geplaatst en kaarten gedeeld.")

@mcp.tool()
def hit() -> ActionResult:
    """Neem een kaart. Bij bust -> ronde eindigt. Anders blijft ronde lopen."""
    if not STATE.in_round:
        return ActionResult(state=STATE.visible_state(), message="Geen actieve ronde.")
    deal_card(STATE.player_hand)
    total, _ = hand_value(STATE.player_hand)
    STATE.can_double = False
    if total > 21:
        res = resolve_outcome(initial_check=False)
        return ActionResult(
            state=STATE.visible_state(),
            message=f"Bust! Resultaat: {res.outcome} (payout {res.payout})."
        )
    return ActionResult(state=STATE.visible_state(), message="Hit uitgevoerd.")

@mcp.tool()
def stand() -> ActionResult:
    """Speler past; dealer speelt en ronde wordt afgerekend (reveal dealer-hand)."""
    if not STATE.in_round:
        return ActionResult(state=STATE.visible_state(), message="Geen actieve ronde.")
    STATE.can_double = False
    dealer_play()
    res = resolve_outcome(initial_check=False)
    return ActionResult(
        state=STATE.visible_state(),
        message=f"Ronde afgerond: {res.outcome} (payout {res.payout})."
    )

@mcp.tool()
def double_down() -> ActionResult:
    """
    Verdubbel inzet, neem precies 1 kaart en sta vervolgens automatisch.
    Alleen toegestaan als eerste actie (can_double=True) en als credits toereikend zijn.
    """
    if not STATE.in_round:
        return ActionResult(state=STATE.visible_state(), message="Geen actieve ronde.")
    if not STATE.can_double:
        raise ValueError("Double down kan nu niet (alleen direct na de deal).")
    if STATE.credits < STATE.current_bet:
        raise ValueError("Onvoldoende credits om te verdubbelen.")

    # Trek extra inzet
    STATE.credits -= STATE.current_bet
    STATE.current_bet *= 2
    STATE.can_double = False

    # Eén kaart
    deal_card(STATE.player_hand)
    total, _ = hand_value(STATE.player_hand)
    if total > 21:
        res = resolve_outcome(initial_check=False)
        return ActionResult(
            state=STATE.visible_state(),
            message=f"Bust na double! Resultaat: {res.outcome} (payout {res.payout})."
        )

    # Daarna automatisch stand
    dealer_play()
    res = resolve_outcome(initial_check=False)
    return ActionResult(
        state=STATE.visible_state(),
        message=f"Ronde afgerond (double): {res.outcome} (payout {res.payout})."
    )

if __name__ == "__main__":
    mcp.run()
