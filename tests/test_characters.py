"""Document construction from a content pack."""

from st_vtt.characters import default_section_value, new_character, new_shared_sheet, validate_import
from st_vtt.content import ContentPack


def _pack(**overrides) -> ContentPack:
    raw = {
        "pack": {"id": "t", "name": "T", "stats": [{"id": "str", "label": "STR"}]},
        "playbooks": [{
            "id": "pb", "name": "PB", "hp_max": 10,
            "inserts": ["gear"],
            "sections": [{
                "id": "appearance", "title": "Appearance", "type": "lines",
                "lines": [
                    {"id": "age", "write_in": "or make something up", "options": [
                        {"id": "age_young", "label": "young & brash"},
                        {"id": "age_old", "label": "old & leathery"},
                    ]},
                    {"id": "voice", "options": [
                        {"id": "voice_soft", "label": "soft-spoken"},
                        {"id": "voice_loud", "label": "gravelly voice"},
                    ]},
                ],
            }],
        }],
    }
    raw.update(overrides)
    return ContentPack.model_validate(raw)


def test_new_character_seeds_its_sections_and_inserts():
    pack = _pack()
    doc = new_character(pack, pack.playbooks[0], "Pedr")
    assert doc["inserts"] == ["gear"]
    assert doc["sections"]["appearance"] == {"age": None, "voice": None}


def test_an_insert_brings_its_sections_and_fixed_moves():
    pack = _pack(
        inserts=[{
            "id": "mule", "name": "Mule",
            "starting_moves": {"fixed": ["stubborn"]},
            "moves": [{"id": "stubborn", "name": "Stubborn"}],
            "sections": [{"id": "mule_temper", "title": "Temperament", "type": "choose",
                          "options": [{"id": "placid", "label": "Placid"}]}],
        }],
        playbooks=[{"id": "pb", "name": "PB", "hp_max": 10, "inserts": ["gear", "mule"]}],
    )
    doc = new_character(pack, pack.playbooks[0], "Pedr")
    assert doc["inserts"] == ["gear", "mule"]
    assert doc["moves"]["taken"] == ["stubborn"]
    assert doc["sections"]["mule_temper"] is None


def test_section_start_seeds_a_new_sheet():
    pack = _pack(shared_sheets=[{
        "id": "village", "name": "Village",
        "sections": [{
            "id": "resources", "title": "Resources", "type": "table",
            "columns": [{"id": "resource", "label": "Resource"}],
            "start": [{"resource": "Farming"}, {"resource": "Distilling"}],
        }],
    }])
    doc = new_shared_sheet(pack, pack.shared_sheets[0])
    assert doc["sections"]["resources"] == [{"resource": "Farming"}, {"resource": "Distilling"}]
    # the seed is copied, not shared between sheets
    doc["sections"]["resources"].append({"resource": "Mill"})
    assert len(new_shared_sheet(pack, pack.shared_sheets[0])["sections"]["resources"]) == 2


def test_default_section_value_per_type():
    pack = _pack(playbooks=[{
        "id": "pb", "name": "PB", "hp_max": 10,
        "sections": [
            {"id": "a", "title": "A", "type": "choose", "options": [{"id": "x", "label": "X"}]},
            {"id": "b", "title": "B", "type": "multichoose", "options": [{"id": "y", "label": "Y"}]},
            {"id": "c", "title": "C", "type": "pips", "max": 3},
            {"id": "d", "title": "D", "type": "text"},
            {"id": "e", "title": "E", "type": "table", "columns": [{"id": "col", "label": "Col"}]},
            {"id": "f", "title": "F", "type": "names", "lists": [{"label": "Hills", "names": ["Bryn"]}]},
        ],
    }])
    got = [default_section_value(s) for s in pack.playbooks[0].sections]
    assert got == [None, [], 0, "", [], {"origin": "", "name": ""}]


def test_import_fills_in_what_a_hand_written_document_leaves_out():
    pack = _pack()
    doc, warnings = validate_import(pack, {"playbook": "pb", "name": "Pedr"})
    assert doc["sections"]["appearance"] == {"age": None, "voice": None}
    assert doc["inserts"] == ["gear"]
    assert warnings == []


def test_a_new_sheet_has_somewhere_to_keep_a_moves_picks():
    pack = _pack()
    doc = new_character(pack, pack.playbooks[0], "Pedr")
    assert doc["moves"]["options"] == {}
    shared = new_shared_sheet(pack, ContentPack.model_validate({
        "pack": {"id": "t", "name": "T", "stats": [{"id": "str", "label": "STR"}]},
        "shared_sheets": [{"id": "village", "name": "Village"}],
    }).shared_sheets[0])
    assert shared["moves"]["options"] == {}
