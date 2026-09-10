"""Operations shared by the REST API and the WebSocket handler.

Each mutating function persists the change and returns one or more events to
broadcast. Events are plain dicts; `render` callables produce a per-user view
(so GM-only data never reaches players).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from fastapi import FastAPI

from . import characters as chars
from . import rolls
from .config import UserConfig
from .content import ContentPack
from .db import Database
from .dice import DiceError
from .patch import PatchError, apply_patch
from .content import Move
from .perms import Forbidden, check_patch, strip_for_user, visible_to

Render = Callable[[UserConfig], dict[str, Any] | None]


class ServiceError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def pack_of(app: FastAPI) -> ContentPack:
    return app.state.pack


def db_of(app: FastAPI) -> Database:
    return app.state.db


# ----------------------------------------------------------------- characters


def character_view(user: UserConfig, row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "data": strip_for_user(user, row["data"])}


def list_characters(app: FastAPI, user: UserConfig) -> list[dict[str, Any]]:
    return [character_view(user, r) for r in db_of(app).list_characters()]


def create_character(app: FastAPI, user: UserConfig, playbook_id: str, name: str, owner: str | None) -> tuple[dict[str, Any], list[Render]]:
    pack = pack_of(app)
    pb = pack.playbook(playbook_id)
    if pb is None:
        raise ServiceError(f"unknown playbook {playbook_id!r}")
    if owner is not None and owner != user.name and not user.is_gm:
        raise ServiceError("only the GM can assign owners", 403)
    if owner is None:
        owner = user.name
    if app.state.config.user(owner) is None:
        raise ServiceError(f"unknown user {owner!r}")
    doc = chars.new_character(pack, pb, name.strip() or pb.name)
    row = db_of(app).insert_character(chars.new_id(), owner, doc)
    msg = db_of(app).add_message(None, "system", {"text": f"{user.name} created {doc['name']} ({pb.name}) for {owner}."})
    return row, [lambda u: {"type": "character_created", "character": character_view(u, row)}, lambda u: {"type": "message", "message": msg}]


def import_character(app: FastAPI, user: UserConfig, doc: dict[str, Any], owner: str | None) -> tuple[dict[str, Any], list[str], list[Render]]:
    pack = pack_of(app)
    try:
        clean, warnings = chars.validate_import(pack, doc)
    except ValueError as e:
        raise ServiceError(str(e)) from e
    if owner is not None and owner != user.name and not user.is_gm:
        raise ServiceError("only the GM can assign owners", 403)
    owner = owner or user.name
    if app.state.config.user(owner) is None:
        raise ServiceError(f"unknown user {owner!r}")
    if not user.is_gm:
        clean["gm_notes"] = ""
    row = db_of(app).insert_character(chars.new_id(), owner, clean)
    msg = db_of(app).add_message(None, "system", {"text": f"{user.name} imported {clean.get('name') or 'a character'} for {owner}."})
    return row, warnings, [lambda u: {"type": "character_created", "character": character_view(u, row)}, lambda u: {"type": "message", "message": msg}]


def delete_character(app: FastAPI, user: UserConfig, cid: str) -> list[Render]:
    row = db_of(app).get_character(cid)
    if row is None:
        raise ServiceError("no such character", 404)
    if not user.is_gm and row["owner"] != user.name:
        raise ServiceError("only the owner or GM can delete", 403)
    db_of(app).delete_character(cid)
    msg = db_of(app).add_message(None, "system", {"text": f"{user.name} deleted {row['data'].get('name') or 'a character'}."})
    return [lambda u: {"type": "character_deleted", "id": cid}, lambda u: {"type": "message", "message": msg}]


def set_owner(app: FastAPI, user: UserConfig, cid: str, owner: str | None) -> list[Render]:
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    if db_of(app).get_character(cid) is None:
        raise ServiceError("no such character", 404)
    if owner is not None and app.state.config.user(owner) is None:
        raise ServiceError(f"unknown user {owner!r}")
    db_of(app).set_character_owner(cid, owner)
    return [lambda u: {"type": "character_owner", "id": cid, "owner": owner}]


# ---------------------------------------------------------------- shared sheets


def shared_template(app: FastAPI, row: dict[str, Any]):
    return pack_of(app).shared_sheet(row["template"])


def shared_visible(app: FastAPI, user: UserConfig, row: dict[str, Any]) -> bool:
    tpl = shared_template(app, row)
    return user.is_gm or tpl is None or tpl.visibility == "table"


def shared_is_gm_only(app: FastAPI, sid: str | None) -> bool:
    """True when the shared sheet `sid` is only visible to GMs."""
    if not sid:
        return False
    row = db_of(app).get_shared(sid)
    if row is None:
        return False
    tpl = shared_template(app, row)
    return bool(tpl and tpl.visibility == "gm")


def shared_view(user: UserConfig, row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "data": strip_for_user(user, row["data"])}


def list_shared(app: FastAPI, user: UserConfig) -> list[dict[str, Any]]:
    return [shared_view(user, r) for r in db_of(app).list_shared() if shared_visible(app, user, r)]


def _shared_render(app: FastAPI, row: dict[str, Any], kind: str) -> Render:
    def render(u: UserConfig) -> dict[str, Any] | None:
        if not shared_visible(app, u, row):
            return None
        if kind == "shared_deleted":
            return {"type": kind, "id": row["id"]}
        return {"type": kind, "sheet": shared_view(u, row)}

    return render


def create_shared(app: FastAPI, user: UserConfig, template_id: str, name: str | None) -> tuple[dict[str, Any], list[Render]]:
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    tpl = pack_of(app).shared_sheet(template_id)
    if tpl is None:
        raise ServiceError(f"unknown shared sheet template {template_id!r}")
    doc = chars.new_shared_sheet(pack_of(app), tpl, name)
    row = db_of(app).insert_shared(chars.new_id(), tpl.id, doc)
    renders: list[Render] = [_shared_render(app, row, "shared_created")]
    if tpl.visibility == "table":
        msg = db_of(app).add_message(None, "system", {"text": f"{user.name} added a shared sheet: {doc['name']}."})
        renders.append(_message_render(msg))
    return row, renders


def delete_shared(app: FastAPI, user: UserConfig, sid: str) -> list[Render]:
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    row = db_of(app).get_shared(sid)
    if row is None:
        raise ServiceError("no such shared sheet", 404)
    db_of(app).delete_shared(sid)
    return [_shared_render(app, row, "shared_deleted")]


def import_shared(app: FastAPI, user: UserConfig, sid: str, doc: dict[str, Any]) -> list[Render]:
    """Replace a shared sheet's contents (GM only). Template stays what it was."""
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    row = db_of(app).get_shared(sid)
    if row is None:
        raise ServiceError("no such shared sheet", 404)
    if not isinstance(doc, dict):
        raise ServiceError("shared sheet must be a JSON object")
    tpl = shared_template(app, row)
    template = chars.new_shared_sheet(pack_of(app), tpl) if tpl else dict(row["data"])
    merged = chars.deep_fill(doc, template)
    merged["template"] = row["template"]
    for k in ("id", "revision"):
        merged.pop(k, None)
    db_of(app).save_shared(sid, merged)
    return [_shared_render(app, db_of(app).get_shared(sid), "shared_replaced")]


def autocreate_shared(app: FastAPI) -> None:
    """Create one instance of each auto_create template, once per campaign (deleting it does not bring it back)."""
    db = db_of(app)
    pack = pack_of(app)
    for tpl in pack.shared_sheets:
        if tpl.auto_create and not db.get_meta(f"auto_created:{tpl.id}"):
            db.insert_shared(chars.new_id(), tpl.id, chars.new_shared_sheet(pack, tpl))
            db.set_meta(f"auto_created:{tpl.id}", "1")


# --------------------------------------------------------------------- patches


def patch_entity(app: FastAPI, user: UserConfig, entity: str, eid: str | None, path: str, value: Any = None, op: str = "set", client: str | None = None, patch: str | None = None) -> list[Render]:
    db = db_of(app)
    if entity == "character":
        if not eid:
            raise ServiceError("missing character id")
        row = db.get_character(eid)
        if row is None:
            raise ServiceError("no such character", 404)
        owner = row["owner"]
    elif entity == "shared":
        if not eid:
            raise ServiceError("missing shared sheet id")
        row = db.get_shared(eid)
        if row is None:
            raise ServiceError("no such shared sheet", 404)
        owner = None
    else:
        raise ServiceError(f"unknown entity {entity!r}")
    gm_sheet = entity == "shared" and not shared_visible(app, UserConfig(name="", role="player"), row)
    try:
        check_patch(user, entity, owner, path, gm_only=gm_sheet)
    except Forbidden as e:
        raise ServiceError(str(e), 403) from e
    doc = row["data"]
    try:
        result = apply_patch(doc, path, value, op, patch)
    except PatchError as e:
        raise ServiceError(f"bad patch: {e}") from e
    merged = op == "text_patch"
    if merged:
        op, value = "set", result
    if entity == "character":
        rev = db.save_character(eid, doc)
    else:
        rev = db.save_shared(eid, doc)
    gm_only = path.startswith("/gm_notes") or gm_sheet

    def render(u: UserConfig) -> dict[str, Any] | None:
        if gm_only and not u.is_gm:
            return None
        return {"type": "patch", "entity": entity, "id": eid, "path": path, "value": value, "op": op, "revision": rev, "by": user.name, "client": client, "merged": merged}

    return [render]


# ------------------------------------------------------------------- messages


def _message_render(msg: dict[str, Any]) -> Render:
    def render(u: UserConfig) -> dict[str, Any] | None:
        return {"type": "message", "message": msg} if visible_to(u, msg.get("visibility")) else None

    return render


def gm_names(app: FastAPI) -> list[str]:
    return [u.name for u in app.state.config.users if u.is_gm]


_CMD = re.compile(r"^/(\w+)\s*(.*)$", re.S)


def post_chat(app: FastAPI, user: UserConfig, text: str, to: list[str] | None = None) -> list[Render]:
    """Plain chat, or slash commands: /roll /r /gmroll /w <name> <text>."""
    text = text.strip()
    if not text:
        raise ServiceError("empty message")
    m = _CMD.match(text)
    if m:
        cmd, rest = m.group(1).lower(), m.group(2).strip()
        if cmd in ("roll", "r"):
            return do_roll(app, user, {"expr": rest})
        if cmd in ("gmroll", "gr"):
            return do_roll(app, user, {"expr": rest, "gm_only": True})
        if cmd in ("w", "whisper"):
            parts = rest.split(None, 1)
            if len(parts) < 2:
                raise ServiceError("usage: /w <name> <message>")
            target = app.state.config.user(parts[0]) or next((u for u in app.state.config.users if u.name.lower() == parts[0].lower()), None)
            if target is None:
                raise ServiceError(f"unknown user {parts[0]!r}")
            to = [target.name]
            text = parts[1]
        elif cmd in ("gm",):
            to = gm_names(app)
            text = rest
        else:
            raise ServiceError(f"unknown command /{cmd}")
    if to:
        vis = sorted(set([user.name, *to]))
        msg = db_of(app).add_message(user.name, "whisper", {"text": text, "to": to}, vis)
    else:
        msg = db_of(app).add_message(user.name, "chat", {"text": text})
    return [_message_render(msg)]


def do_roll(app: FastAPI, user: UserConfig, spec: dict[str, Any]) -> list[Render]:
    """spec: {expr, label} or {character_id, move_id?, stat?, advantage?, disadvantage?, bonus?, label?}; plus gm_only."""
    pack = pack_of(app)
    doc = None
    cid = spec.get("character_id")
    if cid:
        row = db_of(app).get_character(cid)
        if row is None:
            raise ServiceError("no such character", 404)
        doc = row["data"]
    try:
        if spec.get("expr"):
            payload = rolls.roll_expr(pack, str(spec["expr"]), doc, label=spec.get("label"))
        else:
            move = None
            if spec.get("move_id"):
                move = pack.find_move(str(spec["move_id"]), doc.get("playbook") if doc else None)
                if move is None and doc:
                    move = _custom_move(pack, doc, str(spec["move_id"]))
                if move is None:
                    raise ServiceError(f"unknown move {spec['move_id']!r}")
            stat = spec.get("stat")
            if stat is not None and stat not in pack.stat_ids():
                raise ServiceError(f"unknown stat {stat!r}")
            if move and move.roll and stat is None and isinstance(move.roll.stat, str) and move.roll.stat != "choose":
                stat = move.roll.stat
            payload = rolls.roll_move(
                pack,
                doc=doc,
                move=move,
                stat=stat,
                advantage=bool(spec.get("advantage")),
                disadvantage=bool(spec.get("disadvantage")),
                bonus=int(spec.get("bonus") or 0),
                label=spec.get("label"),
            )
    except DiceError as e:
        raise ServiceError(f"bad dice expression: {e}") from e
    payload["character_id"] = cid
    vis = sorted(set([user.name, *gm_names(app)])) if spec.get("gm_only") else None
    payload["gm_only"] = bool(spec.get("gm_only"))
    msg = db_of(app).add_message(user.name, "roll", payload, vis)
    return [_message_render(msg)]


def _custom_move(pack: ContentPack, doc: dict[str, Any], move_id: str) -> Move | None:
    for raw in doc.get("custom_moves") or []:
        if isinstance(raw, dict) and raw.get("id") == move_id:
            try:
                return Move.model_validate(raw)
            except Exception:  # noqa: BLE001
                return None
    return None


def share_move(app: FastAPI, user: UserConfig, character_id: str | None, move_id: str) -> list[Render]:
    """Post a move's text to the chat as a card."""
    pack = pack_of(app)
    doc = None
    if character_id:
        row = db_of(app).get_character(character_id)
        if row is None:
            raise ServiceError("no such character", 404)
        doc = row["data"]
    move = pack.find_move(move_id, doc.get("playbook") if doc else None)
    if move is None and doc:
        move = _custom_move(pack, doc, move_id)
    if move is None:
        raise ServiceError(f"unknown move {move_id!r}")
    payload = {
        "move_id": move.id,
        "name": move.name,
        "trigger": move.trigger,
        "text": move.text,
        "outcomes": move.outcomes,
        "hold": move.hold.model_dump() if move.hold else None,
        "roll": move.roll.model_dump() if move.roll else None,
        "character": doc.get("name") if doc else None,
        "character_id": character_id,
    }
    msg = db_of(app).add_message(user.name, "move", payload)
    return [_message_render(msg)]


def request_roll(app: FastAPI, user: UserConfig, target: str, label: str, stat: str | None) -> list[Render]:
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    if app.state.config.user(target) is None:
        raise ServiceError(f"unknown user {target!r}")
    if stat is not None and stat not in pack_of(app).stat_ids():
        raise ServiceError(f"unknown stat {stat!r}")
    msg = db_of(app).add_message(user.name, "request", {"to": target, "label": label or "a roll", "stat": stat})
    return [_message_render(msg)]


def clear_chat(app: FastAPI, user: UserConfig) -> list[Render]:
    if not user.is_gm:
        raise ServiceError("GM only", 403)
    db_of(app).clear_messages()
    msg = db_of(app).add_message(None, "system", {"text": f"{user.name} cleared the chat."})
    return [lambda u: {"type": "chat_cleared"}, _message_render(msg)]
