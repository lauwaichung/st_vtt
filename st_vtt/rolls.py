"""Move rolls: base dice + stat + bonus, advantage/disadvantage, tier resolution."""

from __future__ import annotations

from typing import Any, Callable

from . import dice
from .content import ContentPack, Move


def debility_disadvantage(pack: ContentPack, doc: dict[str, Any], stat: str | None) -> list[str]:
    """Labels of marked debilities that affect `stat`."""
    if stat is None:
        return []
    marked = doc.get("debilities") or {}
    return [d.label for d in pack.pack.debilities if marked.get(d.id) and stat in d.affects]


def roll_move(
    pack: ContentPack,
    *,
    doc: dict[str, Any] | None,
    move: Move | None,
    stat: str | None,
    advantage: bool = False,
    disadvantage: bool = False,
    bonus: int = 0,
    label: str | None = None,
    rng: Callable[[int, int], int] | None = None,
) -> dict[str, Any]:
    """Roll the pack's base dice for a move. Returns a chat payload dict."""
    rules = pack.pack.roll
    auto = debility_disadvantage(pack, doc or {}, stat) if doc else []
    if auto:
        disadvantage = True
    if advantage and disadvantage:
        expr, mode = rules.base, "both"
    elif advantage:
        expr, mode = rules.advantage, "advantage"
    elif disadvantage:
        expr, mode = rules.disadvantage, "disadvantage"
    else:
        expr, mode = rules.base, "normal"
    stat_mod = 0
    stat_label = None
    if stat is not None:
        stat_mod = int((doc or {}).get("stats", {}).get(stat, 0))
        stat_def = next((s for s in pack.pack.stats if s.id == stat), None)
        stat_label = stat_def.label if stat_def else stat
    if move and move.roll:
        bonus += move.roll.bonus
    result = dice.roll(expr, rng=rng)
    total = result.total + stat_mod + bonus
    tier = rules.tier_for(total)
    return {
        "type": "move",
        "label": label or (move.name if move else "Roll"),
        "move_id": move.id if move else None,
        "character": (doc or {}).get("name"),
        "stat": stat,
        "stat_label": stat_label,
        "stat_mod": stat_mod,
        "bonus": bonus,
        "mode": mode,
        "auto_disadvantage": auto,
        "roll": result.to_dict(),
        "total": total,
        "tier": tier.label if tier else None,
        "outcome": (move.outcomes.get(tier.label) if (move and tier) else None),
        "mark_xp": bool(tier and tier.label in rules.mark_xp_on),
    }


def roll_expr(
    pack: ContentPack,
    expr: str,
    doc: dict[str, Any] | None = None,
    label: str | None = None,
    rng: Callable[[int, int], int] | None = None,
) -> dict[str, Any]:
    """Roll a free-form expression; {damage_die} and {stat} refs resolve against `doc`."""
    refs: dict[str, str | int] = {}
    if doc:
        pb = pack.playbook(doc.get("playbook", ""))
        refs["damage_die"] = pb.damage_die if pb else "1d6"
        for sid, val in (doc.get("stats") or {}).items():
            refs[sid] = int(val)
    else:
        refs["damage_die"] = "1d6"
        for s in pack.pack.stats:
            refs[s.id] = 0
    result = dice.roll(expr, refs=refs, rng=rng)
    return {
        "type": "dice",
        "label": label or expr,
        "character": (doc or {}).get("name"),
        "roll": result.to_dict(),
        "total": result.total,
    }
