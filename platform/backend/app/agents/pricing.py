"""Token → cost pricing for agent runs.

Prices are USD per **1M tokens**, split input/output, keyed by model id. Unknown models (including the
offline ``stub``) price at **zero**, which keeps the offline reference journey's cost deterministic at
``$0`` while a real provider yields real figures. Update the table as provider pricing changes.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# (input_per_million_usd, output_per_million_usd). Representative list price; adjust as needed.
MODEL_PRICING: dict[str, tuple[str, str]] = {
    "claude-opus-4-8": ("15.00", "75.00"),
    "claude-sonnet-5": ("3.00", "15.00"),
    "claude-haiku-4-5-20251001": ("0.80", "4.00"),
}

_ZERO = Decimal("0")


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the USD cost of a run for ``model``; unknown/stub models cost 0.0 (deterministic offline)."""
    prices = MODEL_PRICING.get(model)
    if not prices:
        return 0.0
    in_price, out_price = Decimal(prices[0]), Decimal(prices[1])
    total = (Decimal(input_tokens) * in_price + Decimal(output_tokens) * out_price) / Decimal(1_000_000)
    return float(total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
