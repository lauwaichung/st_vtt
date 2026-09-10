"""Content pack models and loader.

A content pack describes a game (stats, moves, playbooks, shared sheets, ...)
and is supplied by the user as JSON. The pydantic models here are the source of
truth for the schema; `content/schema.json` is generated from them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import dice


class ContentError(Exception):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- pack meta


class Stat(Strict):
    id: str = Field(description="Short key used in moves, e.g. 'str'.")
    label: str = Field(description="Display label, e.g. 'STR'.")
    min: int = -3
    max: int = 3


class Debility(Strict):
    id: str
    label: str
    affects: list[str] = Field(default_factory=list, description="Stat ids that roll with disadvantage while marked.")
    text: str = ""


class Tier(Strict):
    label: str = Field(description="e.g. '10+', '7-9', '6-'. Used as the key in move outcomes.")
    min: int | None = None
    max: int | None = None

    def matches(self, total: int) -> bool:
        return (self.min is None or total >= self.min) and (self.max is None or total <= self.max)


DEFAULT_TIERS = [Tier(label="10+", min=10), Tier(label="7-9", min=7, max=9), Tier(label="6-", max=6)]


class RollRules(Strict):
    base: str = "2d6"
    advantage: str = "3d6kh2"
    disadvantage: str = "3d6kl2"
    tiers: list[Tier] = Field(default_factory=lambda: list(DEFAULT_TIERS))
    mark_xp_on: list[str] = Field(default_factory=lambda: ["6-"], description="Tier labels that suggest marking XP.")

    def tier_for(self, total: int) -> Tier | None:
        for t in self.tiers:
            if t.matches(total):
                return t
        return None


class XpRules(Strict):
    level_up_cost: str = Field(default="6 + 2*level", description="Arithmetic in `level`.")
    start_level: int = 1
    max_xp: int | None = None


class DicePreset(Strict):
    label: str
    expr: str = Field(description="Dice expression; may use {damage_die} or {<stat id>}.")


class LoadRules(Strict):
    light: int = 3
    normal: int = 6
    heavy: int = 9


class PackMeta(Strict):
    id: str
    name: str
    description: str = ""
    stats: list[Stat] = Field(min_length=1)
    stat_array: list[int] = Field(default_factory=list, description="Values to distribute at creation.")
    debilities: list[Debility] = Field(default_factory=list)
    roll: RollRules = Field(default_factory=RollRules)
    xp: XpRules = Field(default_factory=XpRules)
    dice_presets: list[DicePreset] = Field(default_factory=list)
    load: LoadRules | None = None
    gear_tags: list[str] = Field(default_factory=list)
    hold_names: list[str] = Field(default_factory=list, description="Extra hold currencies shown on every sheet.")


# --------------------------------------------------------------------------- moves


class RollSpec(Strict):
    stat: str | list[str] | None = Field(
        default=None,
        description="A stat id, a list of stat ids the player chooses from, 'choose' for any stat, or null for +nothing.",
    )
    bonus: int = 0
    label: str | None = None


class Hold(Strict):
    name: str
    note: str = ""


class Requires(Strict):
    level: int | None = None
    moves: list[str] = Field(default_factory=list)


class Move(Strict):
    id: str
    name: str
    trigger: str = ""
    text: str = Field(default="", description="Markdown body.")
    roll: RollSpec | None = None
    outcomes: dict[str, str] = Field(default_factory=dict, description="Tier label -> markdown.")
    hold: Hold | None = None
    pips: int | None = Field(default=None, ge=1, le=20)
    requires: Requires | None = None
    tags: list[str] = Field(default_factory=list)
    replaces: str | None = None


# --------------------------------------------------------------------------- generic sections


class Effects(Strict):
    moves: list[str] = Field(default_factory=list)
    armor: int | None = None
    hp: int | None = None
    tags: list[str] = Field(default_factory=list)


class Option(Strict):
    id: str
    label: str
    text: str = ""
    effects: Effects | None = None
    pips: int | None = Field(default=None, ge=1, le=20, description="Uses/charges tracked on the sheet while the option is selected.")


class Column(Strict):
    id: str
    label: str
    type: Literal["text", "number", "check", "select", "dice"] = "text"
    options: list[str] = Field(default_factory=list)


class NameList(Strict):
    label: str
    names: list[str]


SectionType = Literal["choose", "multichoose", "checklist", "pips", "text", "table", "names"]


class Section(Strict):
    id: str
    title: str
    type: SectionType
    help: str = ""
    options: list[Option] = Field(default_factory=list, description="For choose/multichoose/checklist.")
    min: int | None = Field(default=None, description="multichoose: minimum picks required (creation checklist).")
    max: int | None = Field(default=None, description="multichoose: maximum picks. pips: number of pips.")
    columns: list[Column] = Field(default_factory=list, description="For table.")
    lists: list[NameList] = Field(default_factory=list, description="For names.")
    placeholder: str = ""
    required: bool = Field(default=True, description="Shown in the creation checklist when unfilled.")

    @model_validator(mode="after")
    def _check(self) -> "Section":
        if self.type in ("choose", "multichoose", "checklist") and not self.options:
            raise ValueError(f"section {self.id!r} of type {self.type} needs options")
        if self.type == "table" and not self.columns:
            raise ValueError(f"table section {self.id!r} needs columns")
        if self.type == "names" and not self.lists:
            raise ValueError(f"names section {self.id!r} needs lists")
        if self.type == "pips" and not self.max:
            raise ValueError(f"pips section {self.id!r} needs max")
        return self


# --------------------------------------------------------------------------- playbooks


class ChooseN(Strict):
    n: int = Field(ge=1)
    from_: list[str] = Field(alias="from", min_length=1)
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class StartingMoves(Strict):
    fixed: list[str] = Field(default_factory=list)
    choose: list[ChooseN] = Field(default_factory=list)


Insert = Literal["gear", "followers", "arcana"]


class Playbook(Strict):
    id: str
    name: str
    blurb: str = ""
    hp_max: int = Field(ge=1)
    damage_die: str = "1d6"
    armor: int = 0
    stat_array: list[int] | None = None
    sections: list[Section] = Field(default_factory=list)
    moves: list[Move] = Field(default_factory=list)
    starting_moves: StartingMoves = Field(default_factory=StartingMoves)
    inserts: list[Insert] = Field(default_factory=lambda: ["gear"])
    hold_names: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- followers / arcana


class FollowerRules(Strict):
    loyalty_max: int = 3
    tags: list[str] = Field(default_factory=list)
    costs: list[str] = Field(default_factory=list)
    instincts: list[str] = Field(default_factory=list)
    fields: list[Column] = Field(default_factory=list, description="Extra per-follower fields.")


class Tracker(Strict):
    id: str
    label: str
    type: Literal["pips", "counter", "toggle"] = "pips"
    max: int | None = None


class Arcanum(Strict):
    id: str
    name: str
    kind: str = Field(default="minor", description="Free-form, e.g. 'major' or 'minor'.")
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    questions: list[str] = Field(default_factory=list)
    prerequisites: str = ""
    moves: list[Move] = Field(default_factory=list)
    trackers: list[Tracker] = Field(default_factory=list)


# --------------------------------------------------------------------------- shared sheets


class SheetStat(Strict):
    id: str
    label: str
    start: int = 0
    min: int = -3
    max: int = 3
    help: str = ""


class SharedSheetDef(Strict):
    """A template for a sheet the whole table (or only the GM) edits together: the village, a GM screen, ..."""

    id: str
    name: str = "Shared sheet"
    blurb: str = ""
    auto_create: bool = Field(default=False, description="Create one instance the first time the campaign runs.")
    visibility: Literal["table", "gm"] = Field(default="table", description="'gm' sheets are only visible to GMs.")
    stats: list[SheetStat] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    size_start: str | None = None
    debilities: list[Debility] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    moves: list[Move] = Field(default_factory=list)


# --------------------------------------------------------------------------- pack


class ContentPack(Strict):
    pack: PackMeta
    moves: dict[str, list[Move]] = Field(default_factory=dict, description="Move groups shared by all PCs, e.g. basic/special.")
    playbooks: list[Playbook] = Field(default_factory=list)
    followers: FollowerRules = Field(default_factory=FollowerRules)
    arcana: list[Arcanum] = Field(default_factory=list)
    shared_sheets: list[SharedSheetDef] = Field(default_factory=list)

    # ---- lookups
    def shared_sheet(self, tid: str) -> SharedSheetDef | None:
        return next((t for t in self.shared_sheets if t.id == tid), None)

    def stat_ids(self) -> list[str]:
        return [s.id for s in self.pack.stats]

    def playbook(self, pid: str) -> Playbook | None:
        return next((p for p in self.playbooks if p.id == pid), None)

    def shared_moves(self) -> dict[str, Move]:
        return {m.id: m for group in self.moves.values() for m in group}

    def all_moves(self) -> dict[str, Move]:
        out = self.shared_moves()
        for p in self.playbooks:
            for m in p.moves:
                out[m.id] = m
        for a in self.arcana:
            for m in a.moves:
                out[m.id] = m
        for t in self.shared_sheets:
            for m in t.moves:
                out[m.id] = m
        return out

    def find_move(self, move_id: str, playbook_id: str | None = None) -> Move | None:
        if playbook_id:
            pb = self.playbook(playbook_id)
            if pb:
                for m in pb.moves:
                    if m.id == move_id:
                        return m
        return self.all_moves().get(move_id)

    # ---- validation
    @model_validator(mode="after")
    def _cross_check(self) -> "ContentPack":
        errors: list[str] = []
        stat_ids = set(self.stat_ids())
        if len(stat_ids) != len(self.pack.stats):
            errors.append("pack.stats: duplicate stat ids")
        for d in self.pack.debilities:
            for s in d.affects:
                if s not in stat_ids:
                    errors.append(f"pack.debilities[{d.id}].affects: unknown stat {s!r}")
        for i, preset in enumerate(self.pack.dice_presets):
            try:
                dice.parse(preset.expr, {"damage_die": "1d6", **{s: 0 for s in stat_ids}})
            except dice.DiceError as e:
                errors.append(f"pack.dice_presets[{i}] ({preset.label}): {e}")
        for expr_name, expr in (("base", self.pack.roll.base), ("advantage", self.pack.roll.advantage), ("disadvantage", self.pack.roll.disadvantage)):
            try:
                dice.parse(expr)
            except dice.DiceError as e:
                errors.append(f"pack.roll.{expr_name}: {e}")
        try:
            level_up_cost(self.pack.xp.level_up_cost, 1)
        except Exception as e:  # noqa: BLE001
            errors.append(f"pack.xp.level_up_cost: {e}")

        def check_move(where: str, m: Move) -> None:
            if m.roll and m.roll.stat is not None and m.roll.stat != "choose":
                stats = [m.roll.stat] if isinstance(m.roll.stat, str) else m.roll.stat
                for s in stats:
                    if s not in stat_ids:
                        errors.append(f"{where}.roll.stat: unknown stat {s!r}")
            tier_labels = {t.label for t in self.pack.roll.tiers}
            for label in m.outcomes:
                if label not in tier_labels:
                    errors.append(f"{where}.outcomes: unknown tier {label!r} (tiers are {sorted(tier_labels)})")

        seen_moves: dict[str, str] = {}
        for group, moves in self.moves.items():
            for m in moves:
                where = f"moves.{group}[{m.id}]"
                if m.id in seen_moves:
                    errors.append(f"{where}: duplicate move id (also in {seen_moves[m.id]})")
                seen_moves[m.id] = where
                check_move(where, m)
        for pb in self.playbooks:
            pb_move_ids = {m.id for m in pb.moves}
            for m in pb.moves:
                where = f"playbooks[{pb.id}].moves[{m.id}]"
                if m.id in seen_moves:
                    errors.append(f"{where}: duplicate move id (also in {seen_moves[m.id]})")
                seen_moves[m.id] = where
                check_move(where, m)
                if m.requires:
                    for r in m.requires.moves:
                        if r not in pb_move_ids and r not in self.shared_moves():
                            errors.append(f"{where}.requires.moves: unknown move {r!r}")
                if m.replaces and m.replaces not in pb_move_ids:
                    errors.append(f"{where}.replaces: unknown move {m.replaces!r}")
            known = pb_move_ids | set(self.shared_moves())
            for r in pb.starting_moves.fixed:
                if r not in known:
                    errors.append(f"playbooks[{pb.id}].starting_moves.fixed: unknown move {r!r}")
            for c in pb.starting_moves.choose:
                for r in c.from_:
                    if r not in known:
                        errors.append(f"playbooks[{pb.id}].starting_moves.choose: unknown move {r!r}")
                if c.n > len(c.from_):
                    errors.append(f"playbooks[{pb.id}].starting_moves.choose: n={c.n} exceeds options")
            if pb.stat_array is not None and len(pb.stat_array) != len(self.pack.stats):
                errors.append(f"playbooks[{pb.id}].stat_array: expected {len(self.pack.stats)} values")
            sec_ids: set[str] = set()
            for sec in pb.sections:
                if sec.id in sec_ids:
                    errors.append(f"playbooks[{pb.id}].sections: duplicate section id {sec.id!r}")
                sec_ids.add(sec.id)
                for opt in sec.options:
                    if opt.effects:
                        for r in opt.effects.moves:
                            if r not in known:
                                errors.append(f"playbooks[{pb.id}].sections[{sec.id}].options[{opt.id}].effects.moves: unknown move {r!r}")
        if self.pack.stat_array and len(self.pack.stat_array) != len(self.pack.stats):
            errors.append(f"pack.stat_array: expected {len(self.pack.stats)} values")
        pb_ids = [p.id for p in self.playbooks]
        if len(set(pb_ids)) != len(pb_ids):
            errors.append("playbooks: duplicate playbook ids")
        arc_ids = [a.id for a in self.arcana]
        if len(set(arc_ids)) != len(arc_ids):
            errors.append("arcana: duplicate arcanum ids")
        for a in self.arcana:
            for m in a.moves:
                check_move(f"arcana[{a.id}].moves[{m.id}]", m)
        tids = [t.id for t in self.shared_sheets]
        if len(set(tids)) != len(tids):
            errors.append("shared_sheets: duplicate template ids")
        for t in self.shared_sheets:
            for m in t.moves:
                check_move(f"shared_sheets[{t.id}].moves[{m.id}]", m)
            if t.size_start and t.size_start not in t.sizes:
                errors.append(f"shared_sheets[{t.id}].size_start: not in sizes")
            sec_ids = set()
            for sec in t.sections:
                if sec.id in sec_ids:
                    errors.append(f"shared_sheets[{t.id}].sections: duplicate section id {sec.id!r}")
                sec_ids.add(sec.id)
        if errors:
            raise ValueError("\n".join(errors))
        return self


def level_up_cost(formula: str, level: int) -> int:
    """Evaluate a tiny arithmetic formula in `level` (digits, + - * / ( ) only)."""
    allowed = set("0123456789+-*/() level")
    if not set(formula) <= allowed:
        raise ValueError(f"illegal characters in formula {formula!r}")
    return int(eval(formula, {"__builtins__": {}}, {"level": level}))  # noqa: S307


# --------------------------------------------------------------------------- loading


LIST_KEYS = {"playbooks", "arcana", "shared_sheets"}
OBJECT_KEYS = {"pack", "followers"}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ContentError(f"{path}: invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}") from e


def merge_pack_files(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    """Merge every *.json under `root` into one raw pack dict.

    Files directly inside a `playbooks/` or `arcana/` directory are single
    entries. Other files contribute top-level keys: list keys concatenate,
    `moves` groups concatenate, object keys must appear in exactly one file.
    Returns (raw, origins) where origins maps "key" -> file for error messages.
    """
    raw: dict[str, Any] = {}
    origins: dict[str, Path] = {}
    files = sorted(p for p in root.rglob("*.json") if not p.name.startswith("."))
    if not files:
        raise ContentError(f"no .json files found under {root}")
    for f in files:
        data = _read_json(f)
        parent = f.parent.name
        if parent in LIST_KEYS and f.parent != root:
            if not isinstance(data, dict):
                raise ContentError(f"{f}: expected a single object")
            raw.setdefault(parent, []).append(data)
            origins[f"{parent}[{data.get('id', len(raw[parent]) - 1)}]"] = f
            continue
        if not isinstance(data, dict):
            raise ContentError(f"{f}: top level must be an object")
        for key, val in data.items():
            if key in LIST_KEYS:
                if not isinstance(val, list):
                    raise ContentError(f"{f}: {key} must be a list")
                raw.setdefault(key, []).extend(val)
                for item in val:
                    if isinstance(item, dict):
                        origins[f"{key}[{item.get('id')}]"] = f
            elif key == "moves":
                if not isinstance(val, dict):
                    raise ContentError(f"{f}: moves must be an object of group -> list")
                groups = raw.setdefault("moves", {})
                for g, moves in val.items():
                    if not isinstance(moves, list):
                        raise ContentError(f"{f}: moves.{g} must be a list")
                    groups.setdefault(g, []).extend(moves)
                    origins[f"moves.{g}"] = f
            elif key in OBJECT_KEYS:
                if key in raw:
                    raise ContentError(f"{f}: {key!r} already defined in {origins[key]}")
                raw[key] = val
                origins[key] = f
            else:
                raise ContentError(f"{f}: unknown top-level key {key!r}")
    return raw, origins


def _format_validation_error(e: ValidationError, source: str, origins: dict[str, Path]) -> str:
    lines = [f"{source}: content pack is invalid"]
    for err in e.errors():
        loc_parts = [str(x) for x in err["loc"]]
        loc = ".".join(loc_parts) or "<root>"
        origin = ""
        if loc_parts:
            head = loc_parts[0]
            if head in ("playbooks", "arcana", "shared_sheets") and len(loc_parts) > 1:
                # try to name the entry by id via origins
                for k, f in origins.items():
                    if k.startswith(head + "["):
                        origin = ""  # ambiguous by index; keep loc only
                        break
            elif head == "moves" and len(loc_parts) > 1:
                origin = f" (in {origins.get(f'moves.{loc_parts[1]}', '')})"
            elif head in origins:
                origin = f" (in {origins[head]})"
        msg = err["msg"]
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        for line in msg.splitlines():
            lines.append(f"  {loc}: {line}{origin}")
    return "\n".join(lines)


def load_content(path: str | Path) -> ContentPack:
    path = Path(path)
    if not path.exists():
        raise ContentError(f"content pack not found: {path}")
    origins: dict[str, Path] = {}
    if path.is_dir():
        raw, origins = merge_pack_files(path)
    else:
        raw = _read_json(path)
    try:
        return ContentPack.model_validate(raw)
    except ValidationError as e:
        raise ContentError(_format_validation_error(e, str(path), origins)) from e


def json_schema() -> dict[str, Any]:
    return ContentPack.model_json_schema()
