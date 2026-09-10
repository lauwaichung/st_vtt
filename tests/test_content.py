import json

import pytest

from st_vtt.content import ContentError, level_up_cost, load_content, merge_pack_files


def test_example_pack_loads(pack):
    assert pack.pack.id == "example"
    assert pack.playbook("wanderer") is not None
    assert "take_a_risk" in pack.shared_moves()
    assert pack.find_move("trailsense", "wanderer").hold.name == "Focus"


def test_level_cost():
    assert level_up_cost("6 + 2*level", 1) == 8
    assert level_up_cost("6 + 2*level", 3) == 12
    with pytest.raises(ValueError):
        level_up_cost("__import__('os')", 1)


def _write_pack(tmp_path, **overrides):
    src = tmp_path / "pack"
    src.mkdir()
    base = {
        "pack": {"id": "t", "name": "T", "stats": [{"id": "str", "label": "STR"}]},
        "moves": {"basic": [{"id": "hit", "name": "Hit", "roll": {"stat": "str"}, "outcomes": {"10+": "ok"}}]},
        "playbooks": [{"id": "pb", "name": "PB", "hp_max": 10, "starting_moves": {"fixed": ["hit"]}}],
    }
    base.update(overrides)
    (src / "all.json").write_text(json.dumps(base))
    return src


def test_minimal_pack(tmp_path):
    p = load_content(_write_pack(tmp_path))
    assert p.playbooks[0].hp_max == 10


def test_unknown_stat_reference_is_reported(tmp_path):
    src = _write_pack(tmp_path, moves={"basic": [{"id": "hit", "name": "Hit", "roll": {"stat": "dex"}}]})
    with pytest.raises(ContentError) as ei:
        load_content(src)
    assert "unknown stat 'dex'" in str(ei.value)


def test_unknown_starting_move(tmp_path):
    src = _write_pack(tmp_path, playbooks=[{"id": "pb", "name": "PB", "hp_max": 10, "starting_moves": {"fixed": ["nope"]}}])
    with pytest.raises(ContentError) as ei:
        load_content(src)
    assert "unknown move 'nope'" in str(ei.value)


def test_bad_json_names_file_and_line(tmp_path):
    src = tmp_path / "pack"
    src.mkdir()
    (src / "pack.json").write_text('{"pack": {\n  "id": }')
    with pytest.raises(ContentError) as ei:
        load_content(src)
    assert "pack.json" in str(ei.value) and "line 2" in str(ei.value)


def test_duplicate_object_key_across_files(tmp_path):
    src = _write_pack(tmp_path)
    (src / "extra.json").write_text(json.dumps({"pack": {"id": "x", "name": "x", "stats": [{"id": "a", "label": "A"}]}}))
    with pytest.raises(ContentError) as ei:
        merge_pack_files(src)
    assert "already defined" in str(ei.value)


def test_extra_field_rejected(tmp_path):
    src = _write_pack(tmp_path, playbooks=[{"id": "pb", "name": "PB", "hp_max": 10, "bogus": 1}])
    with pytest.raises(ContentError) as ei:
        load_content(src)
    assert "bogus" in str(ei.value)


def test_unknown_top_level_key(tmp_path):
    src = tmp_path / "pack"
    src.mkdir()
    src.joinpath("all.json").write_text(json.dumps({
        "pack": {"id": "t", "name": "T", "stats": [{"id": "str", "label": "STR"}]},
        "town_sheet": {"name": "Home"},
    }))
    with pytest.raises(ContentError) as ei:
        load_content(src)
    assert "unknown top-level key 'town_sheet'" in str(ei.value)


def test_shared_sheet_validation(tmp_path):
    src = _write_pack(tmp_path, shared_sheets=[{"id": "a", "sizes": ["x"], "size_start": "y"}, {"id": "a"}])
    with pytest.raises(ContentError) as ei:
        load_content(src)
    msg = str(ei.value)
    assert "duplicate template ids" in msg and "size_start" in msg


def test_example_pack_has_gm_screen(pack):
    t = pack.shared_sheet("gm_screen")
    assert t.visibility == "gm" and not t.auto_create
    assert any(c.type == "dice" for c in t.sections[0].columns)
